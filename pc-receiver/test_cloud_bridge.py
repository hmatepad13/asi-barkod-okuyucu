import asyncio
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cloud_bridge
from cloud_bridge import CloudBridge, CloudBridgeService, JobResult


class CloudBridgeTests(unittest.TestCase):
    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def test_announcement_contains_only_ably_receiver_details(self):
        published = []

        async def publish(channel, name, payload):
            published.append((channel, name, payload))

        with tempfile.TemporaryDirectory() as temp:
            bridge = CloudBridge(
                receiver_id="pc-1",
                receiver_name="HASTAKABUL",
                publish=publish,
                forward=lambda job: JobResult(True),
                processed_path=Path(temp) / "processed.json",
                now_ms=lambda: 1000,
            )
            self.run_async(bridge.announce("request-1"))

        payload = published[0][2]
        self.assertEqual(payload["transport"], "ably")
        self.assertNotIn("localUrls", payload)
        self.assertEqual(payload["responseTo"], "request-1")

    def test_successful_scan_is_forwarded_once_and_acknowledged(self):
        published = []
        forwarded = []

        async def publish(channel, name, payload):
            published.append((channel, name, payload))

        def forward(job):
            forwarded.append(job)
            return JobResult(True, local_ms=12)

        with tempfile.TemporaryDirectory() as temp:
            bridge = CloudBridge(
                receiver_id="pc-1",
                receiver_name="HASTAKABUL",
                publish=publish,
                forward=forward,
                processed_path=Path(temp) / "processed.json",
                now_ms=lambda: 2000,
            )
            job = {
                "id": "scan-1",
                "data": "010123",
                "createdAt": 1900,
                "replyChannel": f"{bridge.prefix}:client:phone-1",
            }
            self.run_async(bridge.handle_scan(job))
            self.run_async(bridge.handle_scan(job))

        self.assertEqual(len(forwarded), 1)
        self.assertEqual(published[0][2]["status"], "delivered")
        self.assertEqual(published[0][2]["localMs"], 12)
        self.assertTrue(published[1][2]["recoveredAck"])

    def test_unrelated_reply_channel_is_ignored(self):
        published = []

        async def publish(channel, name, payload):
            published.append(payload)

        with tempfile.TemporaryDirectory() as temp:
            bridge = CloudBridge(
                receiver_id="pc-1",
                receiver_name="PC",
                publish=publish,
                forward=lambda job: JobResult(True),
                processed_path=Path(temp) / "processed.json",
            )
            self.run_async(
                bridge.handle_scan(
                    {"id": "scan-1", "replyChannel": "unrelated"},
                ),
            )

        self.assertEqual(published, [])

    def test_ably_websocket_uses_certifi_tls_context(self):
        self.assertEqual(cloud_bridge.ABLY_SSL_CONTEXT.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(
            getattr(
                cloud_bridge.ably_websocket_transport.ws_connect,
                "_asi_certifi_tls",
                False,
            ),
        )

    def test_service_retries_after_connection_failure(self):
        statuses = []
        service = CloudBridgeService(
            receiver_id="pc-1",
            receiver_name="PC",
            forward=lambda job: JobResult(True),
            status=statuses.append,
        )
        attempts = 0

        def fake_asyncio_run(coroutine):
            nonlocal attempts
            attempts += 1
            coroutine.close()
            if attempts == 1:
                raise RuntimeError("offline")
            service.stop_requested.set()

        with mock.patch.object(cloud_bridge, "RECONNECT_SECONDS", 0), mock.patch.object(
            cloud_bridge.asyncio,
            "run",
            side_effect=fake_asyncio_run,
        ):
            service._thread_main()

        self.assertEqual(attempts, 2)
        self.assertIn("Bulut baglantisi hatasi: offline", statuses)
        self.assertIn("Bulut baglantisi yeniden deneniyor", statuses)


if __name__ == "__main__":
    unittest.main()
