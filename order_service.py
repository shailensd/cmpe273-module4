#!/usr/bin/env python3
"""Order Service for the Module 4 distributed-store assignment."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid


INVENTORY_URL = os.getenv("INVENTORY_URL", "http://127.0.0.1:8001")
ORDERS = []


def json_response(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def ask_inventory(item_id, quantity):
    query = urllib.parse.urlencode({"item_id": item_id, "quantity": quantity})
    request = urllib.request.Request(f"{INVENTORY_URL}/availability?{query}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ConnectionError("Inventory Service is unavailable") from error


class OrderHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API name
        if self.path == "/health":
            json_response(self, 200, {"service": "order", "status": "ok"})
            return
        if self.path == "/orders":
            json_response(self, 200, {"orders": ORDERS})
            return
        json_response(self, 404, {"error": "route not found"})

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API name
        if self.path != "/orders":
            json_response(self, 404, {"error": "route not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            item_id = str(payload.get("item_id", "")).strip()
            quantity = int(payload.get("quantity", 0))
        except (ValueError, TypeError, json.JSONDecodeError):
            json_response(self, 400, {"error": "body must be JSON with item_id and integer quantity"})
            return

        if not item_id or quantity < 1:
            json_response(self, 400, {"error": "item_id is required and quantity must be positive"})
            return

        try:
            availability = ask_inventory(item_id, quantity)
        except ConnectionError as error:
            json_response(self, 503, {"error": str(error), "dependency": "inventory"})
            return

        if not availability.get("available", False):
            json_response(
                self,
                409,
                {
                    "error": "item unavailable",
                    "item_id": item_id,
                    "requested_quantity": quantity,
                    "available_quantity": availability.get("available_quantity", 0),
                },
            )
            return

        order = {
            "order_id": str(uuid.uuid4()),
            "item_id": item_id,
            "quantity": quantity,
            "status": "created",
        }
        ORDERS.append(order)
        json_response(self, 201, order)

    def log_message(self, format, *args):
        print(f"[order] {self.address_string()} - {format % args}", flush=True)


def main():
    port = int(os.getenv("ORDER_PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), OrderHandler)
    print(f"Order Service listening on http://127.0.0.1:{port}", flush=True)
    print(f"Inventory dependency: {INVENTORY_URL}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nOrder Service stopped", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
