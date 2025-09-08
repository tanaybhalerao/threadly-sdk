from .db_setup import SessionLocal
from .models import MemoryEvent, UserProfile
from .embedding_utils import add_to_memory, add_thread_signature
from .classify_utils import classify_topic, classify_sentiment
from .thread_manager import get_active_thread_id
from .summarizer import summarize_memories
from sqlalchemy import func
import hashlib
import uuid

def hash_message(user_id, message_text):
    if not message_text:
        return None
    key = f"{user_id}::{message_text.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

def get_thread_messages(session, thread_id, user_id):
    events = (
        session.query(MemoryEvent)
        .filter_by(user_id=user_id, thread_id=thread_id)
        .order_by(MemoryEvent.timestamp.asc())
        .all()
    )
    return [e.message_text for e in events if e.message_text]

def summarize_thread_and_update(thread_id, user_id):
    session = SessionLocal()
    messages = get_thread_messages(session, thread_id, user_id)
    summary_data = summarize_memories(messages, user_id)

    last_event = (
        session.query(MemoryEvent)
        .filter_by(user_id=user_id, thread_id=thread_id)
        .order_by(MemoryEvent.timestamp.desc())
        .first()
    )
    if last_event:
        last_event.current_state_summary = summary_data.get("momentum", "")
        last_event.next_step_prediction = summary_data.get("consider_next", "")
        last_event.breakthrough_flag = False
        last_event.breakthrough_description = summary_data.get("change", "")

    session.commit()
    session.close()

def ingest_message(
    user_id,
    message_text,
    tags=None,
    importance_score=0.5,
    debug=False,
    goal_label=None,
    demo_mode=False
):
    if not message_text:
        return "", False, False, {"skipped": True, "reason": "Empty message"}

    session = SessionLocal()

    topic_info = classify_topic(message_text)
    topic = topic_info.get("topic")
    topic_nuance = topic_info.get("topic_nuance")
    subtopics = topic_info.get("subtopics", [])
    reference_past_issue = topic_info.get("reference_past_issue", False)

    dominant_emotion = classify_sentiment(message_text)

    debug_log = {} if debug else None
    thread_id, thread_is_intensifying = get_active_thread_id(
        user_id=user_id,
        current_nuance=topic_nuance,
        dominant_emotion=dominant_emotion,
        debug_log=debug_log,
        current_message_text=message_text,
        current_topic=topic,
        current_subtopics=subtopics
    )

    if debug_log is not None:
        debug_log["matched_thread_id"] = thread_id

    msg_hash = hash_message(user_id, message_text)
    existing = (
        session.query(MemoryEvent)
        .filter_by(user_id=user_id, thread_id=thread_id)
        .filter(MemoryEvent.message_hash == msg_hash)
        .first()
    )
    if existing:
        session.close()
        return thread_id, False, reference_past_issue, {
            "skipped": True,
            "reason": "Duplicate message",
            "thread_id": thread_id,
            "thread_intensity_signal": thread_is_intensifying
        }

    is_first_message = (
        session.query(MemoryEvent)
        .filter_by(user_id=user_id, thread_id=thread_id)
        .count() == 0
    )

    final_tags = (tags or []) + (["demo"] if demo_mode else [])

    memory = MemoryEvent(
        user_id=user_id,
        message_text=message_text,
        response_text="",
        sentiment=dominant_emotion,
        topic=topic,
        topic_nuance=topic_nuance,
        subtopics=",".join(subtopics),
        thread_id=thread_id,
        resolved=False,
        tags=",".join(final_tags),
        importance_score=importance_score,
        message_hash=msg_hash,
        role="user",
        goal_label=goal_label if is_first_message else ""
    )
    session.add(memory)
    session.commit()
    session.close()

    # 🔁 Add message-level embedding to FAISS vector memory
    add_to_memory(message_text, {
        "user_id": user_id,
        "thread_id": thread_id,
        "topic": topic,
        "topic_nuance": topic_nuance,
        "subtopics": subtopics,
        "reference_past_issue": reference_past_issue,
        "tags": final_tags,
        "emotion": dominant_emotion,
        "goal_label": goal_label if is_first_message else ""
    })

    # 🔖 Add thread signature embedding only for first message in a thread
    if is_first_message:
        add_thread_signature(thread_id, user_id, message_text)

    if not demo_mode:
        update_user_profile(user_id, topic, dominant_emotion)

    summarize_thread_and_update(thread_id, user_id)

    debug_meta = {
        "classified_topic": topic,
        "nuance": topic_nuance,
        "subtopics": subtopics,
        "emotion": dominant_emotion,
        "thread_id": thread_id,
        "thread_intensity_signal": thread_is_intensifying,
        "goal_label": goal_label if is_first_message else ""
    }
    if debug_log:
        debug_meta.update(debug_log)

    return thread_id, thread_is_intensifying, reference_past_issue, debug_meta

def update_user_profile(user_id, topic, dominant_emotion):
    if topic == "unknown":
        return

    session = SessionLocal()
    profile = session.query(UserProfile).filter_by(user_id=user_id).first()

    if not profile:
        profile = UserProfile(
            user_id=user_id,
            total_messages=0,
            total_threads=0,
            unresolved_threads=0,
            most_common_topic="",
            dominant_emotion=dominant_emotion,
            active_topic_streak=topic,
            repetition_count=0
        )
        session.add(profile)

    profile.total_messages += 1
    profile.total_threads = (
        session.query(MemoryEvent)
        .filter_by(user_id=user_id)
        .distinct(MemoryEvent.thread_id)
        .count()
    )
    profile.unresolved_threads = (
        session.query(MemoryEvent)
        .filter_by(user_id=user_id, resolved=False)
        .distinct(MemoryEvent.thread_id)
        .count()
    )

    top_topic = (
        session.query(MemoryEvent.topic, func.count(MemoryEvent.topic))
        .filter_by(user_id=user_id)
        .group_by(MemoryEvent.topic)
        .order_by(func.count(MemoryEvent.topic).desc())
        .first()
    )
    if top_topic:
        profile.most_common_topic = top_topic[0]

    profile.dominant_emotion = dominant_emotion
    if profile.active_topic_streak == topic:
        profile.repetition_count += 1
    else:
        profile.active_topic_streak = topic
        profile.repetition_count = 1

    session.commit()
    session.close()
