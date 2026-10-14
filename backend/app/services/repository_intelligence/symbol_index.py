def build_symbol_index(
    code_intelligence: list[dict],
) -> dict:
    index = {
        "classes": {},
        "functions": {},
    }

    for file_info in code_intelligence:
        file_path = file_info["path"]

        for class_name in file_info.get(
            "classes",
            [],
        ):
            index["classes"].setdefault(
                class_name,
                [],
            ).append(file_path)

        for function_name in file_info.get(
            "functions",
            [],
        ):
            index["functions"].setdefault(
                function_name,
                [],
            ).append(file_path)

    return index