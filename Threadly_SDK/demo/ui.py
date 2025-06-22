import streamlit as st
import requests
from collections import defaultdict
from datetime import datetime
from Threadly_SDK.demo.config import BASE_URL, USER_ID, HEADERS

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Thread-ly Journal",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    html, body, .stApp {
        background-color: #1b1a19 !important;
        color: #e9e4dc !important;
    }

    textarea, input {
        background-color: #2c2b2a !important;
        color: #e9e4dc !important;
        border: 1px solid #444;
    }

    .stTextArea > div > div > textarea {
        font-family: 'Georgia', serif;
        font-size: 16px;
        line-height: 1.5;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, h4 {
        color: #f0e9d6 !important;
    }

    .stButton > button {
        background-color: #444 !important;
        color: #fff !important;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 6px;
        font-size: 16px;
        margin-top: 0.5rem;
        transition: background-color 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #666 !important;
    }

    .stMarkdown, .stTextInput, .stTextArea {
        color: #f0e9d6 !important;
    }

    .st-bd {
        background-color: #2a2927 !important;
    }

    .entry-header {
        font-weight: 600;
        font-size: 15px;
        margin-top: 16px;
        margin-bottom: 4px;
        color: #f0e9d6;
    }

    .timestamp {
        font-size: 12px;
        color: #999;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# SESSION STATE INIT
# ---------------------------
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
if "goal_label" not in st.session_state:
    st.session_state.goal_label = ""

# ---------------------------
# SIDEBAR CONTROLS
# ---------------------------
with st.sidebar:
    st.title("Settings")
    st.session_state.goal_label = st.text_input("Goal (optional)", value=st.session_state.goal_label)
    st.session_state.mode = st.selectbox("Response Mode", ["Neutral", "Goal-Tracking"], index=0)
    st.session_state.debug = st.toggle("Debug Mode", value=st.session_state.debug)

    if st.button("Reset Journal"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ---------------------------
# MAIN LAYOUT
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
                st.markdown(f"<div class='entry-header'>Thread {tid}</div>", unsafe_allow_html=True)
                for msg in messages:
                    time = msg.get("timestamp", "")
                    content = msg["content"]
                    st.markdown(f"<div style='padding-left: 10px;'>{content}</div>", unsafe_allow_html=True)
                    if time:
                        st.markdown(f"<div class='timestamp' style='padding-left: 10px;'>{time}</div>", unsafe_allow_html=True)
        else:
            st.write("No entries yet. Start by reflecting on something.")

    st.divider()
    st.subheader("Add Reflection")

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
            payload = {
                "user_id": USER_ID,
                "message": user_msg,
                "tags": [],
                "goal_label": st.session_state.goal_label,
                "mode": st.session_state.mode.lower(),
                "debug_mode": st.session_state.debug,
            }
            res = requests.post(f"{BASE_URL}/message", json=payload, headers=HEADERS)

            if res.ok:
                try:
                    data = res.json()
                    st.session_state.last_response = data
                    thread_id = data.get("context", {}).get("thread_id")
                    st.session_state.chat_history[-1]["thread_id"] = thread_id
                except Exception:
                    st.error("Response could not be parsed.")
                    st.text(res.text)
                st.session_state.last_message = user_msg
                st.rerun()
            else:
                st.error("Couldn’t connect to backend.")
                st.text(res.text)

# ---------------------------
# RIGHT: REFLECTION SUMMARY
# ---------------------------
with right:
    st.subheader("Current Reflection Overview")

    context = {}
    if isinstance(st.session_state.last_response, dict):
        context = st.session_state.last_response.get("context", {})
    else:
        st.warning("Unexpected response format:")
        st.text(st.session_state.last_response)

    if context:
        def render_section(title, value):
            st.markdown(f"**{title}**")
            st.markdown(f"<div style='margin-bottom: 16px; padding-left: 10px;'>{value or 'N/A'}</div>", unsafe_allow_html=True)

        render_section("Theme", context.get("theme"))
        render_section("Reflection", context.get("reflection_summary"))
        render_section("Momentum", context.get("momentum"))
        render_section("Change", context.get("change"))
        render_section("Consider Next", context.get("consider_next"))

        st.divider()
        st.markdown("**Behavioral Insight**")
        insight = context.get("behavioral_insight")
        if insight:
            st.markdown(f"<div style='padding: 12px; background-color: #2a2927; border-radius: 8px;'>{insight}</div>", unsafe_allow_html=True)
        else:
            st.write("Not enough reflection history to generate insight.")

        st.markdown("**Session Context**")
        st.markdown(f"`Thread ID:` `{context.get('thread_id', 'N/A')}`")
        st.markdown(f"`Goal:` `{context.get('goal_label', 'N/A')}`")
        st.markdown(f"`Mode:` `{context.get('mode', 'neutral')}`")

        if st.session_state.debug:
            with st.expander("Internal Debug Log"):
                st.json(context.get("debug_log", {}))

# ---------------------------
# FOOTER: TOPICS
# ---------------------------
st.divider()
st.subheader("Topics You've Reflected On")

topics = context.get("topic_list", [])
if topics:
    st.markdown(", ".join(f"`{t}`" for t in topics))
else:
    st.write("You haven’t reflected on enough topics yet.")
