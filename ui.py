import os
os.environ["WATCHFILES_DISABLE_GLOBAL_WATCHER"] = "true"

import streamlit as st
from datetime import datetime
from uuid import uuid4
import requests
from zoneinfo import ZoneInfo
import time
import csv

# ---------------------------
# CONFIG
# ---------------------------
BACKEND_URL = "https://threadly-backend-sqvr.onrender.com/message"
LOG_FILE = "activity_log.csv"

# ---------------------------
# LOGGING
# ---------------------------
def log_action(user_id, action, content="", meta=None):
    try:
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.utcnow().isoformat() + "Z",
                user_id,
                action,
                content,
                str(meta) if meta else ""
            ])
    except Exception:
        pass

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
if "starter_index" not in st.session_state:
    st.session_state.starter_index = 0
if "prefill_text" not in st.session_state:
    st.session_state.prefill_text = ""
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False  # Hide debug by default

# ---------------------------
# STATIC ROASTS (5 only)
# ---------------------------
ROASTS = [
    "Yep, it’s slow. But hey messages takes time to weave.",
    "UI feels clunky? Fair. But watch how themes and changes line up.",
    "Sometimes it misses — continuity is messy, just like us.",
    "You only get 5 entries… because Thread-ly is still on training wheels.",
    "Here’s a product suggestion based on your recent entries."
]

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Thread-ly Journal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    st.title("Info")
    st.markdown("---")
    st.markdown(f"**User ID:** `{st.session_state.user_id}`")
    st.markdown(f"**Reflections used:** {len(st.session_state.chat_history)}/5")

    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] ol.nav-steps { 
            margin: 0; 
            padding-left: 1.2rem; 
        }
        section[data-testid="stSidebar"] ol.nav-steps li { 
            margin: 0 0 .35rem 0; 
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.subheader("How to Navigate")
    st.markdown(
        """
        <ol class="nav-steps">
          <li>Add your own text or click <em>Add Example Reflection</em></li>
          <li>Click <strong>Save Reflection</strong></li>
          <li>See patterns and suggestions on the right</li>
          <li>Use <strong>Start Over</strong> anytime to reset</li>
        </ol>
        """,
        unsafe_allow_html=True
    )

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
            help="Lower = more forgiving, Higher = stricter thread matching."
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
# HEADER
# ---------------------------
st.title("THREAD-LY: REFLECTIVE JOURNAL")
st.markdown(
    """
    *Thread-ly connects your reflections over time — highlighting recurring themes, shifts, and momentum.*
    """.strip()
)

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

    starter_examples = [
        "I’m trying to stick with running three times a week, but it’s hard to stay consistent.",
        "Yesterday’s run was tough, but at least I got out the door.",
        "On a totally different note, I’m debating if I should finally buy a new laptop.",
        "I wonder if getting a running watch would motivate me like a new gadget does.",
        "I spent all evening comparing laptops instead of stretching after my run."
    ]
    examples_left = st.session_state.starter_index < len(starter_examples)

    with st.form("journal_form"):
        st.text_area(
            "What’s on your mind today?",
            key="journal_input",
            height=120,
            value=st.session_state.prefill_text
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            save_clicked = st.form_submit_button("Save Reflection", use_container_width=True)
        with c2:
            example_clicked = st.form_submit_button(
                "Add Example Reflection",
                disabled=not examples_left,
                use_container_width=True
            )

        if example_clicked and examples_left:
            next_example = starter_examples[st.session_state.starter_index]
            st.session_state.prefill_text = next_example
            st.session_state.starter_index += 1
            log_action(st.session_state.user_id, "used_example", next_example)
            st.rerun()

        if save_clicked and st.session_state.journal_input.strip():
            user_msg = st.session_state.journal_input
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_msg,
                "timestamp_local": now_local_str(),
                "thread_id": "pending"
            })

            with st.empty():
                msg_area = st.empty()
                for stage in [
                    "Checking if this connects to your past entries...",
                    "Looking up similar themes...",
                    "Weaving it into your memory threads..."
                ]:
                    msg_area.info(stage)
                    time.sleep(3)

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
                    log_action(st.session_state.user_id, "add_reflection", user_msg, context)
                else:
                    st.error("Backend error. Please try again later.")
            except Exception as e:
                st.error(f"Request failed: {e}")

            st.session_state.last_message = user_msg
            st.session_state.prefill_text = ""
            st.rerun()

    st.markdown(
        """
        <style>
        div[data-testid="stButton"][id="startover"] button {
            background-color: #cc0000 !important;
            color: #ffffff !important;
            font-weight: bold;
            border-radius: 6px;
            padding: 0.5em 1em;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    if st.button("Start Over", key="startover"):
        log_action(st.session_state.user_id, "start_over")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ---------------------------
# RIGHT: REFLECTION OVERVIEW
# ---------------------------
with right:
    st.subheader("Reflection Overview")

    context = st.session_state.last_response or {}
    entry_count = len(st.session_state.chat_history)

    if 1 <= entry_count <= 5:
        roast_msg = ROASTS[entry_count - 1]
        st.markdown(
            f"""
            <div style="text-align:center; font-size:20px; font-style:italic; margin: 0 0 24px 0; color:#ffcc00;">
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
            st.markdown(
                f"""
                <div style="background: rgba(255,255,255,0.08); padding:16px; border-radius:10px; margin-top:16px;">
                    <h3 style="margin:0; padding-bottom:8px;">Product Recommendation</h3>
                    <div>{context['wild_card']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ---------------------------
    # Under the hood (hidden unless debug_mode is True)
    # ---------------------------
    if st.session_state.debug_mode:
        debug = context.get("debug_log", {})
        keep_keys = [
            "classified_topic", "emotion", "nuance", "subtopics",
            "selected_thread_score", "thread_continuation_reason",
            "thread_memory_hits", "user_entry_count", "countdown_remaining",
            "embedding_threshold_used", "best_embedding_similarity"
        ]
        cleaned_debug = {k: v for k, v in debug.items() if k in keep_keys}

        if cleaned_debug or debug.get("candidate_threads"):
            st.markdown(
                """
                <div style="background: rgba(255,255,255,0.08); padding:16px; border-radius:10px; margin-top:20px;">
                """,
                unsafe_allow_html=True
            )
            st.markdown("### Under the hood")
            if cleaned_debug:
                st.markdown("**Signals**")
                st.dataframe(dict_to_rows(cleaned_debug), use_container_width=True)

            candidate_threads = debug.get("candidate_threads", [])
            if candidate_threads:
                st.markdown("**Candidate Threads Scored**")
                st.dataframe(candidate_threads, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)
