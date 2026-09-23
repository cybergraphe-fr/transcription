"""Transcription locale avec faster-whisper.

Le module reste importable sans faster-whisper afin que les tests de regroupement et de rendu
puissent s'exécuter sans installer les dépendances lourdes ni télécharger de modèle.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def transcribe_audio(
    wav_path: str | Path,
    output_path: str | Path,
    language: str = "fr",
    model: str = "large-v3",
    word_timestamps: bool = False,
    compute_type: str = "int8",
    threads: int = 1,
) -> dict[str, Any]:
    """Transcrit un WAV 16 kHz mono et écrit le JSON métier."""

    from faster_whisper import WhisperModel

    lang = None if language == "auto" else language
    whisper = WhisperModel(
        model,
        device="cpu",
        compute_type=compute_type,
        cpu_threads=threads,
        num_workers=1,
        download_root="/cache",
    )
    segments, info = whisper.transcribe(
        str(wav_path),
        language=lang,
        beam_size=5,
        vad_filter=True,
        word_timestamps=word_timestamps,
    )
    result_segments: list[dict[str, Any]] = []
    for segment in segments:
        item: dict[str, Any] = {
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
        }
        if word_timestamps and segment.words:
            item["words"] = [
                {"w": word.word, "s": round(word.start, 2), "e": round(word.end, 2)}
                for word in segment.words
            ]
        result_segments.append(item)
        print(f"[{segment.start:7.2f} -> {segment.end:7.2f}] {segment.text.strip()}", flush=True)

    data: dict[str, Any] = {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
        "model": model,
        "segments": result_segments,
    }
    Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"DONE {len(result_segments)} segments ; durée {info.duration:.1f} s ; "
        f"langue {info.language} ({info.language_probability:.2f})"
    )
    return data


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav")
    parser.add_argument("output")
    parser.add_argument("language", nargs="?", default="fr")
    parser.add_argument("model", nargs="?", default="large-v3")
    parser.add_argument("words", nargs="?", type=int, default=0)
    args = parser.parse_args(argv)
    transcribe_audio(args.wav, args.output, args.language, args.model, bool(args.words))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
