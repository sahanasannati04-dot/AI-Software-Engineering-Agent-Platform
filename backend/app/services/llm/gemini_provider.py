import time

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.services.llm.provider import LLMProvider


class GeminiProvider(LLMProvider):
    """
    Gemini implementation of the LLM provider interface.

    Uses Google's Interactions API for text generation.

    The Google GenAI SDK retry mechanism is disabled so that
    retry behavior is controlled by this provider.
    """

    def __init__(
        self,
        model: str = "gemini-3.8-flash",
        max_retries: int = 2,
    ):
        settings = get_settings()

        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.model = model
        self.max_retries = max_retries

        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=1,
                ),
            ),
        )

    def _is_quota_exhausted_error(
        self,
        error: Exception,
    ) -> bool:
        """
        Detect a hard quota exhaustion response.

        These errors should never be retried because the API
        explicitly indicates that the project's quota has been
        exhausted.
        """

        error_text = str(error).lower()

        quota_markers = (
            "resource_exhausted",
            "quota exceeded",
            "exceeded your current quota",
            "generate_content_free_tier_requests",
            "daily quota",
            "quota limit",
        )

        return any(
            marker in error_text
            for marker in quota_markers
        )

    def _is_retryable_error(
        self,
        error: Exception,
    ) -> bool:
        """
        Determine whether a Gemini error is likely temporary.
        """

        error_text = str(error).lower()

        retryable_markers = (
            "503",
            "service_unavailable",
            "service unavailable",
            "high demand",
            "temporarily unavailable",
            "temporary",
            "429",
            "too many requests",
            "rate limit",
        )

        return any(
            marker in error_text
            for marker in retryable_markers
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Generate a text response from Gemini.
        """

        if not prompt.strip():
            return ""

        inputs = prompt

        if system_prompt:
            inputs = (
                f"System instructions:\n"
                f"{system_prompt}\n\n"
                f"User request:\n"
                f"{prompt}"
            )

        last_error: Exception | None = None

        total_attempts = self.max_retries + 1

        for attempt in range(total_attempts):
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    input=inputs,
                )

                output_text = interaction.output_text

                if not output_text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return output_text

            except Exception as error:
                last_error = error

                if self._is_quota_exhausted_error(error):
                    raise RuntimeError(
                        "Gemini API quota has been exhausted. "
                        "Please try again after the quota resets."
                    ) from error

                if not self._is_retryable_error(error):
                    raise

                if attempt >= total_attempts - 1:
                    raise RuntimeError(
                        "Gemini service is temporarily unavailable "
                        "after multiple retry attempts."
                    ) from error

                delay = 2 ** attempt

                time.sleep(delay)

        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "Gemini generation failed unexpectedly."
        )