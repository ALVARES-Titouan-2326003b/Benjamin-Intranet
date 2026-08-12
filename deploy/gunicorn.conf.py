import multiprocessing
import os


bind = "0.0.0.0:8000"
workers = int(os.getenv("GUNICORN_WORKERS", str(min(multiprocessing.cpu_count() * 2 + 1, 8))))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
capture_output = True
