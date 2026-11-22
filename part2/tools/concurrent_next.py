"""Fill an empty test queue and check that concurrent /next serves everyone once."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8182")
    args = parser.parse_args()

    def post(route, name=None):
        data = b"" if name is None else json.dumps({"name": name}).encode("utf-8")
        request = Request(
            args.url.rstrip("/") + route, data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=60) as response:
                return response.status, response.read().decode("utf-8")
        except HTTPError as error:
            with error:
                return error.code, error.read().decode("utf-8")

    names = [f"next-{i:03d}" for i in range(1, 201)]
    for ticket, name in enumerate(names, 1):
        if post("/join", name) != (200, str(ticket)):
            raise SystemExit(f"Unexpected ticket for {name}. Start with an empty test queue.")

    with ThreadPoolExecutor(max_workers=200) as pool:
        results = list(pool.map(post, ["/next"] * len(names)))

    taken = Counter(name for status, name in results if status == 200)
    wanted = Counter(names)
    final_status, final_body = post("/next")
    passed = taken == wanted and (final_status, final_body) == (404, "empty")
    print(json.dumps({
        "requests": len(results),
        "successful": taken.total(),
        "unique_names": len(taken),
        "missing": list((wanted - taken).elements()),
        "extra": list((taken - wanted).elements()),
        "final_next": {"status": final_status, "body": final_body},
        "passed": passed,
    }, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
