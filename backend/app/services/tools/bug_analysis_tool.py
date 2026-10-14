from sqlalchemy.orm import Session

from app.services.tools.code_search_tool import search_code


def prepare_bug_analysis(
    db: Session,
    repository_id: int,
    bug_description: str,
    limit: int = 5,
) -> dict:
    """
    Prepare repository context for analyzing a reported bug.
    """

    if not bug_description.strip():
        return {
            "repository_id": repository_id,
            "bug_description": bug_description,
            "matches": [],
            "context": "",
        }

    matches = search_code(
        db=db,
        repository_id=repository_id,
        query=bug_description,
        limit=limit,
    )

    sections = []

    for index, match in enumerate(matches, start=1):
        location = match["path"]

        if match["start_line"] is not None:
            location += f":{match['start_line']}"

            if match["end_line"] is not None:
                location += f"-{match['end_line']}"

        sections.append(
            f"### Possible Relevant Code {index}\n"
            f"File: {location}\n"
            f"Symbol: {match['symbol_name']}\n"
            f"Relevance: {match['relevance_score']:.4f}\n\n"
            f"{match['content']}"
        )

    return {
        "repository_id": repository_id,
        "bug_description": bug_description,
        "matches": matches,
        "context": "\n\n".join(sections),
    }