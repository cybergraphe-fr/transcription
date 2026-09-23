import json
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "cli"))

from group_parts import group_files
from render import render_segments


class TranscriptionToolsTest(unittest.TestCase):
    def test_group_parts_with_injected_durations(self):
        files = [
            "/tmp/20260917_120200_camera.mp4",
            "/tmp/20260917_120000_camera.mp4",
            "/tmp/20260917_121000_camera.mp4",
        ]
        values = {
            files[0]: ("2026-09-17T12:02:00+00:00", 60),
            files[1]: ("2026-09-17T12:00:00+00:00", 60),
            files[2]: ("2026-09-17T12:10:00+00:00", 60),
        }

        def fake_ffprobe(command, **kwargs):
            path = command[-1]
            return CompletedProcess(
                command,
                0,
                stdout=json.dumps({"format": {"duration": values[path][1]}}),
                stderr="",
            )

        with patch("group_parts.subprocess.run", side_effect=fake_ffprobe):
            groups = group_files(files, tolerance=120)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups[0]["files"]), 2)
        self.assertEqual(groups[0]["files"][1]["gap_before"], 60.0)
        self.assertEqual(groups[0]["files"][1]["offset"], 60.0)

    def test_render_formats_and_names(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            segments = output / "segments.json"
            segments.write_text(
                json.dumps(
                    {
                        "language": "fr",
                        "model": "medium",
                        "duration": 8,
                        "segments": [
                            {"start": 0, "end": 2.5, "speaker": "S1", "text": "Bonjour | équipe"},
                            {"start": 3, "end": 8, "speaker": "S2", "text": "À bientôt."},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (output / "parts.json").write_text(
                json.dumps(
                    [
                        {"name": "part-1.mp4", "offset": 0, "duration": 3},
                        {"name": "part-2.mp4", "offset": 3, "duration": 5, "gap_before": 0},
                    ]
                ),
                encoding="utf-8",
            )
            render_segments(segments, output, "transcription_test", "Test", "fichier test", {"S1": "Alice"})
            markdown = (output / "transcription_test.md").read_text(encoding="utf-8")
            csv = (output / "transcription_test.csv").read_text(encoding="utf-8")
            srt = (output / "transcription_test.srt").read_text(encoding="utf-8")
            self.assertIn("Alice", markdown)
            self.assertIn("Bonjour \\| équipe", markdown)
            self.assertIn("part-2.mp4", markdown)
            self.assertIn(";Alice;", csv)
            self.assertIn("00:00:00,000 --> 00:00:02,500", srt)


if __name__ == "__main__":
    unittest.main()
