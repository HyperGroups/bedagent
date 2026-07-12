import json
import os
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path
from unittest import mock

from voice_adapter import (
    build_tts_summary,
    extract_transcript_sentence,
    load_voice_config,
    map_voice_command,
    sanitize_tts_text,
    synthesize_speech,
    transcribe_file,
    write_silent_wav,
)


class VoiceAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_voice_config(Path(__file__).with_name("voice_config.json"))

    def test_extract_transcript_sentence_from_dict(self) -> None:
        text = extract_transcript_sentence({"text": "主角在梦里写字"})
        self.assertEqual(text, "主角在梦里写字")

    def test_extract_transcript_sentence_empty_dict_text(self) -> None:
        text = extract_transcript_sentence({"text": "", "sentence_id": 1})
        self.assertEqual(text, "")

    def test_map_voice_command_recap(self) -> None:
        self.assertEqual(map_voice_command("汇报一下", self.config), "/recap")

    def test_sanitize_tts_text_blocks_secrets(self) -> None:
        text = sanitize_tts_text("your api_key is sk-abc", self.config)
        self.assertIn("不朗读敏感内容", text)

    def test_build_tts_summary_prefers_recap_line(self) -> None:
        reply = "我听懂了：AI 开始做梦\n\nSage 想和你对齐：\n  1. Q?\n\n当前主线：梦境日志异常"
        summary = build_tts_summary(reply, self.config)
        self.assertIn("AI 开始做梦", summary)

    @mock.patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}, clear=False)
    @mock.patch("voice_adapter.configure_dashscope")
    @mock.patch("dashscope.audio.asr.Recognition")
    def test_transcribe_file_success(self, recognition_cls: mock.Mock, _configure: mock.Mock) -> None:
        instance = recognition_cls.return_value
        result = mock.Mock()
        result.status_code = HTTPStatus.OK
        result.get_sentence.return_value = {"text": "这是口述测试"}
        instance.call.return_value = result
        instance.get_last_request_id.return_value = "req-1"

        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "sample.wav"
            write_silent_wav(audio)
            out = transcribe_file(audio, config=self.config)
            self.assertEqual(out.text, "这是口述测试")
            self.assertEqual(out.model, self.config["asr_model"])

    @mock.patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}, clear=False)
    @mock.patch("voice_adapter.configure_dashscope")
    @mock.patch("dashscope.audio.tts_v2.SpeechSynthesizer")
    def test_synthesize_speech_writes_file(self, synth_cls: mock.Mock, _configure: mock.Mock) -> None:
        instance = synth_cls.return_value
        instance.call.return_value = b"fake-audio"

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reply.wav"
            result = synthesize_speech("收到，继续讲。", out, config=self.config)
            self.assertTrue(out.exists())
            self.assertEqual(result.byte_size, len(b"fake-audio"))


if __name__ == "__main__":
    unittest.main()
