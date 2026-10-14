from app.services.tools.registry import (
    TOOL_REGISTRY,
    get_tool,
    list_tools,
)


EXPECTED_TOOLS = {
    "search_code",
    "inspect_repository",
    "inspect_file",
    "inspect_symbol",
    "generate_test_context",
    "prepare_bug_analysis",
    "prepare_code_explanation",
    "prepare_code_modification",
    "prepare_test_execution",
    "validate_code_modification",
}


def test_all_expected_tools_are_registered():
    assert set(TOOL_REGISTRY.keys()) == EXPECTED_TOOLS


def test_list_tools_returns_all_expected_tools():
    assert set(list_tools()) == EXPECTED_TOOLS


def test_get_tool_returns_registered_tool():
    for tool_name in EXPECTED_TOOLS:
        tool = get_tool(tool_name)

        assert tool is not None
        assert callable(tool)


def test_get_tool_returns_none_for_unknown_tool():
    assert get_tool("unknown_tool") is None