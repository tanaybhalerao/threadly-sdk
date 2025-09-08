import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_context_summary(memory_summary, user_message):
    prompt_header = """
You are a journaling memory engine.

Your job is to quietly track whether this new message builds on a past direction or not. Do not rely only on the latest message — look for breadcrumbs from the past.

Speak directly to the user. Never describe them in third person. Avoid therapy-speak. If something changes in tone or pace, say it briefly. If nothing is clear, say less — but never return empty fields.

Only offer a reflection_tip if there’s even a slight tonal shift or a question they might explore further. Keep it minimal. If there’s an implicit tie to something they wrote earlier (e.g., a lifestyle change possibly helping sleep), you can mention it softly — without forcing causality.
"""

    shared_prompt_body = """
Return a JSON object like this:
{
  "theme_match": true,
  "emotional_shift": "less filtered",
  "reflection_tip": "What’s shifting for you here?",
  "confidence": 0.82
}

Field guidelines:
- "theme_match": true if this entry builds on or returns to an earlier topic, mood, or pattern.
- "emotional_shift": describe tone evolution in a few words (e.g. “more neutral”, “less anxious”, “directer”, “quieter”).
- "reflection_tip": make it sound like a journal-aware nudge. Don’t explain or tell them what to do. If nothing is clear, prompt with something like “Want to say more?” or “Still about the same?” — but never leave it empty.
- Return valid JSON only. No extra text or markdown.
"""

    memory_block = memory_summary.strip() or "No prior memory available."

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.5,
        messages=[
            {"role": "system", "content": prompt_header + shared_prompt_body},
            {"role": "user", "content": f"Memory:\n{memory_block}\n\nCurrent entry:\n{user_message}"}
        ]
    )

    raw = response.choices[0].message.content.strip()
    print(f"📨 Raw GPT response: {raw}")

    cleaned = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except Exception as e:
        print("❌ Error parsing context response:", e)
        return {
            "theme_match": False,
            "emotional_shift": "unknown",
            "reflection_tip": "Let me know if this connects to anything you've been thinking about.",
            "confidence": 0.5
        }

def build_summary_prompt(memories, user_id):
    return f"""
You are a quiet summarizer for journaling entries. Your tone is dry, non-interpretive, and direct.

Speak directly to the user. Reflect only what’s repeated, shifting, or clearly stated.

If multiple entries imply a causal chain or timing link (e.g. problem + experiment), connect them simply. Don’t interpret — just order and reflect what happened.

Use this format:

THEME:
REFLECTION:
MOMENTUM:
CHANGE:
CONSIDER NEXT:

Only use “Consider Next” if the entries change tone, direction, or raise a question. But never leave it blank — even a small nudge like “Want to explore this more?” is fine.

Journal entries:
{chr(10).join(memories)}
"""
