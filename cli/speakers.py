"""Attribution des locuteurs par empreinte vocale et regroupement."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any


def identify_speakers(wav_path: str | Path, segments_path: str | Path, count: str) -> dict[str, Any]:
    """Ajoute les étiquettes S1..Sn et les indices de hauteur au JSON."""

    warnings.filterwarnings("ignore")
    import librosa
    import numpy as np
    from resemblyzer import VoiceEncoder, preprocess_wav
    from sklearn.cluster import AgglomerativeClustering

    path = Path(segments_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    segments = data["segments"]
    y, sample_rate = librosa.load(str(wav_path), sr=16000)
    encoder = VoiceEncoder("cpu")
    embeddings = []
    for segment in segments:
        audio = y[int(segment["start"] * sample_rate) : int(segment["end"] * sample_rate)]
        if len(audio) < sample_rate // 2:
            audio = np.pad(audio, (0, sample_rate // 2 - len(audio)))
        embeddings.append(encoder.embed_utterance(preprocess_wav(audio, source_sr=sample_rate)))

    matrix = np.array(embeddings)
    if len(segments) < 2:
        labels = [0] * len(segments)
    elif count == "auto":
        labels = AgglomerativeClustering(
            n_clusters=None, distance_threshold=0.55, metric="cosine", linkage="average"
        ).fit_predict(matrix)
    else:
        labels = AgglomerativeClustering(
            n_clusters=int(count), metric="cosine", linkage="average"
        ).fit_predict(matrix)

    order: dict[int, int] = {}
    for label in labels:
        order.setdefault(int(label), len(order) + 1)

    pitch: dict[int, list[float]] = {}
    for segment, label in zip(segments, labels):
        audio = y[int(segment["start"] * sample_rate) : int(segment["end"] * sample_rate)]
        if len(audio) < 2048:
            continue
        fundamental = librosa.pyin(audio, fmin=80, fmax=500, sr=sample_rate, frame_length=1024)[0]
        fundamental = fundamental[~np.isnan(fundamental)]
        if len(fundamental):
            pitch.setdefault(order[int(label)], []).append(float(np.median(fundamental)))

    for segment, label in zip(segments, labels):
        segment["speaker"] = f"S{order[int(label)]}"
    data["speakers"] = {
        f"S{number}": {
            "segments": int(sum(1 for label in labels if order[int(label)] == number)),
            "pitch_hz_median": round(float(np.median(values)), 0) if (values := pitch.get(number)) else None,
        }
        for number in sorted(order.values())
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("LOCUTEURS", json.dumps(data["speakers"], ensure_ascii=False))
    return data


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav")
    parser.add_argument("segments")
    parser.add_argument("count")
    args = parser.parse_args(argv)
    identify_speakers(args.wav, args.segments, args.count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
