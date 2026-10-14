from arq import ArqRedis, create_pool

from app.services.queue.redis import get_redis_settings


async def get_queue() -> ArqRedis:
    return await create_pool(
        get_redis_settings(),
    )


async def enqueue_repository_ingestion(
    repository_id: int,
) -> str:
    redis = await get_queue()

    try:
        job = await redis.enqueue_job(
            "ingest_repository_job",
            repository_id,
        )

        if job is None:
            raise RuntimeError(
                "Repository ingestion job could not be queued."
            )

        return job.job_id

    finally:
        await redis.aclose()