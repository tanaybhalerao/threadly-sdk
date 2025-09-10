import os
os.environ["WATCHFILES_DISABLE_GLOBAL_WATCHER"] = "true"

import streamlit as st
from collections import defaultdict
from datetime import datetime
from uuid import uuid4
import requests

# ---------------------------
# CONFIG
# ---------------------------
BACKEND_URL = "https://threadly-backend-sqvr.onrender.com/message"

# ---------------------------
# SESSION STATE INIT
# ---------------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = f"demo_{uuid4().hex[:8]}"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
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
    st.markdown("---")
    st.markdown(f"**Session ID:** `{st.session_state.user_id}`")
    st.markdown(f"**Reflections used:** {len(st.session_state.chat_history)}/5")
    if st.button("Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ---------------------------
# MAIN TITLE + ROAST LINE
# ---------------------------
st.title("Thread-ly: Reflective Journal")

# Always read last context so roast appears immediately under header
header_context = st.session_state.last_response or {}
roast_msg = header_context.get("roast_message")
if roast_msg:
    # lightweight, visible line without a header
    st.markdown(
        f"<div style='margin-top:-8px;margin-bottom:16px;font-size:14px;opacity:0.85;'>{roast_msg}</div>",
        unsafe_allow_html=True
    )

left, right = st.columns([1, 1])

# ---------------------------
# LEFT: JOURNAL
# ---------------------------
with left:
    st.subheader("Your Entries")
    with st.container(border=True):
        if st.session_state.chat_history:
            # Show oldest → newest
            for msg in st.session_state.chat_history:
                time = msg.get("timestamp", "")
                content = msg["content"]
                st.markdown(f"- {content}")
                if time:
                    st.caption(time)
        else:
            st.info("No entries yet. Start by reflecting on something.")

    st.divider()
    st.subheader("Add Reflection")
    if len(st.session_state.chat_history) >= 5:
        st.warning("You've reached the 5-entry demo limit. Click 'Start Over' to reset.")
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
                    try:
                        response = requests.post(BACKEND_URL, json={
                            "user_id": st.session_state.user_id,
                            "message": user_msg,
                            "tags": ["demo"],
                            "debug_mode": True,  # Always ON
                            "demo_mode": True,
                            "goal_label": "",
                            "importance_score": 0.5
                        })

                        if response.status_code == 200:
                            data = response.json()
                            context = data.get("context", {})
                            thread_id = context.get("thread_id", "unknown")
                            st.session_state.chat_history[-1]["thread_id"] = thread_id
                            st.session_state.last_response = context
                        else:
                            st.error("Backend error. Please try again later.")
                    except Exception as e:
                        st.error(f"Request failed: {e}")

                st.session_state.last_message = user_msg
                st.rerun()

# ---------------------------
# RIGHT: REFLECTION OVERVIEW
# ---------------------------
with right:
    st.subheader("Reflection Overview")
    context = st.session_state.last_response or {}

    def render_block(title, value):
        if value:
            st.markdown(f"### {title}")
            st.write(value)

    # Two-column layout for summary + product reco
    col1, col2 = st.columns(2)

    with col1:
        render_block("Theme", context.get("theme"))
        render_block("Reflection", context.get("reflection_summary"))
        render_block("Momentum", context.get("momentum"))

    with col2:
        render_block("Change", context.get("change"))
        render_block("Consider Next", context.get("consider_next"))

        # Product recommendation / countdown lives here
        if context.get("wild_card"):
            st.markdown("### Product Recommendation")
            with st.container(border=True):
                st.write(context["wild_card"])

    # ---------------------------
    # Technical details (compact at bottom)
    # ---------------------------
    debug = context.get("debug_log", {})
    keep_keys = [
        "classified_topic",
        "emotion",
        "nuance",
        "subtopics",
        "selected_thread_score",
        "thread_continuation_reason",
        "thread_memory_hits",
        "user_entry_count",
        "countdown_remaining"
    ]
    cleaned_debug = {k: v for k, v in debug.items() if k in keep_keys}

    if cleaned_debug:
        st.divider()
        with st.expander("Technical Details", expanded=False):
            st.json(cleaned_debug)
