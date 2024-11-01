web: uvicorn app.main:app --host=0.0.0.0 --port=${PORT}
worker: REDIS_URL=$REDIS_URL celery -A app.celery_app worker --loglevel=info