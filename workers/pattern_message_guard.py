# pseudo-pattern to copy into each worker loop

message = await consumer.get_message()

incoming_request_id = message.get("request_id")
news_id = message.get("news_id")
session_id = message.get("session_id")

with bind_correlation(incoming_request_id) as corr:
    try:
        logger.info(
            "Worker message received",
            extra=build_worker_log_extra(
                event=WORKER_MESSAGE_RECEIVED,
                worker_name=WORKER_NAME,
                source=SOURCE,
                request_id=corr["request_id"],
                job_id=corr["job_id"],
                news_id=news_id,
                session_id=session_id,
            ),
        )

        # your business logic
        await process_message(message)

        logger.info(
            "Worker message processed",
            extra=build_worker_log_extra(
                event=WORKER_MESSAGE_PROCESSED,
                worker_name=WORKER_NAME,
                source=SOURCE,
                request_id=corr["request_id"],
                job_id=corr["job_id"],
                news_id=news_id,
                session_id=session_id,
            ),
        )

    except Exception:
        logger.exception(
            "Worker message processing failed",
            extra=build_worker_log_extra(
                event=WORKER_ERROR,
                worker_name=WORKER_NAME,
                source=SOURCE,
                request_id=corr["request_id"],
                job_id=corr["job_id"],
                news_id=news_id,
                session_id=session_id,
            ),
        )
        # continue loop
        continue