from flask import Flask, request, jsonify
from .memory_ingestion import ingest_message
from .embedding_utils import init_faiss, search_memory, print_vector_count
from .summarizer import summarize_memories
from .db_setup import SessionLocal
from .models import UserProfile, MemoryEvent
from sqlalchemy import func
from collections import defaultdict
from datetime import datetime, timedelta
from openai import OpenAI
import os

app = Flask(__name__)
init_faiss()
print_vector_count()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# Wild Card Helpers
# ---------------------------
def generate_wild_card(messages, topic):
    prompt = f"""
The user has been journaling. Here are their last 5 entries:

{chr(10).join(f"- {m}" for m in messages)}

Topic focus: {topic}

Give ONE quirky product recommendation (something real people might buy, not abstract).
- Make it surprising but loosely relevant to the theme.
- Keep it to 1 short sentence.
- Avoid generic items like "a book" or "a mug".
- Examples: resistance bands, sleep mask with built-in headphones, desktop punching bag.

Respond with only the product recommendation sentence.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[⚠️ Wild Card Error] {e}")
        return None

def get_countdown_text(remaining):
    roast_map = {
        4: "I know… it's slow. Look, it takes time for a half-baked product to warm up.",
        3: "I'm just trying things out here. Some will stick, the rest get dumped into the 'free features' bin.",
        2: "You seriously think Thread-ly can recommend a product worth buying? Bold of you to assume.",
        1: "One last reflection before I impart some product wisdom. Brace for disappointment."
    }
    return roast_map.get(remaining, "")

# ---------------------------
# Routes
# ---------------------------
@app.route("/message", methods=["POST"])
def handle_message():
    print("✅ REQUEST RECEIVED")
    data = request.json

    user_id = data.get("user_id", "anonymous")
    message = data.get("message", "")
    tags = data.get("tags", [])
    debug_mode = data.get("debug_mode", False)
    is_demo = data.get("demo_mode", False) or user_id.startswith("demo_")

    debug_log = {}

    # 🧠 Ingest message
    thread_id, thread_is_intensifying, reference_past_issue, debug_meta = ingest_message(
        user_id=user_id,
        message_text=message,
        tags=(tags + ["demo"]) if is_demo else tags,
        importance_score=0.5,
        debug=debug_mode,
        goal_label=None
    )
    debug_log.update(debug_meta)
    classified_topic = debug_meta.get("classified_topic", "unknown")

    session = SessionLocal()

    # 🔍 Get all messages in this thread
    thread_events = []
    if message.strip():
        thread_events = (
            session.query(MemoryEvent)
            .filter_by(user_id=user_id, thread_id=thread_id)
            .order_by(MemoryEvent.timestamp.asc())
            .all()
        )
        debug_log["thread_memory_hits"] = len(thread_events)

    # Collect text only for summarization
    past_memories = [e.message_text for e in thread_events if e.message_text]

    # 🧠 Topic-matched fallback messages
    topic_matched_messages = []
    if classified_topic and message.strip():
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        topic_entries = (
            session.query(MemoryEvent)
            .filter(MemoryEvent.user_id == user_id)
            .filter(MemoryEvent.topic == classified_topic)
            .filter(MemoryEvent.thread_id != thread_id)
            .filter(MemoryEvent.timestamp >= recent_cutoff)
            .order_by(MemoryEvent.timestamp.desc())
            .limit(10)
            .all()
        )
        for entry in topic_entries:
            if entry.message_text not in past_memories:
                topic_matched_messages.append(entry.message_text)

        if topic_matched_messages:
            debug_log["topic_matched_memory"] = len(topic_matched_messages)
            past_memories += topic_matched_messages

    # 🧠 Semantic memory fallback
    if reference_past_issue and message.strip():
        global_mem = search_memory(message, user_id=user_id, thread_id=None)
        extra_results = [m[0] for m in global_mem if m[0] not in past_memories]
        past_memories += extra_results
        debug_log["additional_past_memories"] = len(extra_results)

    # 🧠 Resolved thread summaries
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
        summary = summarize_memories(entries, user_id)
        threadwise_summaries.append(f"[Thread {tid}]\n{summary['reflection_summary']}")

    if threadwise_summaries:
        past_memories += threadwise_summaries
        debug_log["resolved_threads_summarized"] = len(threadwise_summaries)

    print("📌 FINAL PAST_MEMORIES GOING INTO SUMMARY:")
    for m in past_memories:
        print("-", m)
    print("📌 Summary input count:", len(past_memories))

    summary_data = summarize_memories(past_memories, user_id)

    # 🧠 Wild Card logic with logging
    thread_entry_count = len(thread_events)
    debug_log["thread_entry_count"] = thread_entry_count
    wild_card = ""
    if thread_entry_count >= 5:
        last_five = [e.message_text for e in thread_events[-5:] if e.message_text]
        wild_card = generate_wild_card(last_five, classified_topic) or ""
        print(f"🎁 Generating product recommendation (entries={thread_entry_count})")
    else:
        remaining = 5 - thread_entry_count
        if remaining > 0:
            wild_card = get_countdown_text(remaining)
            debug_log["countdown_remaining"] = remaining
            print(f"⏳ Countdown: {remaining} reflections left")

    # 🧠 Skip user profile for demo users
    if is_demo:
        user_profile = {}
        behavioral_insight = ""
        topic_freq = []
    else:
        profile = session.query(UserProfile).filter_by(user_id=user_id).first()
        topic_counts = (
            session.query(MemoryEvent.topic, func.count(MemoryEvent.topic))
            .filter_by(user_id=user_id)
            .group_by(MemoryEvent.topic)
            .all()
        )
        topic_freq = [t for t, c in topic_counts if t and t != "unknown"]

        behavioral_insight = ""
        if profile and topic_counts:
            top_topic, top_count = max(topic_counts, key=lambda x: x[1])
            if top_count >= 3:
                behavioral_insight = (
                    f"Your reflections often return to **{top_topic}**, especially in recent sessions. "
                    f"Overall, your tone has leaned **{profile.dominant_emotion}**, with a steady presence of this theme across threads."
                )
            else:
                behavioral_insight = (
                    f"You're exploring a variety of topics right now. "
                    f"Emotionally, your reflections feel mostly **{profile.dominant_emotion}**, with no single dominant pattern yet."
                )

        user_profile = {
            "dominant_emotion": profile.dominant_emotion,
            "active_topic_streak": profile.active_topic_streak,
            "repetition_count": profile.repetition_count,
            "most_common_topic": profile.most_common_topic,
            "total_threads": profile.total_threads,
            "unresolved_threads": profile.unresolved_threads
        } if profile else {}

    session.close()

    context = {
        "user_id": user_id,
        "thread_id": thread_id,
        "theme": summary_data["theme"],
        "reflection_summary": summary_data["reflection_summary"],
        "momentum": summary_data["momentum"],
        "change": summary_data["change"],
        "consider_next": summary_data["consider_next"],
        "user_profile": user_profile,
        "topic_list": topic_freq,
        "behavioral_insight": behavioral_insight,
        "wild_card": wild_card
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

@app.route("/healthz")
def health_check():
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True, port=5050)
