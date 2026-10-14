from app.services.tools.tool_schemas import TOOL_SCHEMAS


EXPECTED_TOOLS = {
    "code_search",
    "repository_inspection",
    "file_inspection",
    "symbol_inspection",
    "test_generation",
    "bug_analysis",
    "code_explanation",
    "code_modification",
    "test_execution",
    "modification_validation",
}


def test_all_expected_tools_are_registered_in_schemas():
    assert set(TOOL_SCHEMAS.keys()) == EXPECTED_TOOLS


def test_all_schemas_have_required_metadata():
    for tool_name, schema in TOOL_SCHEMAS.items():
        assert schema["name"] == tool_name
        assert isinstance(schema["description"], str)
        assert schema["description"].strip()

        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"


def test_all_schemas_have_properties():
    for schema in TOOL_SCHEMAS.values():
        parameters = schema["parameters"]

        assert "properties" in parameters
        assert isinstance(parameters["properties"], dict)
        assert parameters["properties"]


def test_required_parameters_exist_in_properties():
    for schema in TOOL_SCHEMAS.values():
        parameters = schema["parameters"]

        required = parameters.get("required", [])
        properties = parameters["properties"]

        for parameter in required:
            assert parameter in properties


def test_modification_validation_schema_is_safe():
    schema = TOOL_SCHEMAS["modification_validation"]

    properties = schema["parameters"]["properties"]

    assert "repository_id" in properties
    assert "modification_id" in properties
    assert "test_target" in properties

    assert schema["parameters"]["required"] == [
        "repository_id",
        "modification_id",
    ]