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
# MAIN TITLE
# ---------------------------
st.title("Thread-ly: Reflective Journal")
tab1, tab2 = st.tabs(["✍️ Your Entries", "📜 Reflection Overview"])

# ---------------------------
# TAB 1: JOURNAL
# ---------------------------
with tab1:
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
# TAB 2: REFLECTION
# ---------------------------
with tab2:
    st.subheader("Current Reflection Overview")
    context = st.session_state.last_response or {}

    def render_section(title, value):
        if value:
            st.markdown(f"**{title}**")
            st.markdown(f"> {value}")

    render_section("Theme", context.get("theme"))
    render_section("Reflection", context.get("reflection_summary"))
    render_section("Momentum", context.get("momentum"))
    render_section("Change", context.get("change"))
    render_section("Consider Next", context.get("consider_next"))

    st.divider()
    st.markdown("**Session Context**")

    # Goal label: show only if present
    if context.get("goal_label"):
        st.markdown(f"`Goal:` `{context.get('goal_label')}`")

    # User profile if available
    if context.get("user_profile"):
        st.json(context.get("user_profile"))

    # Technical details from debug
    debug = context.get("debug_log", {})
    keep_keys = [
        "classified_topic",
        "emotion",
        "nuance",
        "subtopics",
        "selected_thread_score",
        "thread_continuation_reason",
        "thread_memory_hits",
    ]
    cleaned_debug = {k: v for k, v in debug.items() if k in keep_keys}

    if cleaned_debug:
        st.markdown("**Technical Details**")
        st.json(cleaned_debug)

    # ---------------------------
    # Wild Card (countdown or product reco)
    # ---------------------------
    if context.get("wild_card"):
        st.divider()
        st.subheader("🎁 Wild Card")
        with st.container(border=True):
            st.markdown(f"*{context['wild_card']}*")
