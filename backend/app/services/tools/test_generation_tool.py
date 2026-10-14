from sqlalchemy.orm import Session

from app.services.tools.symbol_inspection_tool import inspect_symbol


def generate_test_context(
    db: Session,
    repository_id: int,
    symbol_name: str,
) -> dict:
    """
    Retrieve the implementation of a symbol and prepare
    structured context for test generation.
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
            "test_context": "",
        }

    sections = []

    for match in result["matches"]:
        sections.append(
            f"File: {match['path']}\n"
            f"Symbol: {match['symbol_name']}\n"
            f"Lines: {match['start_line']}-{match['end_line']}\n\n"
            f"{match['content']}"
        )

    return {
        "repository_id": repository_id,
        "symbol_name": symbol_name,
        "exists": True,
        "test_context": "\n\n".join(sections),
    }