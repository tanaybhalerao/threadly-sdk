import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_context_summary(memory_summary, user_message, mode="neutral"):
    if mode == "goal-tracking":
        prompt_header = """
You are a reflection assistant in a journaling app. The user is tracking a goal over time.

Speak directly to the user. Reflect what they’re expressing using small breadcrumbs across entries — not just the current message. Don’t describe “the user.” Don’t try to diagnose. Stay observational and clear.

If you offer a reflection_tip, it should gently nudge the user forward or spark introspection — not teach or motivate. You may use a Conviction Framework™ prompt only if it naturally fits the shift you observe.

Avoid assumptions. Keep it honest and dry. Don’t repeat what they already know.
"""
    else:
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

def build_summary_prompt(memories, user_id, mode="neutral"):
    if mode == "goal-tracking":
        return f"""
You are a journaling assistant. Help the user reflect on their goal by summarizing *what they wrote*, not what you think they meant.

Speak directly to them. Don’t describe them. Be minimal and observant.

If entries are related by cause, timing, or theme (e.g. sleep issues followed by caffeine changes), connect them naturally. Don’t force links, but don’t ignore obvious sequences.

Use this format:

THEME:
REFLECTION:
MOMENTUM:
CHANGE:
CONSIDER NEXT: Optionally include one Conviction Framework™ prompt if relevant.

Conviction Framework™ prompts:
- “Who is the version of you that already lives this goal?”
- “If the universe gave you a simulated version of your goal—would you still want it?”
- “What can your present self do to outsmart your future self?”
- “How will your 80-year-old self thank you—or regret this moment?”
- “If this resistance had something to teach you, what would it be?”
- “If a camera were watching—how would you act differently?”
- “What’s the comfortable lie you tell yourself—and what’s the courageous truth?”
- “What’s the cleverest way to make this effortless?”
- “If you don’t act now, what will the cost be—to others?”
- “Why does this goal matter in the grand scheme of your life?”

Journal entries:
{chr(10).join(memories)}
"""
    else:
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
