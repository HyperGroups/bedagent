import json
import threading
import unittest
import urllib.error
import urllib.request

from bedagent_web import BedagentWebHandler, ThreadingHTTPServer


class BedagentWebTests(unittest.TestCase):
    def start_server(self) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer(("127.0.0.1", 0), BedagentWebHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def test_health_endpoint(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["service"], "bedagent_web")
        finally:
            server.shutdown()

    def test_agent_page_served(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/agent/", timeout=3) as resp:
                html = resp.read().decode("utf-8")
            self.assertIn("bedagent Agent", html)
            self.assertIn("躺床写故事", html)
        finally:
            server.shutdown()

    def test_mvp_run_endpoint(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        body = json.dumps({"idea": "Draft a short design note for web agent entry.", "auto_confirm": True}).encode(
            "utf-8"
        )
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/mvp/run",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            self.assertIn("run_id", payload)
            self.assertIn("pillow_note", payload)
        finally:
            server.shutdown()

    def test_story_fragment_endpoint(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        body = json.dumps({"fragment": "主角是一个会做梦的维修AI。"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/story/fragment",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(payload["applied"])
            self.assertIn("agent_reply", payload)
            self.assertIn("维修", payload["bible"]["main_thread"])
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
