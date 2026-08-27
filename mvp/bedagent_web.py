#!/usr/bin/env python3
"""bedagent local web server: static site + JSON API for agent UI."""

from __future__ import annotations

import argparse
import base64
import cgi
import json
import mimetypes
import shutil
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MVP_DIR = Path(__file__).resolve().parent
REPO_ROOT = MVP_DIR.parent
SITE_DIR = REPO_ROOT / "site"
STORY_ROOT = REPO_ROOT / ".bedagent" / "stories"
MEMORY_JOURNAL = REPO_ROOT / ".bedagent" / "memory" / "journal.ndjson"
PRODUCT_MILESTONE = "v0.11.0-mvp"


def ensure_mvp_path() -> None:
    if str(MVP_DIR) not in sys.path:
        sys.path.insert(0, str(MVP_DIR))


def json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def convert_to_wav_if_needed(source: Path) -> Path:
    if source.suffix.lower() == ".wav":
        return source
    if shutil.which("ffmpeg"):
        target = source.with_suffix(".wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(source), str(target)],
            check=True,
            capture_output=True,
        )
        return target
    raise RuntimeError(
        f"Audio format '{source.suffix}' requires ffmpeg for conversion to wav. "
        "Install ffmpeg or upload wav/mp3."
    )


class BedagentWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/health":
            ensure_mvp_path()
            from llm_adapter import llm_status

            json_response(
                self,
                200,
                {
                    "ok": True,
                    "service": "bedagent_web",
                    "site_root": str(SITE_DIR),
                    "voice_available": bool(__import__("os").environ.get("DASHSCOPE_API_KEY")),
                    "llm": llm_status(),
                    "product_milestone": PRODUCT_MILESTONE,
                    "features": [
                        "story-resume",
                        "story-expand",
                        "story-memory",
                        "unified-search",
                        "quiet-tts",
                        "character-sheet",
                        "voice-stream",
                        "voice-story-loop",
                        "voice-status",
                    ],
                },
            )
            return
        if path in {"/agent", "/agent/"}:
            self.path = "/agent/index.html"
            super().do_GET()
            return
        if path == "/api/story/list":
            self.handle_story_list()
            return
        if path == "/api/story/latest":
            self.handle_story_latest()
            return
        if path == "/api/story/search":
            self.handle_story_search(parsed.query)
            return
        if path == "/api/search":
            self.handle_unified_search(parsed.query)
            return
        if path == "/api/voice/status":
            self.handle_voice_status()
            return
        if path.startswith("/api/story/") and path.endswith("/characters") and path.count("/") == 4:
            story_id = path.split("/")[3]
            self.handle_story_characters(story_id)
            return
        if path.startswith("/api/story/") and path.count("/") == 3:
            story_id = path.split("/")[-1]
            if story_id not in {"list", "search", "latest", "fragment", "answer", "draft", "export"}:
                self.handle_story_get(story_id)
                return
            super().do_GET()
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        ensure_mvp_path()

        if parsed.path == "/api/mvp/run":
            self.handle_mvp_run()
            return
        if parsed.path == "/api/story/fragment":
            self.handle_story_fragment()
            return
        if parsed.path == "/api/story/answer":
            self.handle_story_answer()
            return
        if parsed.path == "/api/story/search":
            self.handle_story_search_post()
            return
        if parsed.path == "/api/story/draft":
            self.handle_story_draft()
            return
        if parsed.path == "/api/story/export":
            self.handle_story_export()
            return
        if parsed.path == "/api/search":
            self.handle_unified_search_post()
            return
        if parsed.path == "/api/voice/transcribe":
            self.handle_voice_transcribe()
            return
        if parsed.path == "/api/voice/speak":
            self.handle_voice_speak()
            return
        if parsed.path == "/api/voice/story":
            self.handle_voice_story()
            return

        json_response(self, 404, {"error": f"Unknown path: {parsed.path}"})

    def handle_mvp_run(self) -> None:
        from bedagent_mvp import run_closed_loop

        try:
            payload = read_json_body(self)
            idea = str(payload.get("idea", "")).strip()
            if not idea:
                json_response(self, 400, {"error": "idea is required"})
                return
            manifest = run_closed_loop(
                idea=idea,
                output_root=REPO_ROOT / payload.get("output_root", ".bedagent/runs"),
                auto_confirm=bool(payload.get("auto_confirm", True)),
                non_interactive=bool(payload.get("non_interactive", False)),
                blanket_policy_path=REPO_ROOT / payload.get("blanket_policy", "mvp/blanket_policy.json"),
                sandbox_adapter=str(payload.get("sandbox_adapter", "simulated")),
                memory_journal_path=REPO_ROOT / payload.get("memory_journal", ".bedagent/memory/journal.ndjson"),
                git_repo_root=REPO_ROOT / payload.get("git_repo_root", "."),
                allow_side_effects=bool(payload.get("allow_side_effects", False)),
            )
            json_response(
                self,
                200,
                {
                    "run_id": manifest["run_id"],
                    "risk": manifest["plan"]["risk"]["level"],
                    "approved": manifest["confirm"]["approved"],
                    "act_status": manifest["act"]["status"],
                    "pillow_note": manifest["report"]["pillow_note"],
                },
            )
        except Exception as exc:  # pragma: no cover - API guardrail
            json_response(self, 500, {"error": str(exc)})

    def handle_story_list(self) -> None:
        ensure_mvp_path()
        from story_session import list_story_sessions

        items = list_story_sessions(STORY_ROOT)
        json_response(self, 200, {"items": items})

    def handle_story_get(self, story_id: str) -> None:
        ensure_mvp_path()
        from story_session import load_story_state, resolve_story_paths

        paths = resolve_story_paths(STORY_ROOT, story_id, None)
        if not paths.root.exists():
            json_response(self, 404, {"error": f"story not found: {story_id}"})
            return
        session, bible = load_story_state(paths, None)
        json_response(self, 200, {"story_id": story_id, "session": session, "bible": bible})

    def handle_story_search(self, query_string: str) -> None:
        ensure_mvp_path()
        from urllib.parse import parse_qs

        from story_session import search_stories

        params = parse_qs(query_string)
        query = (params.get("q") or params.get("query") or [""])[0]
        if not query.strip():
            json_response(self, 400, {"error": "q is required"})
            return
        hits = search_stories(STORY_ROOT, query, top_k=int((params.get("top_k") or ["3"])[0]))
        json_response(self, 200, {"query": query, "hits": hits})

    def handle_story_search_post(self) -> None:
        ensure_mvp_path()
        from story_session import search_stories

        try:
            payload = read_json_body(self)
            query = str(payload.get("query") or payload.get("q") or "").strip()
            if not query:
                json_response(self, 400, {"error": "query is required"})
                return
            hits = search_stories(
                STORY_ROOT,
                query,
                top_k=int(payload.get("top_k", 3)),
                min_score=float(payload.get("min_score", 0.0)),
            )
            json_response(self, 200, {"query": query, "hits": hits})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_unified_search(self, query_string: str) -> None:
        ensure_mvp_path()
        from urllib.parse import parse_qs

        from bedagent_mvp import unified_search

        params = parse_qs(query_string)
        query = (params.get("q") or params.get("query") or [""])[0]
        if not query.strip():
            json_response(self, 400, {"error": "q is required"})
            return
        hits = unified_search(
            query=query,
            journal_path=MEMORY_JOURNAL,
            story_root=STORY_ROOT,
            top_k=int((params.get("top_k") or ["5"])[0]),
            min_score=float((params.get("min_score") or ["0"])[0]),
        )
        json_response(self, 200, {"query": query, "hits": hits})

    def handle_unified_search_post(self) -> None:
        ensure_mvp_path()
        from bedagent_mvp import unified_search

        try:
            payload = read_json_body(self)
            query = str(payload.get("query") or payload.get("q") or "").strip()
            if not query:
                json_response(self, 400, {"error": "query is required"})
                return
            hits = unified_search(
                query=query,
                journal_path=MEMORY_JOURNAL,
                story_root=STORY_ROOT,
                top_k=int(payload.get("top_k", 5)),
                min_score=float(payload.get("min_score", 0.0)),
            )
            json_response(self, 200, {"query": query, "hits": hits})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_story_latest(self) -> None:
        ensure_mvp_path()
        from story_session import latest_story_session, load_story_state, resolve_story_paths

        latest = latest_story_session(STORY_ROOT)
        if not latest:
            json_response(self, 404, {"error": "no story sessions"})
            return
        paths = resolve_story_paths(STORY_ROOT, latest["story_id"], None)
        session, bible = load_story_state(paths, None)
        json_response(self, 200, {"story_id": latest["story_id"], "session": session, "bible": bible})

    def handle_story_characters(self, story_id: str) -> None:
        ensure_mvp_path()
        from story_session import build_character_sheet, load_story_state, resolve_story_paths

        paths = resolve_story_paths(STORY_ROOT, story_id, None)
        if not paths.root.exists():
            json_response(self, 404, {"error": f"story not found: {story_id}"})
            return
        session, bible = load_story_state(paths, None)
        json_response(
            self,
            200,
            {
                "story_id": story_id,
                "characters": bible.get("characters", []),
                "sheet": build_character_sheet(bible),
                "session": session,
            },
        )

    def _load_story_or_404(self, story_id: str | None, title: str | None = None):
        from story_session import load_story_state, resolve_story_paths

        if not story_id:
            return None, None, None, "story_id is required"
        paths = resolve_story_paths(STORY_ROOT, story_id, title)
        if not paths.root.exists():
            return None, None, None, f"story not found: {story_id}"
        session, bible = load_story_state(paths, title)
        return paths, session, bible, None

    def handle_story_draft(self) -> None:
        ensure_mvp_path()
        from story_session import build_story_drafts

        try:
            payload = read_json_body(self)
            paths, session, bible, error = self._load_story_or_404(payload.get("story_id"), payload.get("title"))
            if error:
                json_response(self, 404 if "not found" in error else 400, {"error": error})
                return
            result = build_story_drafts(
                paths,
                bible,
                session,
                expand=bool(payload.get("expand", False)),
                use_llm=bool(payload.get("use_llm", False)),
                night=bool(payload.get("night", False)),
            )
            json_response(
                self,
                200,
                {
                    "story_id": paths.root.name,
                    "chapter_number": result["chapter_number"],
                    "pillow_note": result.get("pillow_note", ""),
                    "outline": result.get("outline", ""),
                    "sketch": result.get("sketch", ""),
                    "prose": result.get("prose", ""),
                    "characters": result.get("characters", ""),
                    "outline_path": result.get("outline_path"),
                    "chapter_sketch_path": result.get("chapter_sketch_path"),
                    "prose_path": result.get("prose_path", ""),
                    "llm": result.get("llm"),
                },
            )
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_story_export(self) -> None:
        ensure_mvp_path()
        from story_session import export_story

        try:
            payload = read_json_body(self)
            paths, session, bible, error = self._load_story_or_404(payload.get("story_id"), payload.get("title"))
            if error:
                json_response(self, 404 if "not found" in error else 400, {"error": error})
                return
            result = export_story(paths, bible, session)
            json_response(
                self,
                200,
                {
                    "story_id": paths.root.name,
                    "story_bible_path": result["story_bible_path"],
                    "transcript_path": result["transcript_path"],
                    "story_bible": Path(result["story_bible_path"]).read_text(encoding="utf-8"),
                    "transcript": Path(result["transcript_path"]).read_text(encoding="utf-8"),
                },
            )
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_story_fragment(self) -> None:
        from story_session import load_story_state, process_fragment, resolve_story_paths

        try:
            payload = read_json_body(self)
            fragment = str(payload.get("fragment", "")).strip()
            if not fragment:
                json_response(self, 400, {"error": "fragment is required"})
                return
            title = payload.get("title")
            story_id = payload.get("story_id")
            paths = resolve_story_paths(STORY_ROOT, story_id, title)
            paths.root.mkdir(parents=True, exist_ok=True)
            session, bible = load_story_state(paths, title)
            result = process_fragment(
                paths,
                fragment,
                session,
                bible,
                auto_confirm=bool(payload.get("auto_confirm", True)),
                non_interactive=bool(payload.get("non_interactive", False)),
                use_llm=bool(payload.get("use_llm", False)),
                memory_journal_path=MEMORY_JOURNAL,
            )
            json_response(
                self,
                200,
                {
                    "story_id": paths.root.name,
                    "session": result["session"],
                    "bible": result["bible"],
                    "agent_reply": result["agent_reply"],
                    "applied": result["applied"],
                },
            )
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_story_answer(self) -> None:
        from story_session import load_story_state, process_answer, resolve_story_paths

        try:
            payload = read_json_body(self)
            answer = str(payload.get("answer", "")).strip()
            story_id = payload.get("story_id")
            if not answer:
                json_response(self, 400, {"error": "answer is required"})
                return
            if story_id:
                paths = resolve_story_paths(STORY_ROOT, story_id, payload.get("title"))
                if not paths.root.exists():
                    json_response(self, 404, {"error": f"story not found: {story_id}"})
                    return
                session, bible = load_story_state(paths, payload.get("title"))
            else:
                session = payload.get("session")
                bible = payload.get("bible")
                if session is None or bible is None:
                    json_response(self, 400, {"error": "story_id or session+bible required"})
                    return
                paths = _temp_story_paths()
            result = process_answer(paths, answer, session, bible, memory_journal_path=MEMORY_JOURNAL)
            json_response(
                self,
                200,
                {
                    "story_id": paths.root.name,
                    "session": result["session"],
                    "bible": result["bible"],
                    "agent_reply": result["agent_reply"],
                },
            )
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_voice_status(self) -> None:
        ensure_mvp_path()
        from voice_adapter import voice_status

        json_response(self, 200, {"ok": True, **voice_status()})

    def handle_voice_transcribe(self) -> None:
        from voice_adapter import transcribe_file, transcribe_stream

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                },
            )
            simulate_text = form.getvalue("simulate_transcript")
            want_stream = str(form.getvalue("stream") or "").lower() in {"1", "true", "yes"}
            if simulate_text:
                text = str(simulate_text).strip()
                payload: dict[str, Any] = {"text": text, "model": "simulated-asr"}
                if want_stream:
                    from voice_adapter import split_transcript_partials

                    parts = split_transcript_partials(text)
                    payload["partials"] = [
                        {"index": idx, "text": item, "is_final": item == parts[-1]}
                        for idx, item in enumerate(parts, start=1)
                    ]
                json_response(self, 200, payload)
                return
            if "audio" not in form:
                json_response(self, 400, {"error": "audio file field is required"})
                return
            item = form["audio"]
            suffix = Path(item.filename or "audio.webm").suffix or ".webm"
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / f"upload{suffix}"
                src.write_bytes(item.file.read())
                sidecar_text = form.getvalue("transcript_sidecar")
                if sidecar_text:
                    src.with_name(f"{src.stem}.transcript.txt").write_text(
                        str(sidecar_text).strip() + "\n",
                        encoding="utf-8",
                    )
                wav = convert_to_wav_if_needed(src)
                if want_stream:
                    stream = transcribe_stream(wav)
                    json_response(
                        self,
                        200,
                        {
                            "text": stream.text,
                            "model": stream.model,
                            "partials": stream.partials,
                            "skipped": stream.skipped,
                            "skip_reason": stream.skip_reason,
                            "command": stream.command,
                        },
                    )
                    return
                result = transcribe_file(wav)
                json_response(self, 200, {"text": result.text, "model": result.model})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_voice_story(self) -> None:
        from story_session import load_story_state, resolve_resume_story_id, resolve_story_paths, run_voice_story_once

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                },
            )
            simulate_text = form.getvalue("simulate_transcript")
            title = str(form.getvalue("title") or "未命名故事")
            story_id = form.getvalue("story_id") or None
            quiet = str(form.getvalue("quiet") or "").lower() in {"1", "true", "yes"}
            auto_confirm = str(form.getvalue("auto_confirm") or "1").lower() not in {"0", "false", "no"}
            include_audio = str(form.getvalue("include_audio") or "1").lower() not in {"0", "false", "no"}
            resume = str(form.getvalue("resume") or "").lower() in {"1", "true", "yes"}
            if resume and not story_id:
                story_id = resolve_resume_story_id(STORY_ROOT, None, True)
            paths = resolve_story_paths(STORY_ROOT, story_id, title)
            paths.root.mkdir(parents=True, exist_ok=True)
            session, bible = load_story_state(paths, title)

            with tempfile.TemporaryDirectory() as tmp:
                if simulate_text:
                    wav = Path(tmp) / "sim.wav"
                    from voice_adapter import write_silent_wav

                    write_silent_wav(wav)
                    wav.with_name("sim.transcript.txt").write_text(str(simulate_text).strip() + "\n", encoding="utf-8")
                else:
                    if "audio" not in form:
                        json_response(self, 400, {"error": "audio file field or simulate_transcript is required"})
                        return
                    item = form["audio"]
                    suffix = Path(item.filename or "audio.webm").suffix or ".webm"
                    src = Path(tmp) / f"upload{suffix}"
                    src.write_bytes(item.file.read())
                    sidecar_text = form.getvalue("transcript_sidecar")
                    if sidecar_text:
                        src.with_name(f"{src.stem}.transcript.txt").write_text(
                            str(sidecar_text).strip() + "\n",
                            encoding="utf-8",
                        )
                    wav = convert_to_wav_if_needed(src)
                payload = run_voice_story_once(
                    paths,
                    wav,
                    session,
                    bible,
                    auto_confirm=auto_confirm,
                    non_interactive=True,
                    quiet=quiet,
                    memory_journal_path=MEMORY_JOURNAL,
                )
            response = {
                "story_id": payload["story_id"],
                "transcript": payload.get("transcript", ""),
                "partials": payload.get("partials") or [],
                "applied": payload.get("applied", False),
                "skipped": payload.get("skipped", False),
                "skip_reason": payload.get("skip_reason", ""),
                "command": payload.get("command"),
                "agent_reply": payload.get("agent_reply", ""),
                "tts_text": payload.get("reply_text", ""),
                "session": payload.get("session"),
                "bible": payload.get("bible"),
                "quiet": payload.get("quiet", quiet),
            }
            reply_audio = payload.get("reply_audio")
            if include_audio and reply_audio and Path(reply_audio).exists():
                response["reply_audio_base64"] = base64.b64encode(Path(reply_audio).read_bytes()).decode("ascii")
                response["reply_audio_mime"] = "audio/wav"
            json_response(self, 200, response)
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_voice_speak(self) -> None:
        from voice_adapter import apply_quiet_config, build_tts_summary, load_voice_config, synthesize_speech

        try:
            payload = read_json_body(self)
            text = str(payload.get("text", "")).strip()
            if not text:
                json_response(self, 400, {"error": "text is required"})
                return
            config = apply_quiet_config(load_voice_config(), quiet=bool(payload.get("quiet", False)))
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "reply.wav"
                summary = build_tts_summary(text, config)
                result = synthesize_speech(summary, out, config=config)
                data = out.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - [%s] %s\n" % (self.log_date_time_string(), self.address_string(), format % args))


def _temp_story_paths():
    from story_session import StoryPaths

    root = Path(tempfile.mkdtemp(prefix="bedagent-web-story-"))
    return StoryPaths(root)


def main() -> int:
    parser = argparse.ArgumentParser(description="bedagent local web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    if not SITE_DIR.exists():
        print(f"Site directory not found: {SITE_DIR}", file=sys.stderr)
        return 2

    server = ThreadingHTTPServer((args.host, args.port), BedagentWebHandler)
    print(f"bedagent web serving {SITE_DIR} at http://{args.host}:{args.port}")
    print(f"Agent UI: http://{args.host}:{args.port}/agent/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
