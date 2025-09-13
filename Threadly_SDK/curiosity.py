import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_curiosity_prompt(message_text: str, past_topics: list[str] = []) -> str:
    """
    Returns a curious follow-up question to gently clarify vague or ambiguous messages.
    """
    topic_context = f"\nPast topics user has discussed: {', '.join(past_topics)}" if past_topics else ""

    prompt = f"""
You are a journaling assistant that occasionally asks light, curious follow-up questions.

The user just wrote:
\"\"\"{message_text}\"\"\"
{topic_context}

Your job is to gently nudge them for clarification or elaboration **without assuming anything**.

Ask 1 short, human-sounding follow-up question that feels grounded in their message.
Use phrasing like:
- "Can I ask..."
- "Curious — when you say..."
- "Was that connected to..."
- "You mentioned... does it relate to..."
- "What did you mean by..."

If no good question can be asked, return a neutral check-in like:
"Want to say more about that?"

Respond only with a string. No JSON. No extra explanation.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.5,
    )

    return response.choices[0].message.content.strip()
