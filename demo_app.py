import streamlit as st
import requests

# ---------------------------
# CONFIGURATION
# ---------------------------
BASE_URL = "http://localhost:5050"
USER_ID = "tanay_001"
HEADERS = {"Content-Type": "application/json"}

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
st.sidebar.title("Settings")
st.session_state.goal_label = st.sidebar.text_input("Goal (optional)", value=st.session_state.goal_label)
st.session_state.mode = st.sidebar.selectbox("Response Mode", ["Neutral", "Goal-Tracking"], index=0)
st.session_state.debug = st.sidebar.toggle("Debug Mode", value=st.session_state.debug)

if st.sidebar.button("Reset Session"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ---------------------------
# MAIN LAYOUT
# ---------------------------
st.title("Journaling Memory System")

left, right = st.columns(2)

# ---------------------------
# LEFT: Journal Entry + History
# ---------------------------
with left:
    st.header("Journal")

    st.markdown("#### Entry History")
    for msg in st.session_state.chat_history:
        st.markdown(f"- {msg['content']}")

    st.markdown("---")
    st.markdown("#### New Entry")

    with st.form("journal_form"):
        user_msg = st.text_area("Write your thoughts here", key="journal_input", height=120)
        submit = st.form_submit_button("Submit Entry")

        if submit and user_msg.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_msg})
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
                st.session_state.last_response = res.json()
                st.session_state.last_message = user_msg
                st.rerun()
            else:
                st.error("Failed to send message. Is the backend running?")

# ---------------------------
# RIGHT: Summary + Profile
# ---------------------------
with right:
    st.header("Reflection Summary")

    if st.session_state.last_response:
        context = st.session_state.last_response.get("context", {})

        def render_section(title, value):
            st.markdown(f"#### {title}")
            st.markdown(f"> {value or 'N/A'}")

        render_section("Theme", context.get("theme"))
        render_section("Reflection", context.get("reflection_summary"))
        render_section("Momentum", context.get("momentum"))
        render_section("Change", context.get("change"))
        render_section("Consider Next", context.get("consider_next"))

        st.markdown("---")
        st.markdown("#### User Profile")
        st.json(context.get("user_profile", {}))

        st.markdown("#### Technical Details")
        st.markdown(f"`Thread ID:` `{context.get('thread_id', 'N/A')}`")
        st.markdown(f"`Goal:` `{context.get('goal_label', 'N/A')}`")
        st.markdown(f"`References Past Issue:` `{context.get('reference_past_issue', False)}`")
        st.markdown(f"`Mode:` `{context.get('mode', 'neutral')}`")

        if st.session_state.debug:
            with st.expander("Debug Log"):
                st.json(context.get("debug_log", {}))
    else:
        st.info("Add a journal entry to begin.")
