import json
import re
from pathlib import Path


def detect_dependencies(
    repository_path: str,
) -> dict[str, list[str]]:
    root = Path(repository_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repository_path}"
        )

    dependencies: dict[str, list[str]] = {}

    requirements_file = root / "requirements.txt"

    if requirements_file.exists():
        dependencies["python"] = []

        for line in requirements_file.read_text(
            encoding="utf-8"
        ).splitlines():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            package_name = re.split(
                r"[<>=!~;]",
                line,
                maxsplit=1,
            )[0].strip()

            if package_name:
                dependencies["python"].append(
                    package_name
                )

    pyproject_file = root / "pyproject.toml"

    if pyproject_file.exists():
        content = pyproject_file.read_text(
            encoding="utf-8"
        )

        python_dependencies = re.findall(
            r'^\s*"([^"]+)"\s*(?:,|\])',
            content,
            flags=re.MULTILINE,
        )

        if python_dependencies:
            dependencies.setdefault(
                "python",
                [],
            ).extend(python_dependencies)

    package_file = root / "package.json"

    if package_file.exists():
        package_data = json.loads(
            package_file.read_text(
                encoding="utf-8"
            )
        )

        node_dependencies = sorted(
            set(
                list(
                    package_data.get(
                        "dependencies",
                        {},
                    ).keys()
                )
                + list(
                    package_data.get(
                        "devDependencies",
                        {},
                    ).keys()
                )
            )
        )

        if node_dependencies:
            dependencies["node"] = node_dependencies

    for ecosystem in dependencies:
        dependencies[ecosystem] = sorted(
            set(dependencies[ecosystem])
        )

    return dependencies