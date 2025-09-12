import uuid
import re
from datetime import datetime, timedelta
from .db_setup import SessionLocal
from .models import MemoryEvent
from .similarity_utils import get_nuance_similarity, get_embedding_similarity
from .embedding_utils import get_embedding, search_thread_signatures

# ---------------------------
# Configurable thresholds (defaults)
# ---------------------------
NUANCE_SIMILARITY_THRESHOLD = 0.35
THREAD_EMBEDDING_SIMILARITY_THRESHOLD = 0.20   # default embedding cutoff
THREAD_MAX_DAYS_OLD = 30
SUBTOPIC_OVERLAP_MIN = 1
EMBEDDING_GUARDRAIL_SCORE = 0.3
RECENT_THREAD_LIMIT = 10  # how many recent threads to check embeddings against

# ---------------------------
# Helpers
# ---------------------------
def detect_ambiguous_reference(text: str) -> bool:
    pronouns = ["it", "that", "this", "those", "them"]
    return any(re.search(rf"\b{p}\b", text.lower()) for p in pronouns)

def count_overlap(a: list[str], b: list[str]) -> int:
    return len(set(a) & set(b))

# ---------------------------
# Main thread selection logic
# ---------------------------
def get_active_thread_id(
    user_id: str,
    current_nuance: str,
    dominant_emotion: str = "",
    debug_log: dict = None,
    current_message_text: str = "",
    current_topic: str = "",
    current_subtopics: list[str] = None,
    embedding_threshold: float = THREAD_EMBEDDING_SIMILARITY_THRESHOLD
) -> tuple[str, bool]:
    """
    Decide which thread a new message belongs to.
    Uses topic match → candidate gathering (FAISS + recent threads + last thread) → scoring (nuance, subtopics, embeddings).
    """
    session = SessionLocal()
    now = datetime.utcnow()
    thread_is_intensifying = False
    reference_past_issue = False
    best_thread_id = None
    best_score = 0.0
    best_reason = "no prior thread matched"

    current_subtopics = current_subtopics or []
    _ = get_embedding(current_message_text)  # cache side effect

    # 🧠 First: Direct topic match fallback
    if current_topic:
        recent_cutoff = now - timedelta(days=THREAD_MAX_DAYS_OLD)
        topic_matched_threads = (
            session.query(MemoryEvent)
            .filter(MemoryEvent.user_id == user_id)
            .filter(MemoryEvent.topic == current_topic)
            .filter(MemoryEvent.timestamp >= recent_cutoff)
            .order_by(MemoryEvent.timestamp.desc())
            .all()
        )
        if topic_matched_threads:
            best_thread_id = topic_matched_threads[0].thread_id
            best_reason = "recent thread with same topic"
            reference_past_issue = True

    # 🧠 Second: Build candidate set
    candidate_thread_ids = set()
    if not best_thread_id:
        # (a) FAISS shortlist
        matched_threads = search_thread_signatures(current_message_text, user_id=user_id, top_k=5)
        candidate_thread_ids.update(tid for tid, _ in matched_threads)

        # (b) Last N recent threads
        recent_cutoff = now - timedelta(days=THREAD_MAX_DAYS_OLD)
        recent_events = (
            session.query(MemoryEvent)
            .filter(MemoryEvent.user_id == user_id)
            .filter(MemoryEvent.timestamp >= recent_cutoff)
            .order_by(MemoryEvent.timestamp.desc())
            .all()
        )
        seen_threads = {}
        for ev in recent_events:
            if ev.thread_id not in seen_threads:
                seen_threads[ev.thread_id] = ev
            if len(seen_threads) >= RECENT_THREAD_LIMIT:
                break
        candidate_thread_ids.update(seen_threads.keys())

        # (c) Always include last event’s thread
        last_event = (
            session.query(MemoryEvent)
            .filter_by(user_id=user_id)
            .order_by(MemoryEvent.timestamp.desc())
            .first()
        )
        if last_event:
            candidate_thread_ids.add(last_event.thread_id)

    # 🧠 Third: Score candidates
    best_emb_sim = -1.0
    candidate_debug = []  # 👈 collect debug info per candidate
    for thread_id in candidate_thread_ids:
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
        reasons = []

        if topic_match:
            score += 0.5
            reasons.append("topic match")
        if subtopic_overlap >= SUBTOPIC_OVERLAP_MIN:
            score += 0.1 * subtopic_overlap
            reasons.append(f"{subtopic_overlap} subtopics")
        if nuance_match >= NUANCE_SIMILARITY_THRESHOLD:
            score += nuance_match
            reasons.append("nuance aligned")
        elif is_ambiguous:
            score += 0.3
            reasons.append("ambiguous reference")

        # 🔑 Embedding similarity
        emb_sim = get_embedding_similarity(current_message_text, recent_msg.message_text)
        if emb_sim > best_emb_sim:
            best_emb_sim = emb_sim
        if emb_sim >= embedding_threshold:
            score = max(score, emb_sim)
            reasons.append(f"embedding strong ({emb_sim:.3f} ≥ {embedding_threshold})")

        # Save candidate details
        candidate_debug.append({
            "thread_id": thread_id,
            "topic": recent_msg.topic,
            "nuance": recent_msg.topic_nuance,
            "emb_sim": round(emb_sim, 3),
            "nuance_match": round(nuance_match, 3),
            "subtopic_overlap": subtopic_overlap,
            "score": round(score, 3),
            "reasons": reasons
        })

        # Finalize best candidate
        if score >= EMBEDDING_GUARDRAIL_SCORE and score > best_score:
            best_score = score
            best_thread_id = thread_id
            best_reason = "; ".join(reasons)
            thread_is_intensifying = emotion_shift

        if recent_msg.resolved:
            reference_past_issue = True

    session.close()

    # 🧾 Debug logging
    if debug_log is not None:
        debug_log["thread_selection_method"] = "topic + embedding scoring (FAISS + recent + last)"
        debug_log["thread_intensity_signal"] = thread_is_intensifying
        debug_log["thread_continuation_reason"] = best_reason
        debug_log["selected_thread_score"] = round(best_score, 3)
        debug_log["ambiguous_reference_detected"] = detect_ambiguous_reference(current_message_text)
        debug_log["best_embedding_similarity"] = round(best_emb_sim, 3) if best_emb_sim >= 0 else None
        debug_log["embedding_threshold_used"] = embedding_threshold
        debug_log["candidate_threads"] = candidate_debug  # 👈 NEW

    if best_thread_id:
        return best_thread_id, thread_is_intensifying
    else:
        return str(uuid.uuid4()), False
