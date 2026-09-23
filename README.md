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

## Stack technique

Tout tourne sur CPU, dans un seul container, sans GPU ni service en ligne pendant la transcription. Voici ce qui est embarqué et d'où cela vient.

| Brique | Rôle | Version | Source |
|---|---|---|---|
| Debian 13 + Python 3.11 (`python:3.11-slim`) | base de l'image | 3.11 | Docker Hub |
| ffmpeg | décodage audio/vidéo, conversion en WAV 16 kHz mono | 7.1 | paquet Debian |
| faster-whisper | reconnaissance vocale (moteur CTranslate2 4.8) | 1.2.1 | PyPI |
| Modèle Whisper `large-v3` (défaut) ou `medium` | poids du modèle de transcription, quantifiés int8 au chargement | conversion Systran | Hugging Face, dépôt `Systran/faster-whisper-large-v3` |
| resemblyzer | empreintes de voix (embeddings) pour séparer les locuteurs | 0.1.4 | PyPI, poids embarqués dans le paquet |
| scikit-learn | regroupement des empreintes (clustering agglomératif, distance cosinus, moyenne, seuil 0,55 en mode `auto`) | 1.9.1 | PyPI |
| librosa | hauteur de voix (algorithme pyin, 80 à 500 Hz) donnée à titre indicatif par locuteur | 0.11.0 | PyPI |
| torch (build CPU) | dépendance de resemblyzer | 2.8.0 | index PyTorch CPU |
| yt-dlp | téléchargement des URL (YouTube, podcasts, réseaux sociaux) | 2026.7.4 | PyPI |

Paramètres de transcription : faisceau de recherche (`beam_size`) 5, filtre de silence VAD activé, langue détectée automatiquement sauf option `-l`. Le container tourne sous un utilisateur non root (uid 1000) et le modèle est mis en cache dans le volume `/cache` (`HF_HOME`).

Aucun modèle n'est dans l'image : le premier lancement télécharge `large-v3` (environ 3 Go) depuis Hugging Face, une seule fois. Ensuite, le seul trafic sortant possible est celui de yt-dlp quand vous donnez une URL. Vos fichiers audio et le texte produit ne quittent jamais la machine.

Le pipeline, dans l'ordre : regroupement des fichiers auto-découpés (`group_parts.py`, horodatage du nom de fichier puis métadonnées), conversion ffmpeg, transcription faster-whisper, attribution optionnelle des locuteurs (resemblyzer + clustering + hauteur de voix), rendu Markdown, CSV, SRT, TXT et `segments.json`.

## Sorties et confidentialité

Chaque enregistrement contient `segments.json`, `parts.json` si nécessaire, un Markdown, un CSV séparé par `;`, un SRT, un TXT et le journal Whisper. Les données restent locales, sauf le téléchargement initial du modèle depuis Hugging Face et le téléchargement d'une URL demandé à yt-dlp. Le verbatim est une sortie automatique à relire et ne doit pas transformer une attribution de voix incertaine en certitude.

## Construction locale

```sh
docker build -t transcription .
```

La licence est MIT, titulaire Cybergraphe SASU, 2026.
