"""HTTP API for the lab queue.

Bodies are plain text, not JSON:
  GET  /health                  200  ok
  POST /join   {"name": "..."}  200  ticket number, or 400 if the name is rejected
  POST /next                    200  name, or 404 empty

Listen on PORT (default 8000). The queue file is DATA_DIR/queue.txt
(DATA_DIR defaults to /data). main() must bind 0.0.0.0 so the published
port is reachable. serve() must use the host it is given.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.queue import join, take


class QueueServer(ThreadingHTTPServer):
    request_queue_size = 256


def serve(host: str, port: int, data_dir: str) -> None:
    """Listen until the process is stopped. Use join and take from app.queue."""
    path = Path(data_dir) / "queue.txt"
    path.parent.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status: int, text: str) -> None:
            payload = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            if self.path == "/health":
                self.reply(200, "ok")
            else:
                self.reply(404, "not found")

        def join_queue(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("invalid body length")
                data = json.loads(self.rfile.read(length))
                ticket = join(path, data["name"])
            except (KeyError, TypeError, ValueError):
                self.reply(400, "invalid name")
                return
            self.reply(200, str(ticket))

        def next_name(self) -> None:
            try:
                name = take(path)
            except LookupError:
                self.reply(404, "empty")
                return
            self.reply(200, name)

        def do_POST(self) -> None:
            if self.path == "/join":
                self.join_queue()
            elif self.path == "/next":
                self.next_name()
            else:
                self.reply(404, "not found")

    with QueueServer((host, port), Handler) as server:
        server.serve_forever()


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    data_dir = os.environ.get("DATA_DIR", "/data")
    serve("0.0.0.0", port, data_dir)


if __name__ == "__main__":
    main()
