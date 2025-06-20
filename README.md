# Threadly SDK

A plug-and-play journaling memory engine that tracks context, emotion, and reflection patterns.

## Installation

```bash
pip install -e .
```

## Example Usage

```python
from threadly_sdk import ingest_message, summarize_memories

# Ingest a message
thread_id, is_intensifying, referenced_past, debug = ingest_message(
    user_id="demo_user",
    message_text="I’ve been waking up later ever since I started skipping workouts.",
    debug=True
)

# Summarize the user's thread memory
summary = summarize_memories(
    ["I’ve been waking up late", "Skipping workouts lately"],
    user_id="demo_user"
)
print(summary)
```

## Features

- 🧠 Thread-aware memory ingestion
- ❤️ Emotion and nuance classification
- 📝 Summarization with reflection prompts
- 🎯 Goal-labeling and journaling modes
