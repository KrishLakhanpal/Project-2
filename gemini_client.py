"""
Thin wrapper around the `google-genai` SDK (the current, supported Gemini
SDK — NOT the deprecated `google-generativeai` package) so agents don't
repeat client setup code.
"""
from google import genai
from google.genai import types

import config

_client = None


def _get_client():
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def ask(prompt: str, system_instruction: str = None, temperature: float = 0.3) -> str:
    """One-shot generation call. Returns plain text."""
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )
        return (response.text or "").strip()
    except Exception as e:
        return f"[AI ERROR] Could not reach Gemini: {e}"


def chat(history: list, new_message: str, system_instruction: str = None) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}
    Converts to the SDK's expected role names ("user"/"model").
    """
    try:
        client = _get_client()
        gemini_history = [
            types.Content(
                role="user" if h["role"] == "user" else "model",
                parts=[types.Part.from_text(text=h["content"])],
            )
            for h in history
        ]
        convo = client.chats.create(
            model=config.GEMINI_MODEL,
            history=gemini_history,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )
        response = convo.send_message(new_message)
        return (response.text or "").strip()
    except Exception as e:
        return f"[AI ERROR] Could not reach Gemini: {e}"
