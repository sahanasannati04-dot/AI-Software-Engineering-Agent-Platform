from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
import os
import tempfile


class CodeModificationError(Exception):
    """Base exception for code modification operations."""


class CodeModificationValidationError(CodeModificationError):
    """Raised when a modification request is invalid."""


class CodeModificationFileError(CodeModificationError):
    """Raised when a repository file cannot be accessed."""


class CodeModificationConflictError(CodeModificationError):
    """Raised when the target file changed before modification."""


@dataclass
class ProposedModification:
    """
    Represents a proposed repository modification.

    The modification is not applied automatically.
    """

    repository_path: str
    file_path: str
    original_content: str
    proposed_content: str
    diff: str


@dataclass
class AppliedModification:
    """
    Represents a successfully applied repository modification.

    The original content is retained so the modification can
    be rolled back safely.
    """

    repository_path: str
    file_path: str
    original_content: str
    applied_content: str
    diff: str


class CodeModificationService:
    """
    Safely prepares, applies, and rolls back repository
    code modifications.

    Responsibilities:
    - Validate repository paths.
    - Prevent path traversal outside the repository.
    - Read existing files.
    - Validate proposed content.
    - Generate unified diffs.
    - Apply changes atomically.
    - Detect concurrent file changes.
    - Roll back an applied modification.
    """

    def _validate_repository_path(
        self,
        repository_path: str,
    ) -> Path:
        if not isinstance(repository_path, str):
            raise CodeModificationValidationError(
                "repository_path must be a string."
            )

        repository_path = repository_path.strip()

        if not repository_path:
            raise CodeModificationValidationError(
                "repository_path is required."
            )

        path = Path(repository_path).resolve()

        if not path.exists():
            raise CodeModificationFileError(
                "Repository path does not exist."
            )

        if not path.is_dir():
            raise CodeModificationFileError(
                "Repository path must be a directory."
            )

        return path

    def _validate_file_path(
        self,
        repository_path: Path,
        file_path: str,
    ) -> Path:
        if not isinstance(file_path, str):
            raise CodeModificationValidationError(
                "file_path must be a string."
            )

        file_path = file_path.strip()

        if not file_path:
            raise CodeModificationValidationError(
                "file_path is required."
            )

        candidate = Path(file_path)

        if candidate.is_absolute():
            raise CodeModificationValidationError(
                "file_path must be relative to the repository."
            )

        if "\x00" in file_path:
            raise CodeModificationValidationError(
                "file_path contains an invalid character."
            )

        repository_root = repository_path.resolve()
        resolved_file = (
            repository_root / candidate
        ).resolve()

        try:
            resolved_file.relative_to(repository_root)
        except ValueError as exc:
            raise CodeModificationValidationError(
                "file_path must remain inside the repository."
            ) from exc

        return resolved_file

    def read_file(
        self,
        repository_path: str,
        file_path: str,
    ) -> str:
        """
        Read a repository file without modifying it.
        """

        repository_root = self._validate_repository_path(
            repository_path
        )

        resolved_file = self._validate_file_path(
            repository_root,
            file_path,
        )

        if not resolved_file.exists():
            raise CodeModificationFileError(
                "Target file does not exist."
            )

        if not resolved_file.is_file():
            raise CodeModificationFileError(
                "Target path is not a file."
            )

        try:
            return resolved_file.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError as exc:
            raise CodeModificationFileError(
                "Target file is not a valid UTF-8 text file."
            ) from exc
        except OSError as exc:
            raise CodeModificationFileError(
                f"Unable to read target file: {exc}"
            ) from exc

    def generate_diff(
        self,
        file_path: str,
        original_content: str,
        proposed_content: str,
    ) -> str:
        """
        Generate a unified diff between the original and
        proposed file contents.
        """

        if not isinstance(original_content, str):
            raise CodeModificationValidationError(
                "original_content must be a string."
            )

        if not isinstance(proposed_content, str):
            raise CodeModificationValidationError(
                "proposed_content must be a string."
            )

        if original_content == proposed_content:
            return ""

        diff_lines = unified_diff(
            original_content.splitlines(keepends=True),
            proposed_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )

        return "".join(diff_lines)

    def prepare_modification(
        self,
        repository_path: str,
        file_path: str,
        proposed_content: str,
    ) -> ProposedModification:
        """
        Prepare a modification proposal.

        This method ONLY reads the existing file and creates
        a proposed diff. It never writes to disk.
        """

        if not isinstance(proposed_content, str):
            raise CodeModificationValidationError(
                "proposed_content must be a string."
            )

        repository_root = self._validate_repository_path(
            repository_path
        )

        self._validate_file_path(
            repository_root,
            file_path,
        )

        original_content = self.read_file(
            repository_path=str(repository_root),
            file_path=file_path,
        )

        diff = self.generate_diff(
            file_path=file_path,
            original_content=original_content,
            proposed_content=proposed_content,
        )

        return ProposedModification(
            repository_path=str(repository_root),
            file_path=file_path,
            original_content=original_content,
            proposed_content=proposed_content,
            diff=diff,
        )

    def _atomic_write(
        self,
        target_file: Path,
        content: str,
    ) -> None:
        """
        Atomically replace a file using a temporary file in
        the same directory.

        Writing to a temporary file first prevents a partial
        write from corrupting the target file.
        """

        parent_directory = target_file.parent

        temporary_path: Path | None = None

        try:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target_file.name}.",
                suffix=".tmp",
                dir=str(parent_directory),
                text=True,
            )

            os.close(file_descriptor)

            temporary_path = Path(temporary_name)

            temporary_path.write_text(
                content,
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                target_file,
            )

            temporary_path = None

        except OSError as exc:
            raise CodeModificationFileError(
                f"Unable to write target file: {exc}"
            ) from exc

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(
                        missing_ok=True
                    )
                except OSError:
                    pass

    def apply_modification(
        self,
        proposal: ProposedModification,
    ) -> AppliedModification:
        """
        Apply a previously prepared modification.

        Before writing, the service verifies that the target
        file still contains the exact content used to create
        the proposal.

        This prevents overwriting another change that happened
        after the proposal was generated.
        """

        if not isinstance(
            proposal,
            ProposedModification,
        ):
            raise CodeModificationValidationError(
                "proposal must be a ProposedModification."
            )

        repository_root = self._validate_repository_path(
            proposal.repository_path
        )

        target_file = self._validate_file_path(
            repository_root,
            proposal.file_path,
        )

        if not target_file.exists():
            raise CodeModificationFileError(
                "Target file does not exist."
            )

        if not target_file.is_file():
            raise CodeModificationFileError(
                "Target path is not a file."
            )

        current_content = self.read_file(
            repository_path=str(repository_root),
            file_path=proposal.file_path,
        )

        if current_content != proposal.original_content:
            raise CodeModificationConflictError(
                "Target file changed after the modification "
                "proposal was created. Modification was not applied."
            )

        if (
            proposal.original_content
            == proposal.proposed_content
        ):
            return AppliedModification(
                repository_path=str(repository_root),
                file_path=proposal.file_path,
                original_content=proposal.original_content,
                applied_content=proposal.proposed_content,
                diff="",
            )

        self._atomic_write(
            target_file=target_file,
            content=proposal.proposed_content,
        )

        return AppliedModification(
            repository_path=str(repository_root),
            file_path=proposal.file_path,
            original_content=proposal.original_content,
            applied_content=proposal.proposed_content,
            diff=proposal.diff,
        )

    def rollback_modification(
        self,
        modification: AppliedModification,
    ) -> None:
        """
        Roll back a previously applied modification.

        Rollback only succeeds if the current file still contains
        the content that this modification applied.

        This prevents rollback from accidentally deleting a newer
        change made after the modification.
        """

        if not isinstance(
            modification,
            AppliedModification,
        ):
            raise CodeModificationValidationError(
                "modification must be an AppliedModification."
            )

        repository_root = self._validate_repository_path(
            modification.repository_path
        )

        target_file = self._validate_file_path(
            repository_root,
            modification.file_path,
        )

        if not target_file.exists():
            raise CodeModificationFileError(
                "Target file does not exist."
            )

        if not target_file.is_file():
            raise CodeModificationFileError(
                "Target path is not a file."
            )

        current_content = self.read_file(
            repository_path=str(repository_root),
            file_path=modification.file_path,
        )

        if current_content != modification.applied_content:
            raise CodeModificationConflictError(
                "Target file changed after the modification was "
                "applied. Rollback was not performed."
            )

        self._atomic_write(
            target_file=target_file,
            content=modification.original_content,
        )