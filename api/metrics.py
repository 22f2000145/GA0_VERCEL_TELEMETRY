import json
from http.server import BaseHTTPRequestHandler
from api.data import TELEMETRY

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
    "Access-Control-Max-Age": "86400",
    "Content-Type": "application/json",
}


def p95(values):
    if not values:
        return 0.0
    s = sorted(values)
    idx = (len(s) - 1) * 0.95
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def mean(values):
    return sum(values) / len(values) if values else 0.0


def r(n):
    return round(n, 3)


def compute(regions, threshold):
    out = {}
    for reg in regions:
        rows = [t for t in TELEMETRY if t["region"] == reg]
        lat = [t["latency_ms"] for t in rows]
        out[reg] = {
            "avg_latency": r(mean(lat)),
            "p95_latency": r(p95(lat)),
            "avg_uptime": r(mean([t["uptime_pct"] for t in rows])),
            "breaches": len([l for l in lat if l > threshold]),
        }
    return out


class handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for name, value in CORS_HEADERS.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(204)

    def do_GET(self):
        self.send_json(200, {"status": "ok"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            requested = body.get("regions", [])
            regions = [str(value) for value in requested] if isinstance(requested, list) else []
            threshold = float(body.get("threshold_ms", 180))
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(400, {"error": "Invalid JSON"})
            return

        result = compute(regions, threshold)
        self.send_json(200, {"regions": result, **result})
