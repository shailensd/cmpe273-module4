#!/usr/bin/env python3
"""Inventory Service for the Module 4 distributed-store assignment."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from urllib.parse import parse_qs, urlparse


DEFAULT_INVENTORY = {
    "keyboard": 10,
    "mouse": 5,
    "monitor": 0,
}


def json_response(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class InventoryHandler(BaseHTTPRequestHandler):
    inventory = DEFAULT_INVENTORY.copy()

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API name
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            json_response(self, 200, {"service": "inventory", "status": "ok"})
            return

        if parsed.path != "/availability":
            json_response(self, 404, {"error": "route not found"})
            return

        params = parse_qs(parsed.query)
        item_id = params.get("item_id", [""])[0].strip()
        quantity_text = params.get("quantity", [""])[0]
        try:
            quantity = int(quantity_text)
        except ValueError:
            json_response(self, 400, {"error": "quantity must be an integer"})
            return

        if not item_id or quantity < 1:
            json_response(self, 400, {"error": "item_id is required and quantity must be positive"})
            return

        available_quantity = self.inventory.get(item_id, 0)
        json_response(
            self,
            200,
            {
                "item_id": item_id,
                "requested_quantity": quantity,
                "available_quantity": available_quantity,
                "available": available_quantity >= quantity,
            },
        )

    def log_message(self, format, *args):
        print(f"[inventory] {self.address_string()} - {format % args}", flush=True)


def main():
    port = int(os.getenv("INVENTORY_PORT", "8001"))
    server = ThreadingHTTPServer(("127.0.0.1", port), InventoryHandler)
    print(f"Inventory Service listening on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nInventory Service stopped", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
