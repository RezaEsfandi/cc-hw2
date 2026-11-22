from time import perf_counter

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from app.queue import clean_name

BUCKETS = (0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2)
ROUTES = {"/health", "/join", "/next", "/metrics"}
QUEUE = "lab:queue"


class Metrics:
    content_type = CONTENT_TYPE_LATEST

    def __init__(self, queue_length):
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "http_requests_total", "HTTP responses", ("method", "route", "status"),
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "http_request_duration_seconds", "Time to handle an HTTP request",
            ("method", "route"), buckets=BUCKETS, registry=self.registry,
        )
        self.db_errors = Counter(
            "queue_db_errors_total", "Failed Redis operations", ("operation",),
            registry=self.registry,
        )
        self.db_duration = Histogram(
            "queue_db_operation_seconds", "Time spent in Redis calls", ("operation",),
            buckets=BUCKETS, registry=self.registry,
        )
        length = Gauge("queue_length", "Names in the shared Redis queue", registry=self.registry)
        length.set_function(queue_length)

    def record_http(self, method, path, status, elapsed):
        route = path if path in ROUTES else "unknown"
        self.requests.labels(method, route, status).inc()
        self.http_duration.labels(method, route).observe(elapsed)

    def render(self):
        return generate_latest(self.registry)


class RedisQueue:
    def __init__(self, url):
        self.client = Redis.from_url(
            url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1,
            retry=Retry(NoBackoff(), 0),
        )
        self.metrics = Metrics(self.length)

    def run(self, operation, command, *args):
        start = perf_counter()
        try:
            return command(QUEUE, *args)
        except RedisError as error:
            self.metrics.db_errors.labels(operation).inc()
            raise OSError("Redis queue unavailable") from error
        finally:
            self.metrics.db_duration.labels(operation).observe(perf_counter() - start)

    def join(self, name):
        return self.run("rpush", self.client.rpush, clean_name(name))

    def take(self):
        name = self.run("lpop", self.client.lpop)
        if name is None:
            raise LookupError("empty queue")
        return name

    def length(self):
        try:
            return self.run("llen", self.client.llen)
        except OSError:
            return float("nan")
