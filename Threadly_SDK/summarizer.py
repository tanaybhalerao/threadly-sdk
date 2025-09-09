import os
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential
from .context_summary import build_summary_prompt
from .curiosity import generate_curiosity_prompt

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def call_gpt_summary(prompt):
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

def summarize_memories(memory_list, user_id, mode = "neutral"):
    if not memory_list:
        return {
            "theme": "No theme detected yet.",
            "reflection_summary": "No journal entries to reflect on.",
            "momentum": "Hard to say without more entries.",
            "change": "Still early to detect any shift.",
            "consider_next": "Want to expand on this?",
        }

    processed = []
    for entry in memory_list:
        text = entry.strip().removeprefix("User:").strip()
        if "[Thread" in text or "[Emotion:" in text:
            processed.append(text)
        elif text.startswith("[Same Topic:"):
            processed.append(text)
        else:
            processed.append(f"{text}")

    prompt = build_summary_prompt(processed, user_id)

    try:
        raw = call_gpt_summary(prompt)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        parsed = {
            "theme": "",
            "reflection_summary": "",
            "momentum": "",
            "change": "",
            "consider_next": ""
        }

        current_section = None
        for line in lines:
            upper = line.upper()
            if upper.startswith("THEME:"):
                current_section = "theme"
                parsed["theme"] = line.split("THEME:", 1)[1].strip()
            elif upper.startswith("REFLECTION:"):
                current_section = "reflection_summary"
                parsed["reflection_summary"] = line.split("REFLECTION:", 1)[1].strip()
            elif upper.startswith("MOMENTUM:"):
                current_section = "momentum"
                parsed["momentum"] = line.split("MOMENTUM:", 1)[1].strip()
            elif upper.startswith("CHANGE:"):
                current_section = "change"
                parsed["change"] = line.split("CHANGE:", 1)[1].strip()
            elif upper.startswith("CONSIDER NEXT:"):
                current_section = "consider_next"
                parsed["consider_next"] = line.split("CONSIDER NEXT:", 1)[1].strip()
            elif current_section and line:
                parsed[current_section] += " " + line.strip()

        # Curiosity fallback
        if not parsed["consider_next"] or len(parsed["consider_next"]) < 10:
            latest_message = processed[-1]
            past_topics = []
            parsed["consider_next"] = generate_curiosity_prompt(latest_message, past_topics)

        return {
            "theme": parsed["theme"] or "Still forming.",
            "reflection_summary": parsed["reflection_summary"] or "Still early to summarize meaningfully.",
            "momentum": parsed["momentum"] or "You might be circling around something. Let’s keep watching.",
            "change": parsed["change"] or "No major shift clearly stated yet — but maybe one is starting.",
            "consider_next": parsed["consider_next"]
        }

    except Exception as e:
        return {
            "theme": "Reflection Failed",
            "reflection_summary": f"(⚠️ Couldn't generate reflection: {str(e)[:80]})",
            "momentum": "Could not analyze.",
            "change": "Could not analyze.",
            "consider_next": "Try again with more detail?"
        }
