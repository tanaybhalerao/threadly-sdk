import os
os.environ["WATCHFILES_DISABLE_GLOBAL_WATCHER"] = "true"

import streamlit as st
from datetime import datetime
from uuid import uuid4
import requests
from zoneinfo import ZoneInfo

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
if "embedding_threshold" not in st.session_state:
    st.session_state.embedding_threshold = 0.2
if "timezone" not in st.session_state:
    st.session_state.timezone = "America/Los_Angeles"

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Thread-ly Journal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# SIDEBAR (INFO)
# ---------------------------
with st.sidebar:
    st.title("Info")
    st.markdown("---")
    st.markdown(f"**User ID:** `{st.session_state.user_id}`")
    st.markdown(f"**Reflections used:** {len(st.session_state.chat_history)}/5")

    st.subheader("Settings")
    tz_options = [
        "America/Los_Angeles", "US/Eastern", "Europe/London",
        "Europe/Amsterdam", "Asia/Kolkata", "Asia/Tokyo", "Australia/Sydney"
    ]
    st.session_state.timezone = st.selectbox(
        "Timezone",
        options=tz_options,
        index=0,
        help="Controls how entry timestamps are displayed."
    )

    with st.expander("Under the hood", expanded=False):
        st.session_state.embedding_threshold = st.slider(
            "Embedding Threshold",
            min_value=0.00,
            max_value=1.00,
            value=st.session_state.embedding_threshold,
            step=0.10,
            help="Lower = more forgiving, Higher = more strict thread matching."
        )

# ---------------------------
# HELPERS
# ---------------------------
def now_local_str():
    tz = ZoneInfo(st.session_state.timezone)
    return datetime.now(tz).strftime("%b %d, %Y %I:%M %p")

def render_block(title, value):
    if value:
        st.markdown(f"### {title}")
        st.write(value)

def dict_to_rows(d):
    return [{"Field": k, "Value": v if not isinstance(v, list) else ", ".join(map(str, v))} for k, v in d.items()]

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
            for msg in st.session_state.chat_history:
                content = msg["content"]
                time_local = msg.get("timestamp_local", "")
                st.markdown(f"- {content}")
                if time_local:
                    st.caption(time_local)
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
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_msg,
                    "timestamp_local": now_local_str(),
                    "thread_id": "pending"
                })

                with st.spinner("Processing your reflection..."):
                    try:
                        response = requests.post(BACKEND_URL, json={
                            "user_id": st.session_state.user_id,
                            "message": user_msg,
                            "tags": ["demo"],
                            "debug_mode": True,
                            "demo_mode": True,
                            "goal_label": "",
                            "importance_score": 0.5,
                            "embedding_threshold": st.session_state.embedding_threshold
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

    # Start Over button (better style)
    st.markdown(
        """
        <style>
        .stButton>button.start-over {
            background-color: #e63946;
            color: white;
            font-weight: bold;
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    if st.button("Start Over", key="startover", help="Reset demo", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ---------------------------
# RIGHT: REFLECTION OVERVIEW (ENTIRE COLUMN WRAPPED)
# ---------------------------
with right:
    st.markdown(
        """
        <div style="background: rgba(255,255,255,0.05); padding:24px; border-radius:12px;">
        """,
        unsafe_allow_html=True
    )

    st.subheader("Reflection Overview")

    context = st.session_state.last_response or {}

    # Roast (centered + quote style)
    roast_msg = context.get("roast_message")
    if roast_msg:
        st.markdown(
            f"""
            <div style="text-align:center; font-size:20px; font-style:italic; margin: 0 0 24px 0;">
                “{roast_msg}”
            </div>
            """,
            unsafe_allow_html=True
        )

    col1, col2 = st.columns(2)

    with col1:
        render_block("Theme", context.get("theme"))
        render_block("Reflection", context.get("reflection_summary"))
        render_block("Momentum", context.get("momentum"))

    with col2:
        render_block("Change", context.get("change"))
        render_block("Consider Next", context.get("consider_next"))
        if context.get("wild_card"):
            st.markdown("### Product Recommendation")
            st.markdown(
                f"""
                <div style="background: rgba(255,255,255,0.12); padding:12px; border-radius:10px; margin-top:8px;">
                    {context['wild_card']}
                </div>
                """,
                unsafe_allow_html=True
            )

    # Debug log
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
        "countdown_remaining",
        "embedding_threshold_used",
        "best_embedding_similarity"
    ]
    cleaned_debug = {k: v for k, v in debug.items() if k in keep_keys}

    if cleaned_debug or debug.get("candidate_threads"):
        st.divider()
        with st.expander("Under the hood", expanded=False):
            if cleaned_debug:
                st.markdown("**Signals**")
                st.dataframe(dict_to_rows(cleaned_debug), use_container_width=True)

            candidate_threads = debug.get("candidate_threads", [])
            if candidate_threads:
                st.markdown("**Candidate Threads Scored**")
                st.dataframe(candidate_threads, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
