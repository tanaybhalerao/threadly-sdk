import uuid
import re
from datetime import datetime, timedelta
from .db_setup import SessionLocal
from .models import MemoryEvent
from .similarity_utils import get_nuance_similarity
from .embedding_utils import get_embedding, search_thread_signatures

# Configurable thresholds
NUANCE_SIMILARITY_THRESHOLD = 0.6
THREAD_EMBEDDING_SIMILARITY_THRESHOLD = 0.82
THREAD_MAX_DAYS_OLD = 30
SUBTOPIC_OVERLAP_MIN = 1
EMBEDDING_GUARDRAIL_SCORE = 0.75  # Below this, ignore even if close

def detect_ambiguous_reference(text: str) -> bool:
    pronouns = ["it", "that", "this", "those", "them"]
    return any(re.search(rf"\b{p}\b", text.lower()) for p in pronouns)

def count_overlap(a: list[str], b: list[str]) -> int:
    return len(set(a) & set(b))

def get_active_thread_id(
    user_id: str,
    current_nuance: str,
    dominant_emotion: str = "",
    debug_log: dict = None,
    current_message_text: str = "",
    current_topic: str = "",
    current_subtopics: list[str] = None
) -> tuple[str, bool]:
    session = SessionLocal()
    now = datetime.utcnow()
    thread_is_intensifying = False
    reference_past_issue = False
    best_thread_id = None
    best_score = 0.0
    best_reason = "no prior thread matched"

    current_subtopics = current_subtopics or []
    current_vector = get_embedding(current_message_text)

    # 🔍 Try matching using thread signature embeddings
    matched_threads = search_thread_signatures(current_message_text, user_id=user_id, top_k=5)

    for thread_id, _ in matched_threads:
        recent_msg = (
            session.query(MemoryEvent)
            .filter_by(user_id=user_id, thread_id=thread_id)
            .order_by(MemoryEvent.timestamp.desc())
            .first()
        )
        if not recent_msg:
            continue

        days_old = (now - recent_msg.timestamp).days
        if days_old > THREAD_MAX_DAYS_OLD:
            continue

        nuance_match = get_nuance_similarity(current_nuance, recent_msg.topic_nuance)
        emotion_shift = recent_msg.sentiment != dominant_emotion
        is_ambiguous = detect_ambiguous_reference(current_message_text)

        past_subtopics = [s.strip() for s in recent_msg.subtopics.split(",") if s.strip()]
        subtopic_overlap = count_overlap(current_subtopics, past_subtopics)
        topic_match = (recent_msg.topic == current_topic)

        score = 0.0
        reason = ""

        if topic_match:
            score += 0.5
            reason += "topic match; "
        if subtopic_overlap >= SUBTOPIC_OVERLAP_MIN:
            score += 0.1 * subtopic_overlap
            reason += f"{subtopic_overlap} shared subtopics; "
        if nuance_match >= NUANCE_SIMILARITY_THRESHOLD:
            score += nuance_match
            reason += "nuance aligned; "
        elif is_ambiguous:
            score += 0.3
            reason += "ambiguous language; "

        if score >= EMBEDDING_GUARDRAIL_SCORE and score > best_score:
            best_score = score
            best_thread_id = thread_id
            best_reason = reason.strip()
            thread_is_intensifying = emotion_shift

        if recent_msg.resolved:
            reference_past_issue = True

    # 🧠 Fallback: Check recent threads with same topic if no strong match
    if not best_thread_id and current_topic:
        recent_cutoff = now - timedelta(days=THREAD_MAX_DAYS_OLD)
        recent_topic_threads = (
            session.query(MemoryEvent.thread_id, MemoryEvent.timestamp)
            .filter_by(user_id=user_id, topic=current_topic)
            .filter(MemoryEvent.timestamp >= recent_cutoff)
            .order_by(MemoryEvent.timestamp.desc())
            .distinct()
            .all()
        )
        if recent_topic_threads:
            best_thread_id = recent_topic_threads[0][0]
            best_reason = "fallback to recent same-topic thread"
            reference_past_issue = True  # treat as context continuation

    session.close()

    if debug_log is not None:
        debug_log["thread_selection_method"] = "thread_signature_embedding + topic fallback"
        debug_log["thread_intensity_signal"] = thread_is_intensifying
        debug_log["thread_continuation_reason"] = best_reason
        debug_log["selected_thread_score"] = round(best_score, 3)
        debug_log["ambiguous_reference_detected"] = detect_ambiguous_reference(current_message_text)

    if best_thread_id:
        return best_thread_id, thread_is_intensifying
    else:
        return str(uuid.uuid4()), False
