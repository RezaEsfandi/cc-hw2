"""Check the Redis HTTP contract on an empty test queue."""

import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8185")
    base = parser.parse_args().url.rstrip("/")

    def request(route, method="POST", name=None):
        body = json.dumps({"name": name}, ensure_ascii=False).encode() if name is not None else None
        req = Request(
            base + route, data=body, method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, response.read().decode()
        except HTTPError as error:
            with error:
                return error.code, error.read().decode()

    assert request("/health", "GET") == (200, "ok")
    assert request("/next") == (404, "empty")
    for invalid in ("", " " * 7, "x" * 41, "Ali\nSara"):
        assert request("/join", name=invalid) == (400, "invalid name")
    assert request("/next") == (404, "empty")
    assert request("/join", name="   Ali   ") == (200, "1")
    assert request("/join", name="Sara") == (200, "2")
    assert request("/next") == (200, "Ali")
    assert request("/join", name="Nima") == (200, "2")
    assert request("/next") == (200, "Sara")
    assert request("/next") == (200, "Nima")
    assert request("/next") == (404, "empty")
    print("Redis: health, validation, FIFO, ticket length and empty queue passed.")


if __name__ == "__main__":
    main()
