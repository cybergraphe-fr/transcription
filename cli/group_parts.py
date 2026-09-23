"""Regroupement des morceaux contigus en enregistrements."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

Probe = Callable[[str], dict[str, Any]]


def probe(path: str) -> dict[str, Any]:
    """Retourne durée et début selon la priorité métier du skill de référence."""

    output = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:format_tags=creation_time:stream_tags=creation_time",
            "-of",
            "json",
            path,
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    data = json.loads(output or "{}")
    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or 0)
    creation_time = fmt.get("tags", {}).get("creation_time") or next(
        (
            stream.get("tags", {}).get("creation_time")
            for stream in data.get("streams", [])
            if stream.get("tags", {}).get("creation_time")
        ),
        None,
    )

    match = re.search(
        r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_T ]?(\d{2})[-_.:]?(\d{2})[-_.:]?(\d{2})",
        os.path.basename(path),
    )
    if match:
        start = datetime(*map(int, match.groups())).replace(tzinfo=timezone.utc)
        source = "nom de fichier (heure locale)"
    elif creation_time:
        start = datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
        source = "metadata"
    else:
        start = datetime.fromtimestamp(
            os.path.getmtime(path) - duration, tz=timezone.utc
        )
        source = "mtime moins durée (fin d'écriture supposée = fin de l'enregistrement)"
    return {
        "path": os.path.abspath(path),
        "name": os.path.basename(path),
        "start": start.isoformat(),
        "duration": round(duration, 2),
        "start_source": source,
        "_t": start.timestamp(),
    }


def group_files(files: list[str], tolerance: float = 120, probe_func: Probe = probe) -> list[dict[str, Any]]:
    """Trie les morceaux et fusionne ceux dont l'écart est entre -60 s et la tolérance."""

    items = sorted((probe_func(path) for path in files), key=lambda item: item["_t"])
    groups: list[dict[str, Any]] = []
    for item in items:
        if groups:
            previous = groups[-1]["files"][-1]
            gap = item["_t"] - (previous["_t"] + previous["duration"])
            if -60 <= gap <= tolerance:
                item["gap_before"] = round(gap, 1)
                groups[-1]["files"].append(item)
                continue
        groups.append({"files": [item]})

    for group_id, group in enumerate(groups, 1):
        offset = 0.0
        for item in group["files"]:
            item["offset"] = round(offset, 2)
            offset += item["duration"]
            item.pop("_t", None)
        group["id"] = group_id
        group["total_duration"] = round(offset, 2)
        group["start"] = group["files"][0]["start"]
    return groups


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tolerance", type=float)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)
    print(json.dumps(group_files(args.files, args.tolerance), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
