# Transcription locale distribuable

Cette image transcrit localement des fichiers audio, des vidéos, des dossiers de morceaux et des URL avec faster-whisper sur CPU. Elle regroupe les vidéos auto-découpées, attribue optionnellement les locuteurs avec resemblyzer et produit des rendus relisibles.

Code source : https://github.com/cybergraphe-fr/transcription (licence MIT). Image prête à l'emploi : `registry.cybergraphe.fr/transcription:1.0.1`. Guide pas à pas pour un nouvel utilisateur : `TUTORIEL.md`. L'installation ne touche rien d'existant sur votre machine : voir la partie 2 du tutoriel.

## Prérequis

Il faut Docker, une machine amd64 et idéalement 10 Go de RAM pour `large-v3`. Le premier lancement télécharge environ 3 Go de modèle dans le volume de cache. Le traitement est CPU et aucun modèle Whisper n'est embarqué dans l'image.

## Installation en trois commandes

```sh
mkdir -p transcriptions
docker pull registry.cybergraphe.fr/transcription:1.0.1
docker volume create cybergraphe-transcription-cache
```

## Exemples

```sh
docker run --rm -v "$PWD:/in:ro" -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.1 /in/reunion.m4a
docker run --rm -v "$PWD:/in:ro" -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.1 /in/ray-ban/ -s auto --names '{"S1":"Alice","S2":"Bob"}'
docker run --rm -v "$PWD:/in:ro" -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.1 'https://exemple.invalid/video'
docker run --rm -v "$PWD:/in:ro" -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.1 /in/reunion.mp4 -s 2 -w
```

Le fichier `.srt` produit contient les sous-titres. Les options utiles sont `-l fr|en|auto`, `-m large-v3|medium`, `-s N|auto`, `-t "titre"`, `-w`, `-g 120`, `--compute-type int8` et `--threads N`. Pour conserver l'interface courte, installe aussi `skill/transcrire.sh` dans un dossier de commandes.

## Installer le skill Claude Code

```sh
docker run --rm -v ~/.claude/skills:/export registry.cybergraphe.fr/transcription:1.0.1 --export-skill /export/transcription
```

## Sorties et confidentialité

Chaque enregistrement contient `segments.json`, `parts.json` si nécessaire, un Markdown, un CSV séparé par `;`, un SRT, un TXT et le journal Whisper. Les données restent locales, sauf le téléchargement initial du modèle depuis Hugging Face et le téléchargement d'une URL demandé à yt-dlp. Le verbatim est une sortie automatique à relire et ne doit pas transformer une attribution de voix incertaine en certitude.

## Construction locale

```sh
docker build -t transcription .
```

La licence est MIT, titulaire Cybergraphe SASU, 2026.
