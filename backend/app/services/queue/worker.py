import signal

from arq.connections import RedisSettings

from app.services.queue.redis import get_redis_settings
from app.services.queue.repository_jobs import ingest_repository_job


# ARQ expects Unix signals that do not exist on Windows.
# Map them to Windows-supported signals so worker shutdown
# remains compatible with the development environment.
if not hasattr(signal, "SIGUSR1"):
    signal.SIGUSR1 = signal.SIGINT

if not hasattr(signal, "SIGUSR2"):
    signal.SIGUSR2 = signal.SIGTERM


async def health_check_job(ctx) -> dict:
    return {
        "status": "ok",
        "message": "ARQ worker is running.",
    }


class WorkerSettings:
    functions = [
        health_check_job,
        ingest_repository_job,
    ]

    redis_settings: RedisSettings = get_redis_settings()

    queue_name = "ai-engineering-platform"

    max_jobs = 5

    job_timeout = 1800