"""Ably cloud transport embedded in the Windows barcode receiver."""

from __future__ import annotations

import asyncio
import functools
import json
import os
import platform
import ssl
import threading
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

import ably.transport.websockettransport as ably_websocket_transport
import certifi
from ably import AblyRealtime


WORKSPACE_ID = "4232a7f478a64df09506dc7919c1821b"
TOKEN_URL = "https://asi-barkod-pwa.vercel.app/api/ably-token"
RECONNECT_SECONDS = 5


ABLY_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
if not getattr(ably_websocket_transport.ws_connect, "_asi_certifi_tls", False):
    _original_ws_connect = ably_websocket_transport.ws_connect

    @functools.wraps(_original_ws_connect)
    def _certifi_ws_connect(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("ssl", ABLY_SSL_CONTEXT)
        return _original_ws_connect(*args, **kwargs)

    _certifi_ws_connect._asi_certifi_tls = True  # type: ignore[attr-defined]
    ably_websocket_transport.ws_connect = _certifi_ws_connect


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / "AsiBarkod"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_processed(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [str(item) for item in payload if str(item)]
    except (OSError, ValueError, TypeError):
        pass
    return []


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(str(temp), str(path))


@dataclass
class JobResult:
    delivered: bool
    error: str = ""
    local_ms: int = 0


class CloudBridge:
    def __init__(
        self,
        *,
        receiver_id: str,
        receiver_name: str,
        publish: Callable[[str, str, dict[str, Any]], Awaitable[None]],
        forward: Callable[[dict[str, Any]], JobResult],
        processed_path: Path | None = None,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self.receiver_id = receiver_id
        self.receiver_name = receiver_name
        self.publish = publish
        self.forward = forward
        self.processed_path = processed_path or (app_data_dir() / "cloud_processed_jobs.json")
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.processed_order = read_processed(self.processed_path)
        self.processed = set(self.processed_order)
        self.process_lock: asyncio.Lock | None = None

    @property
    def prefix(self) -> str:
        return f"asi-barkod:{WORKSPACE_ID}"

    @property
    def discovery_channel(self) -> str:
        return f"{self.prefix}:discovery"

    @property
    def scan_channel(self) -> str:
        return f"{self.prefix}:receiver:{self.receiver_id}"

    def receiver_payload(self, response_to: str = "") -> dict[str, Any]:
        payload = {
            "id": self.receiver_id,
            "name": self.receiver_name,
            "online": True,
            "lastSeen": self.now_ms(),
            "host": platform.node(),
            "transport": "ably",
        }
        if response_to:
            payload["responseTo"] = response_to
        return payload

    async def announce(self, response_to: str = "") -> None:
        await self.publish(
            self.discovery_channel,
            "receiver",
            self.receiver_payload(response_to),
        )

    def remember_processed(self, job_id: str) -> None:
        if job_id not in self.processed:
            self.processed_order.append(job_id)
        self.processed_order = self.processed_order[-1000:]
        self.processed = set(self.processed_order)
        atomic_write_json(self.processed_path, self.processed_order)

    async def handle_scan(self, message_data: Any) -> None:
        if isinstance(message_data, str):
            try:
                job = json.loads(message_data)
            except ValueError:
                return
        elif isinstance(message_data, dict):
            job = message_data
        else:
            return

        job_id = str(job.get("id", "")).strip()
        reply_channel = str(job.get("replyChannel", "")).strip()
        if not job_id or not reply_channel.startswith(f"{self.prefix}:client:"):
            return

        if self.process_lock is None:
            self.process_lock = asyncio.Lock()
        async with self.process_lock:
            received_at = self.now_ms()
            if job_id in self.processed:
                await self.publish(
                    reply_channel,
                    "delivery",
                    {
                        "id": job_id,
                        "receiverId": self.receiver_id,
                        "status": "delivered",
                        "deliveredAt": self.now_ms(),
                        "recoveredAck": True,
                    },
                )
                return

            loop = asyncio.get_running_loop()
            started = time.perf_counter()
            result = await loop.run_in_executor(None, self.forward, job)
            local_ms = result.local_ms or int((time.perf_counter() - started) * 1000)
            if result.delivered:
                self.remember_processed(job_id)

            await self.publish(
                reply_channel,
                "delivery",
                {
                    "id": job_id,
                    "receiverId": self.receiver_id,
                    "status": "delivered" if result.delivered else "error",
                    "error": None if result.delivered else result.error,
                    "receivedAt": received_at,
                    "deliveredAt": self.now_ms() if result.delivered else None,
                    "localMs": local_ms,
                    "phoneToBridgeMs": max(
                        0,
                        received_at - int(job.get("createdAt", received_at)),
                    ),
                },
            )


class CloudBridgeRuntime:
    def __init__(
        self,
        *,
        receiver_id: str,
        receiver_name: str,
        forward: Callable[[dict[str, Any]], JobResult],
        status: Callable[[str], None],
        connection_state: Callable[[bool], None] | None = None,
    ) -> None:
        self.status = status
        self.connection_state = connection_state or (lambda _connected: None)
        client_id = f"receiver-{receiver_id}"
        auth_url = f"{TOKEN_URL}?clientId={urllib.parse.quote(client_id)}"
        self.ably = AblyRealtime(
            auth_url=auth_url,
            client_id=client_id,
            auto_connect=True,
        )
        self.bridge = CloudBridge(
            receiver_id=receiver_id,
            receiver_name=receiver_name,
            publish=self.publish,
            forward=forward,
        )
        self.stop_event = asyncio.Event()

    async def publish(
        self,
        channel_name: str,
        event_name: str,
        payload: dict[str, Any],
    ) -> None:
        channel = self.ably.channels.get(channel_name)
        await channel.publish(event_name, payload)

    async def run(self) -> None:
        def on_connection_state(change: Any) -> None:
            # This is an Ably socket event, not a periodic internet check.
            current = str(getattr(change, "current", "")).lower()
            self.connection_state(current == "connected")

        self.ably.connection.on(on_connection_state)
        discovery = self.ably.channels.get(self.bridge.discovery_channel)
        scans = self.ably.channels.get(self.bridge.scan_channel)

        def on_discovery(message: Any) -> None:
            if getattr(message, "name", "") != "discover":
                return
            data = getattr(message, "data", {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except ValueError:
                    data = {}
            request_id = str(data.get("requestId", "")) if isinstance(data, dict) else ""
            asyncio.create_task(self.bridge.announce(request_id))

        def on_scan(message: Any) -> None:
            if getattr(message, "name", "") == "scan":
                asyncio.create_task(
                    self.bridge.handle_scan(getattr(message, "data", None)),
                )

        await discovery.subscribe(on_discovery)
        await scans.subscribe(on_scan)
        self.connection_state(True)
        self.status("Ably bulut baglantisi hazir; PC arama istegi bekleniyor")
        try:
            await self.stop_event.wait()
        finally:
            await self.ably.close()


class CloudBridgeService:
    def __init__(
        self,
        *,
        receiver_id: str,
        receiver_name: str,
        forward: Callable[[dict[str, Any]], JobResult],
        status: Callable[[str], None],
        connection_state: Callable[[bool], None] | None = None,
    ) -> None:
        self.receiver_id = receiver_id
        self.receiver_name = receiver_name
        self.forward = forward
        self.status = status
        self.connection_state = connection_state or (lambda _connected: None)
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.runtime: CloudBridgeRuntime | None = None
        self.stop_requested = threading.Event()

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_requested.clear()
        self.thread = threading.Thread(
            target=self._thread_main,
            daemon=True,
            name="AsiBarkodCloudBridge",
        )
        self.thread.start()

    def _thread_main(self) -> None:
        while not self.stop_requested.is_set():
            try:
                asyncio.run(self._run())
            except Exception as exc:
                self.connection_state(False)
                self.status(f"Bulut baglantisi hatasi: {exc}")
            finally:
                self.loop = None
                self.runtime = None
            if self.stop_requested.wait(RECONNECT_SECONDS):
                break
            self.connection_state(False)
            self.status("Bulut baglantisi yeniden deneniyor")

    async def _run(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.runtime = CloudBridgeRuntime(
            receiver_id=self.receiver_id,
            receiver_name=self.receiver_name,
            forward=self.forward,
            status=self.status,
            connection_state=self.connection_state,
        )
        self.status("Bulut baglantisi kuruluyor")
        await self.runtime.run()

    def stop(self) -> None:
        self.stop_requested.set()
        self.connection_state(False)
        if self.loop and self.runtime:
            self.loop.call_soon_threadsafe(self.runtime.stop_event.set)
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=5)
        self.thread = None
        self.loop = None
        self.runtime = None
