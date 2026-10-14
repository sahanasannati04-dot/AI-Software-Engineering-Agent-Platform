from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Abstract interface for Large Language Model providers.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Generate a text response from the LLM.
        """
        raise NotImplementedError