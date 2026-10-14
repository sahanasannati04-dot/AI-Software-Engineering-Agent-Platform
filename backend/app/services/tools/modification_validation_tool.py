from sqlalchemy.orm import Session

from app.services.modification.modification_validation_service import (
    ModificationValidationService,
)


validation_service = ModificationValidationService()


def validate_code_modification(
    db: Session,
    repository_id: int,
    modification_id: int,
    test_target: str | None = None,
) -> dict:
    """
    Validate an applied code modification by running repository tests.

    A successful validation marks the modification as validated.

    A failed validation marks the modification as validation_failed
    and signals that bug analysis should be performed.
    """

    if not isinstance(repository_id, int):
        raise ValueError(
            "repository_id must be an integer."
        )

    if not isinstance(modification_id, int):
        raise ValueError(
            "modification_id must be an integer."
        )

    if test_target is not None:
        if not isinstance(test_target, str):
            raise ValueError(
                "test_target must be a string."
            )

        test_target = test_target.strip()

        if not test_target:
            test_target = None

        if test_target is not None and "\x00" in test_target:
            raise ValueError(
                "test_target contains an invalid character."
            )

    return validation_service.validate_applied_modification(
        db=db,
        repository_id=repository_id,
        modification_id=modification_id,
        test_target=test_target,
    )