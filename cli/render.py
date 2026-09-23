"""Rendu de segments.json en Markdown, CSV, SRT et texte brut."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any


def timecode(value: float, srt: bool = False) -> str:
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    if srt:
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(round((seconds - int(seconds)) * 1000)):03d}"
    return (f"{int(hours)}:" if hours >= 1 else "") + f"{int(minutes):02d}:{seconds:05.2f}"


def render_segments(
    segments_path: str | Path,
    output_dir: str | Path,
    base: str,
    title: str,
    source: str,
    names: dict[str, str] | None = None,
) -> list[Path]:
    """Rend les quatre formats et retourne les chemins écrits."""

    output = Path(output_dir)
    data = json.loads(Path(segments_path).read_text(encoding="utf-8"))
    segments = data["segments"]
    if names is None:
        names = json.loads(os.environ.get("SPEAKER_NAMES", "{}"))

    def speaker(segment: dict[str, Any]) -> str:
        value = segment.get("speaker", "")
        return names.get(value, value)

    has_speakers = any("speaker" in segment for segment in segments)
    duration = data.get("duration", segments[-1]["end"] if segments else 0)
    markdown = [
        f"# Transcription - {title}",
        "",
        f"**Source** : {source}, durée {int(duration // 60)} min {int(duration % 60):02d} s ({duration:.2f} s), langue détectée : {data.get('language', '?')}.",
        "",
        "**Méthode** : transcription automatique locale (Whisper "
        f"{data.get('model', '?')}, moteur faster-whisper sur CPU, aucun envoi vers un service en ligne)"
        + (", attribution des locuteurs par empreinte vocale (resemblyzer) puis regroupement, à relire" if has_speakers else "")
        + ". Les timecodes sont ceux détectés par le moteur (début -> fin de chaque segment parlé).",
        "",
        "**Réserve** : quelques mots peuvent être mal reconnus ; en cas de doute, l'audio original fait foi.",
        "",
    ]
    parts_path = output / "parts.json"
    if parts_path.exists():
        parts = json.loads(parts_path.read_text(encoding="utf-8"))
        if len(parts) > 1:
            markdown.extend(
                [
                    f"**Fichiers** : enregistrement unique découpé en {len(parts)} morceaux par l'appareil de captation (horodatages contigus), transcrits d'un seul tenant ; les timecodes sont continus sur l'ensemble.",
                    "",
                    "| Morceau | Fichier | Début (timecode) | Durée | Écart avec le précédent |",
                    "|---|---|---|---|---|",
                ]
            )
            markdown.extend(
                f"| {index} | `{part['name']}` | {timecode(part['offset'])} | {timecode(part['duration'])} | {'' if 'gap_before' not in part else str(part['gap_before']) + ' s'} |"
                for index, part in enumerate(parts, 1)
            )
            markdown.append("")

    markdown.append("| Début | Fin | Locuteur | Texte |" if has_speakers else "| Début | Fin | Texte |")
    markdown.append("|---|---|---|---|" if has_speakers else "|---|---|---|")
    for segment in segments:
        text = segment["text"].replace("|", "\\|")
        if has_speakers:
            markdown.append(
                f"| {timecode(segment['start'])} | {timecode(segment['end'])} | {speaker(segment)} | {text} |"
            )
        else:
            markdown.append(f"| {timecode(segment['start'])} | {timecode(segment['end'])} | {text} |")

    paths = [output / f"{base}.md", output / f"{base}.csv", output / f"{base}.srt", output / f"{base}.txt"]
    paths[0].write_text("\n".join(markdown) + "\n", encoding="utf-8")
    with paths[1].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["debut", "fin", "debut_s", "fin_s", "locuteur", "texte"])
        for segment in segments:
            writer.writerow(
                [
                    timecode(segment["start"]),
                    timecode(segment["end"]),
                    segment["start"],
                    segment["end"],
                    speaker(segment),
                    segment["text"],
                ]
            )
    with paths[2].open("w", encoding="utf-8") as handle:
        for index, segment in enumerate(segments, 1):
            prefix = f"{speaker(segment)} : " if has_speakers else ""
            handle.write(
                f"{index}\n{timecode(segment['start'], True)} --> {timecode(segment['end'], True)}\n{prefix}{segment['text']}\n\n"
            )
    paths[3].write_text(
        "\n".join((f"{speaker(segment)} : " if has_speakers else "") + segment["text"] for segment in segments) + "\n",
        encoding="utf-8",
    )
    print(f"RENDU {paths[0]} .csv .srt .txt ({len(segments)} segments)")
    return paths


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("segments")
    parser.add_argument("output_dir")
    parser.add_argument("base")
    parser.add_argument("title")
    parser.add_argument("source")
    args = parser.parse_args(argv)
    render_segments(args.segments, args.output_dir, args.base, args.title, args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
