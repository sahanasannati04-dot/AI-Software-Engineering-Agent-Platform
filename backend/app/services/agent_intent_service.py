import json

from app.schemas.agent_intent import (
    AgentIntent,
    IntentClassification,
)
from app.services.llm.gemini_provider import GeminiProvider


INTENT_SYSTEM_PROMPT = """
You are an intent classifier for an AI software engineering agent.

Classify the user's request into exactly one of these intents:

- general_question
- code_search
- code_explanation
- bug_analysis
- code_modification
- test_generation
- test_execution
- repository_inspection

Return ONLY valid JSON in this format:

{
  "intent": "one_allowed_intent",
  "confidence": 0.0,
  "reasoning": "short explanation"
}

Rules:
- confidence must be between 0 and 1.
- Do not include markdown.
- Do not include extra fields.
- Choose the intent that best matches the user's primary goal.
"""


def classify_intent(
    question: str,
) -> IntentClassification:

    if not question.strip():
        return IntentClassification(
            intent=AgentIntent.GENERAL_QUESTION,
            confidence=1.0,
            reasoning="The user provided an empty request.",
        )

    provider = GeminiProvider()

    response = provider.generate(
        prompt=question,
        system_prompt=INTENT_SYSTEM_PROMPT,
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid intent JSON."
        ) from exc

    try:
        return IntentClassification(
            intent=data["intent"],
            confidence=float(data["confidence"]),
            reasoning=data["reasoning"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(
            "Gemini returned an invalid intent classification."
        ) from exc