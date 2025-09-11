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
def generate_wild_card(structured_entries, topic):
    prompt = f"""
The user has been journaling. Here are their last 5 entries summarized:

{chr(10).join(f"- {m}" for m in structured_entries)}

Topic focus: {topic}

Recommend ONE real consumer product or sponsorship category that the user could realistically purchase online or in a store.
- Base it on recurring topics, subtopics, and emotions across the 5 entries (not just the most recent one).
- Suggest well-known, practical categories: fitness gear, creator tools, home office gadgets, kitchen tools, wellness items, travel accessories, or books.
- Avoid novelty, joke, or fantasy products.
- Keep the output short and simple, just the product or category name.

Examples: "Adjustable dumbbells", "Noise-canceling headphones", "A standing desk mat", "Ring light kit", "Video editing software".
Only output the product suggestion, nothing else.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[⚠️ Wild Card Error] {e}", flush=True)
        return None

def get_countdown_text(remaining):
    simple_map = {
        4: "4 messages until a product recommendation.",
        3: "3 messages until a product recommendation.",
        2: "2 messages until a product recommendation.",
        1: "1 message until a product recommendation.",
    }
    return simple_map.get(remaining, "")

def get_roast_message(entry_count):
    roast_map = {
        1: "We know… it’s slow. But notice how your messy thoughts are already bucketed into themes.",
        2: "Still warming up. At least we can already summarize and hint at your momentum — faster than your notes app.",
        3: "Getting closer. Try switching topics entirely — we’ll still stitch context together.",
        4: "Now go back to your earlier theme. See how we carry continuity across separate threads?",
        5: "Finally. After all this waiting, here comes our most questionable feature: a product recommendation. Don’t expect genius.",
    }
    return roast_map.get(entry_count, "")

# ---------------------------
# Routes
# ---------------------------
@app.route("/message", methods=["POST"])
def handle_message():
    print("✅ REQUEST RECEIVED", flush=True)
    data = request.json

    user_id = data.get("user_id", "anonymous")
    message = data.get("message", "")
    tags = data.get("tags", [])
    debug_mode = data.get("debug_mode", False)
    is_demo = data.get("demo_mode", False) or user_id.startswith("demo_")

    # 👇 NEW: embedding threshold override
    embedding_threshold = float(data.get("embedding_threshold", 0.82))

    debug_log = {}

    # 🧠 Ingest message
    thread_id, thread_is_intensifying, reference_past_issue, debug_meta = ingest_message(
        user_id=user_id,
        message_text=message,
        tags=(tags + ["demo"]) if is_demo else tags,
        importance_score=0.5,
        debug=debug_mode,
        goal_label=None,
        embedding_threshold=embedding_threshold   # 👈 pass through
    )
    debug_log.update(debug_meta)
    classified_topic = debug_meta.get("classified_topic", "unknown")

    session = SessionLocal()

    # 🔍 Count total reflections by this user (global, across all threads)
    user_entry_count = (
        session.query(func.count(MemoryEvent.id))
        .filter_by(user_id=user_id)
        .scalar()
    )
    debug_log["user_entry_count"] = user_entry_count

    # 🔍 Get all messages in this thread (for summarization/context continuity)
    thread_events = []
    if message.strip():
        thread_events = (
            session.query(MemoryEvent)
            .filter_by(user_id=user_id, thread_id=thread_id)
            .order_by(MemoryEvent.timestamp.asc())
            .all()
        )
        debug_log["thread_memory_hits"] = len(thread_events)

    # Collect raw messages for summarization
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

    # Summarization still uses raw messages
    summary_data = summarize_memories(past_memories, user_id)

    # 🧠 Wild Card + Roast logic (global counter)
    wild_card = ""
    roast_message = get_roast_message(user_entry_count)

    if user_entry_count >= 5:
        # Last 5 entries as structured Topic/Subtopics/Emotion (for product recs only)
        recent_events = (
            session.query(MemoryEvent)
            .filter_by(user_id=user_id)
            .order_by(MemoryEvent.timestamp.desc())
            .limit(5)
            .all()
        )
        structured_last_five = []
        for ev in reversed(recent_events):
            if not ev:
                continue
            structured_last_five.append(
                f"Topic: {ev.topic} | Subtopics: {ev.subtopics or 'N/A'} | Emotion: {ev.sentiment}"
            )

        wild_card = generate_wild_card(structured_last_five, classified_topic) or ""
        print(f"🎁 Product recommendation triggered (global entries={user_entry_count})", flush=True)
    else:
        remaining = 5 - user_entry_count
        if remaining > 0:
            wild_card = get_countdown_text(remaining)
            debug_log["countdown_remaining"] = remaining
            print(f"⏳ Countdown: {remaining} reflections left (global entries={user_entry_count})", flush=True)

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
        "wild_card": wild_card,
        "roast_message": roast_message
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
