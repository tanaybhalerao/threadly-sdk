from summarizer import summarize_memories

memories = [
    "User: I still haven’t gotten my refund. Agent: Let me check that for you.",
    "User: Why is my payment taking so long? Agent: It may be delayed 24 hours.",
    "User: This is the second time this happened! Agent: I understand your frustration.",
    "User: I got the refund now, thanks. Agent: Glad to help!"
]

summary = summarize_memories(memories, user_id="tanay_001")
print("\n🧠 Memory Summary:\n", summary)
