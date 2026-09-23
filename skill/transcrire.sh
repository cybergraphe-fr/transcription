#!/bin/sh
set -eu
IMAGE=${TRANSCRIPTION_IMAGE:-registry.cybergraphe.fr/transcription:1.0.1}
ROOT=$(pwd)
OUT=$ROOT/transcriptions
PREVIOUS=
for ARG in "$@"; do
  if [ "$PREVIOUS" = out ]; then OUT=$ARG; PREVIOUS=; continue; fi
  case "$ARG" in -o|--out) PREVIOUS=out ;; --out=*) OUT=${ARG#*=} ;; esac
done
mkdir -p "$OUT"
exec docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -w /in \
  -v "$ROOT:/in:ro" -v "$OUT:/out" -v cybergraphe-transcription-cache:/cache \
  "$IMAGE" "$@" -o /out
