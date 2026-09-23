#!/usr/bin/env python3
"""CLI distribuable de transcription audio et vidéo locale."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from group_parts import group_files
from render import render_segments
from speakers import identify_speakers
from transcribe import transcribe_audio

MEDIA_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".mkv",
    ".webm",
    ".avi",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wav",
    ".flac",
    ".3gp",
    ".amr",
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Transcrit localement des fichiers, dossiers ou URL avec faster-whisper."
    )
    result.add_argument("inputs", nargs="*", metavar="ENTRÉE")
    result.add_argument("-o", "--out", default=None, help="Dossier de sortie, par défaut sous /out")
    result.add_argument("-l", "--lang", default="fr", help="Langue forcée ou auto")
    result.add_argument("-m", "--model", default="large-v3")
    result.add_argument("-s", "--speakers", default=None, metavar="N|auto")
    result.add_argument("-t", "--title", default="")
    result.add_argument("-w", "--words", action="store_true", help="Ajouter les timecodes par mot")
    result.add_argument("-g", "--gap", type=float, default=120, help="Tolérance de regroupement en secondes")
    result.add_argument("--metube-url", default=None)
    result.add_argument("--metube-dir", default=None)
    result.add_argument("--metube-timeout", type=float, default=1800)
    result.add_argument("--names", default="{}", help="Objet JSON associant S1, S2, etc. à des noms")
    result.add_argument("--compute-type", default="int8")
    result.add_argument("--threads", type=int, default=os.cpu_count() or 1)
    result.add_argument("--export-skill", metavar="DOSSIER", default=None)
    return result


def parse_names(value: str) -> dict[str, str]:
    try:
        names = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"--names n'est pas un JSON valide : {error}") from error
    if not isinstance(names, dict) or not all(isinstance(key, str) and isinstance(name, str) for key, name in names.items()):
        raise ValueError("--names doit être un objet JSON de chaînes")
    return names


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def download_with_metube(
    url: str, service_url: str, directory: str, timeout: float
) -> tuple[str, str]:
    """Télécharge une URL via l'API MeTube et retourne le chemin et le titre."""

    try:
        response = request_json(
            urllib.parse.urljoin(service_url.rstrip("/") + "/", "add"),
            method="POST",
            payload={"url": url, "quality": "best", "format": "m4a", "folder": "transcription", "auto_start": True},
        )
    except Exception as error:
        raise RuntimeError(f"MeTube injoignable ({service_url}) : {error}") from error
    if not isinstance(response, dict) or not response.get("ok"):
        raise RuntimeError(f"MeTube a refusé l'URL : {response}")

    deadline = time.monotonic() + timeout
    filename = ""
    title = ""
    while not filename:
        try:
            history = request_json(urllib.parse.urljoin(service_url.rstrip("/") + "/", "history"))
        except Exception as error:
            raise RuntimeError(f"MeTube injoignable pendant le suivi : {error}") from error
        for entry in history.get("done", []):
            if entry.get("url") != url:
                continue
            if entry.get("status") == "error":
                raise RuntimeError(f"MeTube : {entry.get('msg', 'erreur inconnue')}")
            if entry.get("status") == "finished":
                filename = str(entry.get("filename", ""))
                title = str(entry.get("title", ""))
                break
        if filename:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError("MeTube : délai dépassé")
        time.sleep(5)

    root = Path(directory)
    candidates = [root / "transcription" / Path(filename).name, root / filename]
    source = next((candidate for candidate in candidates if candidate.is_file()), None)
    if source is None:
        raise RuntimeError(f"fichier MeTube introuvable : {filename}")
    return str(source), title


def download_with_ytdlp(url: str) -> tuple[str, str]:
    """Télécharge une URL dans l'espace de travail éphémère du container."""

    directory = Path("/work/downloads")
    directory.mkdir(parents=True, exist_ok=True)
    before = {path.resolve() for path in directory.iterdir() if path.is_file()}
    result = subprocess.run(
        [
            "yt-dlp",
            "--no-playlist",
            "-f",
            "bestaudio/best",
            "--restrict-filenames",
            "--print",
            "after_move:filepath",
            "-o",
            str(directory / "%(title)s.%(ext)s"),
            url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"yt-dlp a échoué pour {url} : {result.stderr.strip()}")
    reported = [Path(line.strip()) for line in result.stdout.splitlines() if Path(line.strip()).is_file()]
    created = [path for path in directory.iterdir() if path.is_file() and path.resolve() not in before]
    source = next((path for path in reported if path.is_file()), None) or (max(created, key=lambda path: path.stat().st_mtime) if created else None)
    if source is None:
        raise RuntimeError(f"yt-dlp n'a produit aucun fichier pour {url}")
    return str(source), ""


def collect_inputs(args: argparse.Namespace) -> tuple[list[str], str]:
    files: list[str] = []
    url_description = ""
    for value in args.inputs:
        if value.startswith(("http://", "https://")):
            if args.metube_url or args.metube_dir:
                service = args.metube_url or "http://metube:8081"
                directory = args.metube_dir or "/metube-downloads"
                path, title = download_with_metube(value, service, directory, args.metube_timeout)
                method = "MeTube"
            else:
                path, title = download_with_ytdlp(value)
                method = "yt-dlp"
            url_description = f"média en ligne : {value} (« {title} », téléchargé par {method} dans `{path}`)"
            files.append(path)
            if not args.title and title:
                args.title = title
            continue

        path = Path(value)
        if path.is_dir():
            files.extend(
                str(child)
                for child in sorted(path.iterdir())
                if child.is_file() and child.suffix.lower() in MEDIA_EXTENSIONS
            )
        elif path.is_file():
            files.append(str(path))
        else:
            raise FileNotFoundError(f"introuvable : {value}")
    if not files:
        raise ValueError("aucun fichier média")
    return files, url_description


def media_description(first: str, count: int) -> str:
    if count > 1:
        return f"{count} fichiers contigus, premier `{Path(first).name}`"
    details = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name:stream=codec_type,codec_name,channels,sample_rate",
            "-of",
            "csv=p=0",
            first,
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.replace(",", " ").replace("\n", " ").strip()
    return f"fichier `{Path(first).name}` ({details})"


def safe_base(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return base.strip("._") or "transcription"


def extract_audio(parts: list[dict[str, Any]], destination: Path) -> Path:
    wav_parts: list[Path] = []
    for index, part in enumerate(parts, 1):
        wav = destination / f"part{index}.wav"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", part["path"], "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
            check=True,
        )
        wav_parts.append(wav)
    target = destination / "audio16k.wav"
    if len(wav_parts) == 1:
        wav_parts[0].replace(target)
        return target
    concat = destination / "concat.txt"
    concat.write_text("\n".join(f"file '{path.name}'" for path in wav_parts) + "\n", encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(target)],
        check=True,
        cwd=destination,
    )
    for wav in wav_parts:
        wav.unlink()
    concat.unlink()
    return target


def export_skill(directory: str) -> int:
    """Copie le skill embarqué sans jamais écraser un fichier existant : l'installation ne doit pas toucher un environnement déjà en place."""
    target = Path(directory)
    source = Path("/skill")
    if not source.is_dir():
        raise RuntimeError("le skill embarqué est introuvable sous /skill")
    target.mkdir(parents=True, exist_ok=True)
    written, kept = [], []
    for item in sorted(source.rglob("*")):
        rel = item.relative_to(source)
        dest = target / rel
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        if dest.exists():
            kept.append(str(rel))
            continue
        shutil.copy2(item, dest)
        written.append(str(rel))
    print(f"SKILL exporté dans {target} : {len(written)} fichier(s) écrit(s)" + (f" ({', '.join(written)})" if written else ""))
    if kept:
        print(f"Fichiers déjà présents, laissés intacts : {', '.join(kept)} (supprimez-les d'abord pour obtenir la version embarquée)")
    return 0


def run(args: argparse.Namespace) -> int:
    if args.export_skill:
        return export_skill(args.export_skill)
    if args.gap < 0:
        raise ValueError("--gap doit être positif ou nul")
    if args.threads < 1:
        raise ValueError("--threads doit être supérieur ou égal à 1")
    if args.speakers is not None and args.speakers != "auto":
        if not args.speakers.isdigit() or int(args.speakers) < 1:
            raise ValueError("--speakers attend N ou auto")
    names = parse_names(args.names)
    files, url_description = collect_inputs(args)
    output = Path(args.out or f"/out/transcription-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    output.mkdir(parents=True, exist_ok=True)
    print(f"== {len(files)} fichier(s) ; regroupement des morceaux contigus (tolérance {args.gap:g} s)")
    groups = group_files(files, args.gap)
    groups_path = output / "groupes.json"
    groups_path.write_text(json.dumps(groups, ensure_ascii=False, indent=1), encoding="utf-8")
    for group in groups:
        first = group["files"][0]
        print(
            f"   enregistrement {group['id']} : {len(group['files'])} morceau(x), "
            f"{group['total_duration'] / 60:.1f} min, début {group['start']} ({first['start_source']})"
        )

    for index, group in enumerate(groups, 1):
        group_output = output / (f"enregistrement-{index}" if len(groups) > 1 else "")
        group_output.mkdir(parents=True, exist_ok=True)
        parts = group["files"]
        (group_output / "parts.json").write_text(json.dumps(parts, ensure_ascii=False, indent=1), encoding="utf-8")
        first_path = parts[0]["path"]
        base = safe_base(Path(first_path).stem)
        if len(parts) > 1:
            base = f"{base}_et_{len(parts)}_morceaux"
        title = args.title or base
        if len(groups) > 1:
            title = f"{title} (enregistrement {index})"
        source = url_description or media_description(first_path, len(parts))
        print(f"== enregistrement {index}/{len(groups)} : extraction audio 16 kHz mono (ffmpeg, {len(parts)} morceau(x))")
        audio = extract_audio(parts, group_output)
        print(
            f"== transcription faster-whisper {args.model} (langue {args.lang}) : "
            "compter environ 1 fois la durée de l'audio"
        )
        segments_path = group_output / "segments.json"
        transcribe_audio(
            audio,
            segments_path,
            language=args.lang,
            model=args.model,
            word_timestamps=args.words,
            compute_type=args.compute_type,
            threads=args.threads,
        )
        if args.speakers:
            print(f"== locuteurs ({args.speakers})")
            identify_speakers(audio, segments_path, args.speakers)
        render_segments(segments_path, group_output, f"transcription_{base}", title, source, names)
    print(f"== terminé : {output} ({len(groups)} enregistrement(s))")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
