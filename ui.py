import os
os.environ["WATCHFILES_DISABLE_GLOBAL_WATCHER"] = "true"

import streamlit as st
from collections import defaultdict
from datetime import datetime
from uuid import uuid4
import requests
import pytz

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
    page_title="Threadly Journaling Demo",
    layout="wide"
)

st.title("🧵 Threadly Journaling Demo")

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    with st.expander("Under the hood", expanded=False):
        st.markdown("Adjust internal parameters here.")
        threshold = st.slider(
            "Embedding Threshold",
            min_value=0.0, max_value=1.0,
            value=0.3, step=0.01,
            help="Controls how strictly entries are linked to past reflections."
        )

# ---------------------------
# FUNCTIONS
# ---------------------------
def format_local_time(utc_time_str: str):
    try:
        utc_dt = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
        local_dt = utc_dt.astimezone(pytz.timezone("US/Pacific"))  # Auto: fallback to Pacific
        return local_dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return utc_time_str

def display_table(data: dict):
    """Display dict as a clean table instead of raw JSON."""
    rows = [{"Field": k, "Value": str(v)} for k, v in data.items()]
    st.table(rows)

def display_reflection(reflection: dict):
    st.subheader("Reflection Overview", divider="gray")

    explanations = {
        "theme": "Biggest thread tying your entries.",
        "reflection": "What you've been circling around.",
        "momentum": "Where energy is building or fading.",
        "change": "What's shifting compared to before.",
        "consider_next": "A nudge on what to explore."
    }

    for key, text in reflection.items():
        if text:
            st.markdown(f"### {key.capitalize()}")
            st.write(text)
            if key in explanations:
                st.caption(explanations[key])
            st.markdown("---")

# ---------------------------
# MAIN CHAT AREA
# ---------------------------
user_input = st.text_area("✍️ Add a journal entry", height=120, placeholder="Write your reflection here...")

col1, col2 = st.columns([3, 1])
with col1:
    if st.button("Add Reflection"):
        if user_input.strip():
            payload = {
                "user_id": st.session_state.user_id,
                "message": user_input,
                "threshold": threshold,
            }
            resp = requests.post(BACKEND_URL, json=payload)
            if resp.status_code == 200:
                st.session_state.last_response = resp.json()
                st.session_state.chat_history.append({
                    "message": user_input,
                    "response": resp.json(),
                    "timestamp": datetime.utcnow().isoformat()
                })
                st.session_state.last_message = user_input
                st.experimental_rerun()

with col2:
    if st.button("Start Over", type="primary"):
        st.session_state.chat_history = []
        st.session_state.last_response = {}
        st.session_state.last_message = ""
        st.experimental_rerun()

# ---------------------------
# DISPLAY HISTORY + REFLECTIONS
# ---------------------------
if st.session_state.chat_history:
    st.subheader("📝 Your Journal")

    for idx, entry in enumerate(st.session_state.chat_history, 1):
        local_time = format_local_time(entry["timestamp"])
        st.markdown(f"**Entry {idx} — {local_time}**")
        st.write(entry["message"])

        if "response" in entry and entry["response"]:
            reflection = entry["response"].get("reflection", {})
            if reflection:
                with st.expander("Reflection Overview", expanded=True):
                    display_reflection(reflection)

            meta = entry["response"].get("meta", {})
            if meta:
                with st.expander("Under the hood", expanded=False):
                    display_table(meta)
