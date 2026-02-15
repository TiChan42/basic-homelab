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


def _ws_generic(
    ha_url: str,
    token: str,
    ws_type: str,
    data: dict | None = None,
) -> dict:
    """Send an arbitrary WebSocket command to HA (e.g. config/auth_provider/…)."""
    ws_url = ha_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + "/api/websocket"

    cmd: dict = {"id": 1, "type": ws_type}
    if data:
        cmd.update(data)

    if HAS_WEBSOCKETS:
        async def _run() -> dict:
            async with websockets.connect(ws_url) as ws:
                msg = json.loads(await ws.recv())
                if msg.get("type") != "auth_required":
                    raise RuntimeError(f"Unexpected: {msg}")
                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                msg = json.loads(await ws.recv())
                if msg.get("type") != "auth_ok":
                    raise RuntimeError(f"Auth failed: {msg}")
                await ws.send(json.dumps(cmd))
                return json.loads(await ws.recv())
        return asyncio.run(_run())
    else:
        ws_conn = websocket.create_connection(ws_url)
        try:
            msg = json.loads(ws_conn.recv())
            if msg.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected: {msg}")
            ws_conn.send(json.dumps({"type": "auth", "access_token": token}))
            msg = json.loads(ws_conn.recv())
            if msg.get("type") != "auth_ok":
                raise RuntimeError(f"Auth failed: {msg}")
            ws_conn.send(json.dumps(cmd))
            return json.loads(ws_conn.recv())
        finally:
            ws_conn.close()


def _ws_create_user(
    ha_url: str,
    token: str,
    name: str,
    username: str,
    password: str,
    group_ids: list[str] | None = None,
    local_only: bool = False,
) -> dict:
    """Create a HA user with auth credentials (two-step WebSocket flow).

    Step 1: config/auth/create          → creates the User object (returns user_id)
    Step 2: config/auth_provider/homeassistant/create → creates the login credential
    """
    if group_ids is None:
        group_ids = ["system-users"]

    ws_url = ha_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + "/api/websocket"

    def _do_sync() -> dict:
        ws_conn = websocket.create_connection(ws_url)
        try:
            msg = json.loads(ws_conn.recv())
            if msg.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected: {msg}")
            ws_conn.send(json.dumps({"type": "auth", "access_token": token}))
            msg = json.loads(ws_conn.recv())
            if msg.get("type") != "auth_ok":
                raise RuntimeError(f"Auth failed: {msg}")

            msg_id = 1

            # Step 1: Create the User object
            ws_conn.send(json.dumps({
                "id": msg_id,
                "type": "config/auth/create",
                "name": name,
                "group_ids": group_ids,
                "local_only": local_only,
            }))
            r1 = json.loads(ws_conn.recv())
            msg_id += 1

            if not r1.get("success"):
                return r1

            user_id = r1["result"]["user"]["id"]

            # Step 2: Create the auth credential
            ws_conn.send(json.dumps({
                "id": msg_id,
                "type": "config/auth_provider/homeassistant/create",
                "user_id": user_id,
                "username": username,
                "password": password,
            }))
            r2 = json.loads(ws_conn.recv())
            return r2
        finally:
            ws_conn.close()

    async def _do_async() -> dict:
        async with websockets.connect(ws_url) as ws:
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected: {msg}")
            await ws.send(json.dumps({"type": "auth", "access_token": token}))
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_ok":
                raise RuntimeError(f"Auth failed: {msg}")

            msg_id = 1

            # Step 1: Create the User object
            await ws.send(json.dumps({
                "id": msg_id,
                "type": "config/auth/create",
                "name": name,
                "group_ids": group_ids,
                "local_only": local_only,
            }))
            r1 = json.loads(await ws.recv())
            msg_id += 1

            if not r1.get("success"):
                return r1

            user_id = r1["result"]["user"]["id"]

            # Step 2: Create the auth credential
            await ws.send(json.dumps({
                "id": msg_id,
                "type": "config/auth_provider/homeassistant/create",
                "user_id": user_id,
                "username": username,
                "password": password,
            }))
            r2 = json.loads(await ws.recv())
            return r2

    if HAS_WEBSOCKETS:
        return asyncio.run(_do_async())
    else:
        return _do_sync()


def main() -> int:
    # -----------------------------------------------------------------
    # Sub-command: create-user
    # -----------------------------------------------------------------
    if len(sys.argv) >= 2 and sys.argv[1] == "create-user":
        import argparse

        p = argparse.ArgumentParser(prog="ha_supervisor_api.py create-user")
        p.add_argument("--url", required=True, help="HA base URL")
        p.add_argument("--token", required=True, help="HA access token")
        p.add_argument("--username", required=True)
        p.add_argument("--password", required=True)
        p.add_argument("--display-name", required=True)
        args = p.parse_args(sys.argv[2:])

        try:
            result = _ws_create_user(
                ha_url=args.url,
                token=args.token,
                name=args.display_name,
                username=args.username,
                password=args.password,
            )
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1

        if result.get("success"):
            print(json.dumps({"created": True, "user": args.username}))
            return 0
        else:
            err = result.get("error", {}).get("message", "unknown error")
            print(json.dumps({"created": False, "error": err}))
            if "already exists" in err.lower():
                return 0
            return 1

    # -----------------------------------------------------------------
    # Default: supervisor/api or generic ws call
    # -----------------------------------------------------------------
    if len(sys.argv) < 5:
        print(
            "Usage: ha_supervisor_api.py <ha_url> <access_token> <method> <endpoint> [json_data]\n"
            "       ha_supervisor_api.py create-user --url URL --token TOKEN ...\n"
            "\n"
            "  method can be GET/POST/etc. for supervisor/api calls,\n"
            "  or 'ws' to send a raw WebSocket command where <endpoint>\n"
            "  becomes the WS message 'type' and json_data its payload.",
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
        if method.lower() == "ws":
            # Generic WebSocket command mode – send any WS type directly
            result = _ws_generic(ha_url, token, ws_type=endpoint, data=data)
        elif HAS_WEBSOCKETS:
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
