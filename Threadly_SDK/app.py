from flask import Flask, request, jsonify
from .memory_ingestion import ingest_message
from .embedding_utils import init_faiss, search_memory, print_vector_count
from .summarizer import summarize_memories
from .db_setup import SessionLocal
from .models import UserProfile, MemoryEvent
from sqlalchemy import desc, func
from collections import defaultdict, Counter

app = Flask(__name__)
init_faiss()
print_vector_count()


@app.route("/message", methods=["POST"])
def handle_message():
    print("✅ REQUEST RECEIVED")
    data = request.json

    user_id = data.get("user_id", "anonymous")
    message = data.get("message", "")
    tags = data.get("tags", [])
    debug_mode = data.get("debug_mode", False)
    goal_label = data.get("goal_label", "")
    mode = data.get("mode", "neutral")

    debug_log = {}

    # 🧠 Ingest message
    thread_id, thread_is_intensifying, reference_past_issue, debug_meta = ingest_message(
        user_id=user_id,
        message_text=message,
        tags=tags,
        importance_score=0.5,
        debug=debug_mode,
        goal_label=goal_label
    )
    debug_log.update(debug_meta)
    classified_topic = debug_meta.get("classified_topic", "unknown")

    # 🔍 Fetch memory for summarization
    past_memories = []
    if message.strip():
        session = SessionLocal()
        thread_events = (
            session.query(MemoryEvent)
            .filter_by(user_id=user_id, thread_id=thread_id)
            .order_by(MemoryEvent.timestamp.asc())
            .all()
        )
        session.close()
        past_memories = [e.message_text for e in thread_events if e.message_text]
        debug_log["thread_memory_hits"] = len(past_memories)

    if reference_past_issue and message.strip():
        global_mem = search_memory(message, user_id=user_id, thread_id=None)
        extra_results = [m[0] for m in global_mem if m[0] not in past_memories]
        past_memories += extra_results
        debug_log["additional_past_memories"] = len(extra_results)

    session = SessionLocal()
    resolved_history = (
        session.query(MemoryEvent)
        .filter_by(user_id=user_id, topic=classified_topic, resolved=True)
        .order_by(MemoryEvent.timestamp.desc())
        .limit(10)
        .all()
    )

    threads = defaultdict(list)
    for m in resolved_history:
        threads[m.thread_id].append(
            f"[Emotion: {m.sentiment} | Nuance: {m.topic_nuance}] {m.message_text}"
        )

    threadwise_summaries = []
    for tid, entries in threads.items():
        summary = summarize_memories(entries, user_id, mode=mode)
        threadwise_summaries.append(f"[Thread {tid}]\n{summary['reflection_summary']}")

    if threadwise_summaries:
        past_memories += threadwise_summaries
        debug_log["resolved_threads_summarized"] = len(threadwise_summaries)

    print("📌 FINAL PAST_MEMORIES GOING INTO SUMMARY:")
    for m in past_memories:
        print("-", m)
    print("📌 Summary input count:", len(past_memories))

    summary_data = summarize_memories(past_memories, user_id, mode=mode)

    profile = session.query(UserProfile).filter_by(user_id=user_id).first()

    topic_counts = (
        session.query(MemoryEvent.topic, func.count(MemoryEvent.topic))
        .filter_by(user_id=user_id)
        .group_by(MemoryEvent.topic)
        .all()
    )
    topic_freq = [t for t, c in topic_counts if t and t != "unknown"]

    # ✨ Behavioral Insight block
    behavior_insight = ""
    if profile and topic_counts:
        top_topic, top_count = max(topic_counts, key=lambda x: x[1])
        if top_count >= 3:
            behavior_insight = (
                f"Your reflections often return to **{top_topic}**, especially in recent sessions. "
                f"Overall, your tone has leaned **{profile.dominant_emotion}**, with a steady presence of this theme across threads."
            )
        else:
            behavior_insight = (
                f"You're exploring a variety of topics right now. "
                f"Emotionally, your reflections feel mostly **{profile.dominant_emotion}**, with no single dominant pattern yet."
            )

    session.close()

    user_profile = {
        "dominant_emotion": profile.dominant_emotion,
        "active_topic_streak": profile.active_topic_streak,
        "repetition_count": profile.repetition_count,
        "most_common_topic": profile.most_common_topic,
        "total_threads": profile.total_threads,
        "unresolved_threads": profile.unresolved_threads
    } if profile else {}

    context = {
        "user_id": user_id,
        "thread_id": thread_id,
        "theme": summary_data["theme"],
        "reflection_summary": summary_data["reflection_summary"],
        "momentum": summary_data["momentum"],
        "change": summary_data["change"],
        "consider_next": summary_data["consider_next"],
        "goal_label": goal_label,
        "mode": mode,
        "user_profile": user_profile,
        "topic_list": topic_freq,
        "behavioral_insight": behavior_insight
    }

    if debug_mode:
        context["debug_log"] = debug_log

    return jsonify({"context": context})


@app.route("/profile/<user_id>", methods=["GET"])
def get_user_profile(user_id):
    session = SessionLocal()
    profile = session.query(UserProfile).filter_by(user_id=user_id).first()
    session.close()

    if not profile:
        return jsonify({"error": "User profile not found"}), 404

    return jsonify({
        "user_id": profile.user_id,
        "total_messages": profile.total_messages,
        "total_threads": profile.total_threads,
        "unresolved_threads": profile.unresolved_threads,
        "most_common_topic": profile.most_common_topic,
        "dominant_emotion": profile.dominant_emotion,
        "active_topic_streak": profile.active_topic_streak,
        "repetition_count": profile.repetition_count
    })


@app.route("/ping")
def ping():
    return "Flask is alive on port 5050!"


if __name__ == "__main__":
    app.run(debug=True, port=5050)
