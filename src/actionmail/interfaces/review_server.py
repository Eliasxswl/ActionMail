import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from actionmail.evaluation.cli import DEFAULT_MAILEX_ROOT, DEFAULT_MANIFEST
from actionmail.evaluation.review import ReviewDataset


STATIC_FILES = {
    "/": ("review_index.html", "text/html; charset=utf-8"),
    "/style.css": ("review_style.css", "text/css; charset=utf-8"),
    "/app.js": ("review_app.js", "text/javascript; charset=utf-8"),
}


def create_server(dataset: ReviewDataset, port: int = 0) -> ThreadingHTTPServer:
    class ReviewHandler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict) -> None:
            self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _allowed_host(self) -> bool:
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self) -> None:
            if not self._allowed_host():
                self._json(403, {"error": "Local access only"})
                return
            path = urlsplit(self.path).path
            try:
                if path in STATIC_FILES:
                    filename, content_type = STATIC_FILES[path]
                    content = (Path(__file__).parent / filename).read_bytes()
                    self._send(200, content, content_type)
                elif path == "/api/cases":
                    self._json(200, dataset.overview())
                elif path.startswith("/api/cases/"):
                    case_id = unquote(path.removeprefix("/api/cases/"))
                    if case_id not in dataset.rows:
                        self._json(404, {"error": "Case not found"})
                    else:
                        self._json(200, dataset.detail(case_id))
                else:
                    self._json(404, {"error": "Not found"})
            except (OSError, ValueError, KeyError) as exc:
                self._json(500, {"error": str(exc)})

        def do_POST(self) -> None:
            if not self._allowed_host() or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}":
                self._json(403, {"error": "Local access only"})
                return
            path = urlsplit(self.path).path
            if not path.startswith("/api/cases/") or not path.endswith("/review"):
                self._json(404, {"error": "Not found"})
                return
            case_id = unquote(path[len("/api/cases/"):-len("/review")])
            if case_id not in dataset.rows:
                self._json(404, {"error": "Case not found"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self._json(415, {"error": "JSON is required"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 10000:
                    raise ValueError("Review request is empty or too large")
                review = json.loads(self.rfile.read(size))
                if not isinstance(review, dict):
                    raise ValueError("Review must be a JSON object")
                saved = dataset.save_review(case_id, review)
                self._json(200, {"review": saved})
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self._json(400, {"error": str(exc)})

        def log_message(self, format: str, *args) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), ReviewHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="actionmail-review", description="Review a saved evaluation run in a local browser.")
    parser.add_argument("run_dir", type=Path, help="Directory containing run.json and cases.jsonl")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mailex-root", type=Path, default=DEFAULT_MAILEX_ROOT)
    parser.add_argument("--port", type=int, default=61933, help="Local port (default: 61933)")
    parser.add_argument("--no-browser", action="store_true", help="Print the URL without opening a browser")
    args = parser.parse_args(argv)
    try:
        dataset = ReviewDataset.open(args.run_dir, args.manifest, args.mailex_root)
        server = create_server(dataset, args.port)
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Reviewing {len(dataset.rows)} cases from {dataset.run_dir}")
        print(f"Open {url} (Ctrl+C to stop)")
        if not args.no_browser:
            webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("Review server stopped.")
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if "server" in locals():
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
