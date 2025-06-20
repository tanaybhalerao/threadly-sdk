import streamlit as st
import requests
import json

st.set_page_config(page_title="🧠 Memory Context Viewer", page_icon="🧠")
st.title("🧠 AI Memory Context System")

# Input Section
user_id = st.text_input("Enter User ID", key="user_id_input")
message = st.text_area("Enter User Message", height=150)
debug_mode = st.toggle("Debug Mode", value=False)

# Store session-level state
if "last_thread_id" not in st.session_state:
    st.session_state.last_thread_id = None

if st.button("Submit Message"):
    with st.spinner("Processing..."):
        response = requests.post("http://localhost:5050/message", json={
            "user_id": user_id,
            "message": message,
            "debug_mode": debug_mode
        })

        if response.status_code == 200:
            data = response.json()["context"]

            st.session_state.last_thread_id = data["thread_id"]

            st.subheader("📌 Context Payload")
            st.markdown(f"**User ID:** `{data['user_id']}`")
            st.markdown(f"**Thread ID:** `{data['thread_id']}`")

            st.markdown("### 🧠 Memory Summary")
            # st.info(data["memory_summary"] or "Not enough history yet.")

            st.markdown("### 🧾 User Profile")
            profile = data.get("user_profile", {})
            if profile:
                st.markdown(f"- **Dominant Emotion:** `{profile.get('dominant_emotion', 'N/A')}`")
                st.markdown(f"- **Active Topic Streak:** `{profile.get('active_topic_streak', '')}`")
                st.markdown(f"- **Repetition Count:** `{profile.get('repetition_count', 0)}`")
                st.markdown(f"- **Most Common Topic:** `{profile.get('most_common_topic', '')}`")
                st.markdown(f"- **Total Threads:** `{profile.get('total_threads', 0)}`")
                st.markdown(f"- **Unresolved Threads:** `{profile.get('unresolved_threads', 0)}`")
            else:
                st.warning("No profile available yet.")

            st.markdown("### 🚦 Metadata")
            st.markdown(f"- **Clarification Needed:** `{data['clarification_needed']}`")
            st.markdown(f"- **Refers to Past Issue:** `{data['reference_past_issue']}`")

            if debug_mode and "debug_log" in data:
                st.markdown("### 🪵 Debug Log")
                st.json(data["debug_log"])

        else:
            st.error("❌ Something went wrong. Check Flask logs or restart the backend.")

# ✅ Thread Resolution Section
st.divider()
st.subheader("✅ Resolve Current Thread")
if st.session_state.last_thread_id:
    if st.button("Mark Current Thread as Resolved"):
        with st.spinner("Resolving thread..."):
            res = requests.post("http://localhost:5050/resolve_thread", json={
                "user_id": user_id,
                "thread_id": st.session_state.last_thread_id
            })

            if res.status_code == 200:
                thread_data = res.json()
                st.success(f"Thread `{thread_data['thread_id']}` marked as resolved.")
                st.info(f"🧠 Final Summary:\n\n{thread_data['summary']}")
            else:
                st.error("❌ Failed to resolve thread.")
else:
    st.warning("⚠️ No thread to resolve. Submit a message first.")
