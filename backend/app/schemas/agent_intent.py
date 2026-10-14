from enum import Enum

from pydantic import BaseModel


class AgentIntent(str, Enum):
    GENERAL_QUESTION = "general_question"
    CODE_SEARCH = "code_search"
    CODE_EXPLANATION = "code_explanation"
    BUG_ANALYSIS = "bug_analysis"
    CODE_MODIFICATION = "code_modification"
    TEST_GENERATION = "test_generation"
    TEST_EXECUTION = "test_execution"
    REPOSITORY_INSPECTION = "repository_inspection"


class IntentClassification(BaseModel):
    intent: AgentIntent
    confidence: float
    reasoning: str