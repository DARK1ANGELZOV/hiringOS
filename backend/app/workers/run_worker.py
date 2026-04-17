from app.core.celery_app import celery_app


def run() -> None:
    celery_app.worker_main(['worker', '--loglevel=info', '--concurrency=2', '--queues=interviews'])


if __name__ == '__main__':
    run()
