import streamlit as st
from collections import defaultdict
from datetime import datetime
from uuid import uuid4
from Threadly_SDK.memory_ingestion import ingest_message
from Threadly_SDK.db_setup import SessionLocal
from Threadly_SDK.models import MemoryEvent
from Threadly_SDK.summarizer import summarize_memories
from Threadly_SDK.embedding_utils import init_faiss, print_vector_count

init_faiss()
print_vector_count()

# ---------------------------
# SESSION STATE INIT
# ---------------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = f"demo_{uuid4().hex[:8]}"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "debug" not in st.session_state:
    st.session_state.debug = False
if "mode" not in st.session_state:
    st.session_state.mode = "Neutral"
if "last_response" not in st.session_state:
    st.session_state.last_response = {}
if "last_message" not in st.session_state:
    st.session_state.last_message = ""

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Thread-ly Journal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# SIDEBAR CONTROLS
# ---------------------------
with st.sidebar:
    st.title("Settings")
    st.session_state.mode = st.selectbox("Mode", ["Neutral", "Goal-Tracking"], index=0)
    st.session_state.debug = st.toggle("Debug Mode", value=st.session_state.debug)
    st.markdown("---")
    st.markdown(f"**Session ID:** `{st.session_state.user_id}`")
    st.markdown(f"**Reflections used:** {len(st.session_state.chat_history)}/3")
    if st.button("Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ---------------------------
# MAIN TITLE
# ---------------------------
st.title("Thread-ly: Reflective Journal")
left, right = st.columns([1, 1])

# ---------------------------
# LEFT: JOURNAL
# ---------------------------
with left:
    st.subheader("Your Entries")
    with st.container(border=True):
        if st.session_state.chat_history:
            grouped = defaultdict(list)
            for msg in st.session_state.chat_history:
                grouped[msg.get("thread_id", "unknown")].append(msg)
            for tid, messages in reversed(list(grouped.items())):
                st.markdown(f"**Thread {tid}**")
                for msg in messages:
                    time = msg.get("timestamp", "")
                    content = msg["content"]
                    st.markdown(f"- {content}")
                    if time:
                        st.caption(time)
        else:
            st.info("No entries yet. Start by reflecting on something.")

    st.divider()
    st.subheader("Add Reflection")
    if len(st.session_state.chat_history) >= 3:
        st.warning("You've reached the 3-entry demo limit. Click 'Start Over' to reset.")
    else:
        with st.form("journal_form"):
            user_msg = st.text_area("What’s on your mind today?", key="journal_input", height=120)
            submit = st.form_submit_button("Save Reflection")
            if submit and user_msg.strip():
                now = datetime.now().strftime("%b %d, %Y %I:%M %p")
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_msg,
                    "timestamp": now,
                    "thread_id": "pending"
                })

                with st.spinner("Processing your reflection..."):
                    thread_id, _, _, debug_meta = ingest_message(
                        user_id=st.session_state.user_id,
                        message_text=user_msg,
                        tags=["demo"],
                        debug=st.session_state.debug,
                        goal_label="",
                        importance_score=0.5
                    )
                    st.session_state.chat_history[-1]["thread_id"] = thread_id

                    # ✅ FIXED: Use actual DB entries instead of chat_history
                    session = SessionLocal()
                    entries = (
                        session.query(MemoryEvent)
                        .filter_by(user_id=st.session_state.user_id, thread_id=thread_id)
                        .order_by(MemoryEvent.timestamp.asc())
                        .all()
                    )
                    messages = [e.message_text for e in entries if e.message_text]
                    mode = st.session_state.get("mode", "Neutral")
                    summary = summarize_memories(messages, st.session_state.user_id, mode=mode.lower())

                    session.close()

                    st.session_state.last_response = {
                        "context": {
                            **summary,
                            "thread_id": thread_id,
                            "mode": st.session_state.mode.lower(),
                            "goal_label": "",
                            "debug_log": debug_meta if st.session_state.debug else {}
                        }
                    }

                st.session_state.last_message = user_msg
                st.rerun()

# ---------------------------
# RIGHT: SUMMARY
# ---------------------------
with right:
    st.subheader("Current Reflection Overview")
    context = st.session_state.last_response.get("context", {})

    def render_section(title, value):
        st.markdown(f"**{title}**")
        st.markdown(f"> {value or 'N/A'}")

    render_section("Theme", context.get("theme"))
    render_section("Reflection", context.get("reflection_summary"))
    render_section("Momentum", context.get("momentum"))
    render_section("Change", context.get("change"))
    render_section("Consider Next", context.get("consider_next"))

    st.divider()
    st.markdown("**Session Context**")
    st.markdown(f"`Thread ID:` `{context.get('thread_id', 'N/A')}`")
    st.markdown(f"`Mode:` `{context.get('mode', 'neutral')}`")

    if st.session_state.debug:
        debug = context.get("debug_log", {})
        if debug.get("topic_matched_memory"):
            st.markdown("✅ Using context from a **related topic**, not just this thread.")
        with st.expander("Internal Debug Log"):
            st.json(debug)
