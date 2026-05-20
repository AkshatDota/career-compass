import json
import re
import time

from app.config import AI_PROVIDER, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that some models wrap JSON in."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_ai(system_prompt: str, user_prompt: str) -> dict:
    """Call the configured AI provider and return parsed JSON dict. Retries up to 3x on bad JSON."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            if AI_PROVIDER == "gemini":
                return _call_gemini(system_prompt, user_prompt)
            if AI_PROVIDER == "groq":
                return _call_groq(system_prompt, user_prompt)
            return _call_anthropic(system_prompt, user_prompt)
        except json.JSONDecodeError as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1)
        # Non-JSON errors (network, auth, rate-limit) propagate immediately
    raise last_exc  # type: ignore[misc]


# ── Provider implementations ──────────────────────────────────────────────────

def _call_anthropic(system_prompt: str, user_prompt: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return json.loads(_strip_fences(msg.content[0].text))


def _call_gemini(system_prompt: str, user_prompt: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="models/gemini-2.0-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=4096,
            temperature=0.7,
        ),
    )
    return json.loads(_strip_fences(response.text))


def _call_groq(system_prompt: str, user_prompt: str) -> dict:
    from openai import OpenAI
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
        temperature=0.7,
    )
    return json.loads(_strip_fences(response.choices[0].message.content))
