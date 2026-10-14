from pathlib import Path


def detect_repository_metadata(
    repository_path: str,
) -> dict[str, bool]:
    root = Path(repository_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repository_path}"
        )

    files = {
        path.name.lower()
        for path in root.iterdir()
        if path.is_file()
    }

    directories = {
        path.name.lower()
        for path in root.iterdir()
        if path.is_dir()
    }

    return {
        "is_git_repository": ".git" in directories,
        "has_readme": any(
            name.startswith("readme")
            for name in files
        ),
        "has_gitignore": ".gitignore" in files,
        "has_dockerfile": "dockerfile" in files,
        "has_docker_compose": (
            "docker-compose.yml" in files
            or "docker-compose.yaml" in files
        ),
        "has_github_actions": (
            ".github" in directories
            and any(
                path.name.lower() == "workflows"
                for path in (root / ".github").iterdir()
                if path.is_dir()
            )
        ),
        "has_python_project": (
            "requirements.txt" in files
            or "pyproject.toml" in files
            or "setup.py" in files
        ),
        "has_node_project": "package.json" in files,
    }