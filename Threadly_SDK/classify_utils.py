import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def classify_sentiment(message_text):
    prompt = f"""
You are an emotion detection system. Given the message below, classify the dominant customer emotion in ONE WORD (e.g., neutral, frustrated, angry, confused, happy, grateful).

Message: "{message_text}"

Respond in JSON with a single field:
{{"sentiment": "..."}}.
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2
        )
        text = res.choices[0].message.content.strip()
        sentiment = json.loads(text).get("sentiment", "neutral")
        return sentiment.lower()
    except Exception as e:
        print(f"[⚠️ Sentiment Error] {e}")
        return "neutral"

def classify_topic(message_text, past_topic_nuances=None):
    past_summary = ""
    if past_topic_nuances:
        past_summary = "\n".join(f"- {item}" for item in past_topic_nuances[:3])

    prompt = f"""
You are an assistant that tags journal entries with topic, nuance, and subtopics.

Message:
\"\"\"{message_text}\"\"\"

Context:
Past nuanced topics (if any):
{past_summary if past_summary else "None"}

Instructions:
- Extract the most likely primary topic (e.g., sleep, work, relationships, fitness).
- Add a 'topic_nuance' that captures what’s specific about this message.
- Extract 2–3 short subtopics (e.g., “caffeine”, “late nights”, “mood swings”) as a list.
- Decide whether the message references a past issue (true/false).

Respond only in this JSON format:
{{
  "topic": "...",
  "topic_nuance": "...",
  "subtopics": ["...", "..."],
  "reference_past_issue": true
}}
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3
        )
        parsed = json.loads(res.choices[0].message.content.strip())
        return {
            "topic": parsed.get("topic", "unknown").lower(),
            "topic_nuance": parsed.get("topic_nuance", ""),
            "subtopics": parsed.get("subtopics", []),
            "reference_past_issue": parsed.get("reference_past_issue", False)
        }
    except Exception as e:
        print(f"[⚠️ Topic Error] {e}")
        return {
            "topic": "unknown",
            "topic_nuance": "",
            "subtopics": [],
            "reference_past_issue": False
        }
