TOOL_SCHEMAS = {
    "code_search": {
        "name": "code_search",
        "description": (
            "Search the indexed repository codebase for relevant "
            "files, symbols, functions, classes, or code patterns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID to search.",
                },
                "query": {
                    "type": "string",
                    "description": "Natural-language or code search query.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results.",
                    "default": 10,
                },
            },
            "required": [
                "repository_id",
                "query",
            ],
        },
    },

    "repository_inspection": {
        "name": "repository_inspection",
        "description": (
            "Inspect repository metadata, structure, status, "
            "workspace information, and indexed code statistics."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID to inspect.",
                },
            },
            "required": [
                "repository_id",
            ],
        },
    },

    "file_inspection": {
        "name": "file_inspection",
        "description": (
            "Inspect the contents and metadata of a specific file "
            "inside the repository."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Relative path of the file.",
                },
            },
            "required": [
                "repository_id",
                "file_path",
            ],
        },
    },

    "symbol_inspection": {
        "name": "symbol_inspection",
        "description": (
            "Inspect a specific function, class, method, or other "
            "code symbol inside the repository."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID.",
                },
                "symbol_name": {
                    "type": "string",
                    "description": "Symbol name to inspect.",
                },
                "file_path": {
                    "type": "string",
                    "description": (
                        "Optional file path containing the symbol."
                    ),
                },
            },
            "required": [
                "repository_id",
                "symbol_name",
            ],
        },
    },

    "test_generation": {
        "name": "test_generation",
        "description": (
            "Generate automated tests for repository code "
            "based on the requested functionality."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID.",
                },
                "target": {
                    "type": "string",
                    "description": (
                        "Function, class, file, or feature for "
                        "which tests should be generated."
                    ),
                },
            },
            "required": [
                "repository_id",
                "target",
            ],
        },
    },

    "bug_analysis": {
        "name": "bug_analysis",
        "description": (
            "Analyze repository code for potential bugs, failures, "
            "exceptions, or incorrect behavior."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID.",
                },
                "target": {
                    "type": "string",
                    "description": (
                        "File, function, class, error, or behavior "
                        "to analyze."
                    ),
                },
            },
            "required": [
                "repository_id",
                "target",
            ],
        },
    },

    "code_explanation": {
        "name": "code_explanation",
        "description": (
            "Explain repository code, architecture, logic, "
            "dependencies, or execution flow."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID.",
                },
                "target": {
                    "type": "string",
                    "description": (
                        "Code element, file, symbol, or architectural "
                        "component to explain."
                    ),
                },
            },
            "required": [
                "repository_id",
                "target",
            ],
        },
    },

    "code_modification": {
        "name": "code_modification",
        "description": (
            "Safely understand, prepare, apply, or rollback a controlled "
            "code modification in a repository. The workflow should "
            "prefer understanding the target and preparing a proposed "
            "change before applying it. Modifications produce a diff, "
            "validate repository-relative paths, detect concurrent file "
            "changes, and support rollback."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID.",
                },
                "target": {
                    "type": "string",
                    "description": (
                        "File, function, class, feature, or code area "
                        "that should be modified."
                    ),
                },
                "instruction": {
                    "type": "string",
                    "description": (
                        "Natural-language instruction describing the "
                        "requested code modification."
                    ),
                },
                "modification_request": {
                    "type": "string",
                    "description": (
                        "Natural-language description of the requested "
                        "code change. This is the normalized modification "
                        "request used internally by the modification "
                        "workflow."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of repository search results "
                        "used when building modification context."
                    ),
                    "default": 5,
                },
                "operation": {
                    "type": "string",
                    "enum": [
                        "context",
                        "prepare",
                        "apply",
                        "rollback",
                    ],
                    "description": (
                        "Modification workflow operation. Use context "
                        "to understand the relevant code, prepare to "
                        "create a proposed change and diff, apply only "
                        "an explicitly prepared change, and rollback "
                        "an explicitly applied change."
                    ),
                    "default": "context",
                },
                "file_path": {
                    "type": "string",
                    "description": (
                        "Repository-relative path of the file being "
                        "modified. Required for prepare, apply, and "
                        "rollback operations."
                    ),
                },
                "proposed_content": {
                    "type": "string",
                    "description": (
                        "Complete proposed file content. Required for "
                        "prepare and apply operations."
                    ),
                },
                "original_content": {
                    "type": "string",
                    "description": (
                        "Original file content captured when the "
                        "modification was prepared. Required for apply "
                        "and rollback operations. Do not invent it."
                    ),
                },
                "applied_content": {
                    "type": "string",
                    "description": (
                        "File content that was applied by the modification. "
                        "Required for rollback. Do not invent it."
                    ),
                },
                "diff": {
                    "type": "string",
                    "description": (
                        "Unified diff associated with the prepared or "
                        "applied modification. Preserve it when available."
                    ),
                },
                "modification_id": {
                    "type": "integer",
                    "description": (
                        "Persisted modification ID returned by the "
                        "prepare operation."
                    ),
                },
            },
            "required": [
                "repository_id",
                "target",
                "instruction",
            ],
        },
    },

    "test_execution": {
        "name": "test_execution",
        "description": (
            "Execute repository tests inside an isolated sandbox "
            "and return structured test results including exit code, "
            "stdout, stderr, pass/fail status, and timeout status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": (
                        "Absolute or configured workspace path of "
                        "the repository to test."
                    ),
                },
                "test_target": {
                    "type": "string",
                    "description": (
                        "Optional pytest target such as a test file, "
                        "directory, test class, or test function."
                    ),
                },
            },
            "required": [
                "repository_path",
            ],
        },
    },

    "modification_validation": {
        "name": "modification_validation",
        "description": (
            "Validate an already-applied code modification by "
            "automatically running repository tests. If tests pass, "
            "the modification is marked validated. If tests fail or "
            "time out, the modification is marked validation_failed "
            "and the result signals that bug analysis should follow."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repository_id": {
                    "type": "integer",
                    "description": "Repository ID.",
                },
                "modification_id": {
                    "type": "integer",
                    "description": (
                        "Persisted code modification ID returned "
                        "by the prepare/apply workflow."
                    ),
                },
                "test_target": {
                    "type": "string",
                    "description": (
                        "Optional pytest target to validate, such as "
                        "a test file, directory, class, or function."
                    ),
                },
            },
            "required": [
                "repository_id",
                "modification_id",
            ],
        },
    },
}