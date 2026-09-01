"""
Thin wrapper around Google's Gemini API via the official `google-genai` SDK.

Verified against current official docs (ai.google.dev/gemini-api), August
2026: uses the Interactions API (client.interactions.create), GA since
June 2026 and the currently recommended path for new projects — the older
generate_content() method still works but is now considered legacy.

IMPORTANT: Gemini is used ONLY to explain data our own deterministic
engines (technical analysis, risk, decision, news sentiment) have already
computed. It is never the source of prices or other facts, and it never
decides BUY/SELL on its own — see app/analysis/decision.py for that.
"""

import json

from google import genai

from app.config import settings

SYSTEM_INSTRUCTION = (
    "You are the SmartStock AI assistant, an explanatory layer over a "
    "deterministic stock analysis system. You will be given verified, "
    "pre-computed data (prices, technical indicators, risk scores, "
    "decision signals, news sentiment, portfolio holdings, and recent "
    "conversation history) as structured JSON. Your job is to answer the "
    "user's question or explain this data clearly in plain language, using "
    "ONLY the data given to you.\n\n"
    "Rules you must always follow:\n"
    "- Only explain the data given to you. Never invent prices, indicators, "
    "or news that are not present in the input.\n"
    "- Never guarantee future returns, and never say a stock is a "
    "guaranteed BUY or guaranteed SELL.\n"
    "- Clearly separate stated facts (the numbers given) from your own "
    "interpretation of them.\n"
    "- Mention uncertainty where relevant — markets are unpredictable.\n"
    "- Do not claim to have live market access; you only know what is in "
    "the provided data.\n"
    "- Keep the tone neutral and analytical, not hype-driven.\n"
    "- End with a brief note that this is not financial advice."
)


class GeminiError(Exception):
    """Raised when the Gemini API cannot be reached or returns an error."""


def _get_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise GeminiError(
            "GEMINI_API_KEY is not configured. Set it in .env (see Phase 10 setup instructions)."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_explanation(context: dict, user_question: str = "") -> str:
    """Ask Gemini to explain a block of structured, pre-verified data."""
    client = _get_client()

    prompt = f"Here is the verified data (JSON):\n{json.dumps(context, default=str, indent=2)}\n"
    if user_question:
        prompt += f"\nThe user asked: {user_question}\n"
    else:
        prompt += "\nExplain this data in plain language for a retail investor.\n"

    try:
        interaction = client.interactions.create(
            model=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
            input=prompt,
            generation_config={"temperature": 0.4},
        )
    except Exception as exc:
        raise GeminiError(f"Gemini API request failed: {exc}") from exc

    if not getattr(interaction, "output_text", None):
        raise GeminiError("Gemini API returned an empty response.")

    return interaction.output_text
