from sqlalchemy.orm import Session

from app.services.tools.symbol_inspection_tool import inspect_symbol


def prepare_code_explanation(
    db: Session,
    repository_id: int,
    symbol_name: str,
) -> dict:
    """
    Prepare repository context for explaining a specific symbol.
    """

    result = inspect_symbol(
        db=db,
        repository_id=repository_id,
        symbol_name=symbol_name,
    )

    if not result["exists"]:
        return {
            "repository_id": repository_id,
            "symbol_name": symbol_name,
            "exists": False,
            "context": "",
        }

    sections = []

    for match in result["matches"]:
        location = match["path"]

        if match["start_line"] is not None:
            location += f":{match['start_line']}"

            if match["end_line"] is not None:
                location += f"-{match['end_line']}"

        sections.append(
            f"File: {location}\n"
            f"Symbol: {match['symbol_name']}\n"
            f"Type: {match['chunk_type']}\n\n"
            f"{match['content']}"
        )

    return {
        "repository_id": repository_id,
        "symbol_name": symbol_name,
        "exists": True,
        "context": "\n\n".join(sections),
    }