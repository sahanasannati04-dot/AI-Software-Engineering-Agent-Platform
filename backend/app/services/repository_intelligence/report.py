def build_repository_report(
    analysis: dict,
) -> dict:
    repository = analysis["repository"]
    languages = analysis["languages"]
    file_classification = analysis["file_classification"]
    dependencies = analysis["dependencies"]
    metadata = analysis["metadata"]
    code_intelligence = analysis["code_intelligence"]

    total_classes = 0
    total_functions = 0
    syntax_errors = []

    for file_info in code_intelligence:
        total_classes += len(
            file_info.get("classes", [])
        )

        total_functions += len(
            file_info.get("functions", [])
        )

        if file_info.get("error"):
            syntax_errors.append(
                {
                    "path": file_info["path"],
                    "error": file_info["error"],
                    "message": file_info.get(
                        "message",
                        "",
                    ),
                }
            )

    return {
        "summary": {
            "total_files": repository["file_count"],
            "total_directories": repository[
                "directory_count"
            ],
            "total_classes": total_classes,
            "total_functions": total_functions,
            "syntax_error_count": len(
                syntax_errors
            ),
        },
        "languages": languages,
        "file_classification": file_classification,
        "dependencies": dependencies,
        "metadata": metadata,
        "syntax_errors": syntax_errors,
    }