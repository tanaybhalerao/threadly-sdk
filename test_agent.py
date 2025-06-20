from summarizer import summarize_memories
from prompt_agent import respond_to_user

# Fake past memory
memories = [
    "User: I asked for a refund two days ago. Agent: It’s still processing.",
    "User: This delay is really annoying. Agent: I understand, we’re looking into it.",
    "User: Okay I got it. Thanks. Agent: Happy to help!"
]

summary = summarize_memories(memories, user_id="tanay_001")
response = respond_to_user(summary, "Why does this happen so often?")

print("🧠 Memory Summary:\n", summary)
print("\n🤖 Agent Response:\n", response)
