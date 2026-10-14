from app.services.tools.bug_analysis_tool import (
    prepare_bug_analysis,
)
from app.services.tools.code_explanation_tool import (
    prepare_code_explanation,
)
from app.services.tools.code_modification_tool import (
    prepare_code_modification,
)
from app.services.tools.code_search_tool import (
    search_code,
)
from app.services.tools.file_inspection_tool import (
    inspect_file,
)
from app.services.tools.modification_validation_tool import (
    validate_code_modification,
)
from app.services.tools.repository_inspection_tool import (
    inspect_repository,
)
from app.services.tools.symbol_inspection_tool import (
    inspect_symbol,
)
from app.services.tools.test_execution_tool import (
    prepare_test_execution,
)
from app.services.tools.test_generation_tool import (
    generate_test_context,
)


TOOL_REGISTRY = {
    "search_code": search_code,
    "inspect_repository": inspect_repository,
    "inspect_file": inspect_file,
    "inspect_symbol": inspect_symbol,
    "generate_test_context": generate_test_context,
    "prepare_bug_analysis": prepare_bug_analysis,
    "prepare_code_explanation": prepare_code_explanation,
    "prepare_code_modification": prepare_code_modification,
    "prepare_test_execution": prepare_test_execution,
    "validate_code_modification": validate_code_modification,
}


def get_tool(name: str):
    return TOOL_REGISTRY.get(name)


def list_tools() -> list[str]:
    return list(TOOL_REGISTRY.keys())