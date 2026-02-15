#!/usr/bin/env python3
"""
Helper script to call the Home Assistant Supervisor API via WebSocket.

The HA Core HTTP proxy (/api/hassio/*) restricts which Supervisor endpoints
are accessible to authenticated users.  Endpoints such as
network/interface/*/update, addons/*/install, store/repositories, etc. are
NOT whitelisted in PATHS_ADMIN and always return 401.

The WebSocket command "supervisor/api" has no such path restriction for
admin users, so we use it to reach any Supervisor endpoint.

Usage:
    python3 ha_supervisor_api.py <ha_url> <access_token> <method> <endpoint> [json_data]

    If json_data is the single character '-', JSON is read from stdin.

Examples:
    # GET request
    python3 ha_supervisor_api.py http://192.168.1.50:8123 MYTOKEN GET /network/info

    # POST request with inline JSON
    python3 ha_supervisor_api.py http://192.168.1.50:8123 MYTOKEN POST /addons/slug/start

    # POST request with JSON from stdin
    echo '{"ipv4":{"method":"static"}}' | python3 ha_supervisor_api.py \
        http://192.168.1.50:8123 MYTOKEN POST /network/interface/default/update -

Exit codes:
    0 – success (result JSON printed to stdout)
    1 – error   (error JSON or message printed to stderr)
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    # Fallback: try websocket-client (synchronous)
    import websocket  # type: ignore[no-redef]
    HAS_WEBSOCKETS = False
else:
    HAS_WEBSOCKETS = True


async def call_supervisor_api_async(
    ha_url: str,
    token: str,
    method: str,
    endpoint: str,
    data: dict | None = None,
) -> dict:
    """Call Supervisor API via HA WebSocket (async version using 'websockets')."""
    ws_url = ha_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + "/api/websocket"

    async with websockets.connect(ws_url) as ws:
        # Phase 1: receive auth_required
        msg = json.loads(await ws.recv())
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected message: {msg}")

        # Phase 2: authenticate
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        msg = json.loads(await ws.recv())
        if msg.get("type") != "auth_ok":
            raise RuntimeError(f"Authentication failed: {msg}")

        # Phase 3: send supervisor/api command
        cmd = {
            "id": 1,
            "type": "supervisor/api",
            "endpoint": endpoint,
            "method": method.lower(),
        }
        if data is not None:
            cmd["data"] = data

        await ws.send(json.dumps(cmd))
        msg = json.loads(await ws.recv())

        return msg


def call_supervisor_api_sync(
    ha_url: str,
    token: str,
    method: str,
    endpoint: str,
    data: dict | None = None,
) -> dict:
    """Call Supervisor API via HA WebSocket (sync version using 'websocket-client')."""
    ws_url = ha_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + "/api/websocket"

    ws = websocket.create_connection(ws_url)
    try:
        # Phase 1: receive auth_required
        msg = json.loads(ws.recv())
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected message: {msg}")

        # Phase 2: authenticate
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        msg = json.loads(ws.recv())
        if msg.get("type") != "auth_ok":
            raise RuntimeError(f"Authentication failed: {msg}")

        # Phase 3: send supervisor/api command
        cmd = {
            "id": 1,
            "type": "supervisor/api",
            "endpoint": endpoint,
            "method": method.lower(),
        }
        if data is not None:
            cmd["data"] = data

        ws.send(json.dumps(cmd))
        msg = json.loads(ws.recv())

        return msg
    finally:
        ws.close()


def main() -> int:
    if len(sys.argv) < 5:
        print(
            "Usage: ha_supervisor_api.py <ha_url> <access_token> <method> <endpoint> [json_data]",
            file=sys.stderr,
        )
        return 1

    ha_url = sys.argv[1]
    token = sys.argv[2]
    method = sys.argv[3]
    endpoint = sys.argv[4]

    raw_data = sys.argv[5] if len(sys.argv) > 5 else None
    if raw_data == "-":
        raw_data = sys.stdin.read()
    data = json.loads(raw_data) if raw_data else None

    try:
        if HAS_WEBSOCKETS:
            result = asyncio.run(
                call_supervisor_api_async(ha_url, token, method, endpoint, data)
            )
        else:
            result = call_supervisor_api_sync(
                ha_url, token, method, endpoint, data
            )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    if result.get("success"):
        print(json.dumps(result.get("result", {})))
        return 0
    else:
        print(json.dumps(result), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
