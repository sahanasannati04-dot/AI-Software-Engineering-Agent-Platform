from app.models.repository import Repository


class RepositoryStatusError(Exception):
    """Raised when an invalid repository status transition is requested."""


class RepositoryService:
    """
    Service responsible for repository lifecycle operations.
    """

    ALLOWED_STATUSES = {
        "pending",
        "cloning",
        "connected",
        "analyzing",
        "ready",
        "failed",
    }

    ALLOWED_TRANSITIONS = {
        "pending": {
            "cloning",
            "failed",
        },
        "cloning": {
            "connected",
            "failed",
        },
        "connected": {
            "analyzing",
            "failed",
        },
        "analyzing": {
            "ready",
            "failed",
        },
        "ready": {
            "analyzing",
            "failed",
        },
        "failed": {
            "pending",
            "cloning",
        },
    }

    def set_status(
        self,
        repository: Repository,
        new_status: str,
    ) -> Repository:
        if new_status not in self.ALLOWED_STATUSES:
            raise RepositoryStatusError(
                f"Invalid repository status: {new_status}"
            )

        current_status = repository.status

        if current_status == new_status:
            return repository

        allowed_next_statuses = self.ALLOWED_TRANSITIONS.get(
            current_status,
            set(),
        )

        if new_status not in allowed_next_statuses:
            raise RepositoryStatusError(
                f"Invalid repository status transition: "
                f"{current_status} -> {new_status}"
            )

        repository.status = new_status

        return repository

    def mark_pending(
        self,
        repository: Repository,
    ) -> Repository:
        return self.set_status(
            repository,
            "pending",
        )

    def mark_cloning(
        self,
        repository: Repository,
    ) -> Repository:
        return self.set_status(
            repository,
            "cloning",
        )

    def mark_connected(
        self,
        repository: Repository,
    ) -> Repository:
        return self.set_status(
            repository,
            "connected",
        )

    def mark_analyzing(
        self,
        repository: Repository,
    ) -> Repository:
        return self.set_status(
            repository,
            "analyzing",
        )

    def mark_ready(
        self,
        repository: Repository,
    ) -> Repository:
        return self.set_status(
            repository,
            "ready",
        )

    def mark_failed(
        self,
        repository: Repository,
    ) -> Repository:
        return self.set_status(
            repository,
            "failed",
        )
