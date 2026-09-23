# Transcrire un audio ou une vidéo en 10 minutes

Cet outil transcrit vos enregistrements (réunion, message vocal, vidéo, lien YouTube) en texte horodaté, entièrement sur votre machine. Rien n'est envoyé sur Internet, sauf le téléchargement du modèle de reconnaissance vocale la première fois.

## 1. Ce qu'il vous faut

- Docker installé (Docker Desktop sur Mac ou Windows, Docker Engine sur Linux). Testez avec `docker --version`.
- Un ordinateur avec 10 Go de mémoire libre et un processeur x86-64 (Intel ou AMD). Pas besoin de carte graphique.
- Environ 4 Go d'espace disque : 1 Go pour l'image, 3 Go pour le modèle.

## 2. Ce que l'installation touche sur votre machine

Rien d'autre que ceci, et jamais vos fichiers existants :

- une image Docker (`registry.cybergraphe.fr/transcription`), comme n'importe quelle autre image, supprimable avec `docker rmi` ;
- un volume Docker nommé `cybergraphe-transcription-cache` pour le modèle, supprimable avec `docker volume rm` ;
- un sous-dossier `transcriptions/` créé là où vous lancez la commande, avec un dossier horodaté par exécution (aucun résultat précédent n'est écrasé) ;
- si vous choisissez le raccourci de la partie 7 : deux fichiers (`SKILL.md`, `transcrire.sh`) dans le dossier que vous indiquez, et uniquement s'ils n'existent pas déjà. Un `CLAUDE.md`, un autre skill ou une configuration Docker déjà en place ne sont ni lus ni modifiés.

Aucun service ne reste lancé après la transcription, aucune configuration Docker (réseaux, `daemon.json`, compose existants) n'est modifiée.

## 3. Installer (une seule fois)

Ouvrez un terminal et tapez :

```
docker pull registry.cybergraphe.fr/transcription:1.0.2
```

Le téléchargement prend une à trois minutes selon votre connexion.

## 4. Transcrire votre premier fichier

Placez-vous dans le dossier qui contient votre fichier (ici `reunion.mp4`) et lancez :

```
docker run --rm -v "$PWD:/in:ro" -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.2 /in/reunion.mp4
```

Ce qui se passe : le dossier courant est lu en lecture seule, les résultats arrivent dans un sous-dossier `transcriptions`, et le modèle est conservé dans un espace nommé `cybergraphe-transcription-cache` pour ne pas être retéléchargé.

Le premier lancement télécharge le modèle (3 Go, quelques minutes). Pendant ce téléchargement, vous verrez une ligne `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN…` : c'est le serveur de Hugging Face (l'hébergeur du modèle) qui signale que vous téléchargez sans compte. Ce n'est pas une erreur, le téléchargement continue et le message ne revient plus une fois le modèle en cache. Un compte n'est nécessaire que si vous téléchargez beaucoup depuis la même adresse IP (voir la partie 8). Ensuite, comptez à peu près la durée de l'enregistrement : 10 minutes d'audio donnent 10 minutes de traitement sur un ordinateur récent.

À la fin, vous avez dans `transcriptions/` :

- `transcription_reunion.md` : le texte, ligne par ligne avec les heures de début et de fin, lisible dans n'importe quel éditeur.
- `transcription_reunion.csv` : la même chose pour Excel (séparateur point-virgule).
- `transcription_reunion.srt` : des sous-titres pour VLC ou YouTube.
- `transcription_reunion.txt` : le texte brut.

## 5. Les options utiles

Ajoutez-les à la fin de la commande, après le nom du fichier.

| Besoin | Option | Exemple |
|---|---|---|
| Plusieurs personnes parlent | `-s auto` ou `-s 3` si vous savez combien | `/in/reunion.mp4 -s 3` |
| Enregistrement en anglais | `-l en` (`-l auto` pour laisser détecter) | `/in/call.m4a -l en` |
| Aller plus vite, un peu moins précis | `-m medium` | `/in/long.mp3 -m medium` |
| Donner un titre au document | `-t "Réunion du 12 mars"` | |
| Nommer les voix après relecture | `--names '{"S1":"Alice","S2":"Bob"}'` | relancez la même commande avec cette option |

Les voix sont détectées automatiquement et étiquetées S1, S2, etc. Cette détection se trompe souvent en environnement bruyant : relisez avant de faire confiance aux étiquettes.

## 6. Cas particuliers

**Une vidéo découpée en morceaux** (lunettes Ray-Ban Meta, dashcam, dictaphone qui coupe toutes les 3 ou 5 minutes) : mettez tous les morceaux dans un dossier et donnez le dossier au lieu du fichier. L'outil reconnaît les morceaux qui se suivent grâce à leur horodatage et produit une seule transcription continue, avec la liste des morceaux en tête de document.

```
docker run --rm -v "$PWD:/in:ro" -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.2 /in/lunettes
```

**Un lien YouTube ou autre** : donnez l'URL à la place du fichier. Le téléchargement est fait par yt-dlp à l'intérieur de l'outil.

```
docker run --rm -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.2 "https://www.youtube.com/watch?v=..."
```

## 7. Raccourci : ne plus taper la longue commande

L'outil embarque un petit script qui fait les montages pour vous. Récupérez-le une fois :

```
docker run --rm -v "$HOME/.local/bin:/export" registry.cybergraphe.fr/transcription:1.0.2 --export-skill /export/transcription
```

Ensuite, depuis n'importe quel dossier :

```
~/.local/bin/transcription/transcrire.sh reunion.mp4 -s auto
```

Si vous utilisez Claude Code, exportez plutôt vers `~/.claude/skills` : Claude saura alors transcrire vos fichiers tout seul quand vous le lui demandez.

```
docker run --rm -v "$HOME/.claude/skills:/export" registry.cybergraphe.fr/transcription:1.0.2 --export-skill /export/transcription
```

## 8. Si ça coince

- `permission denied` sur le dossier `transcriptions` : créez-le vous-même avant de lancer (`mkdir transcriptions`), ou ajoutez `--user "$(id -u):$(id -g)"` juste après `docker run --rm`.
- Le container s'arrête sans rien produire, ou affiche `Killed` : mémoire insuffisante. Ajoutez `-m medium` pour utiliser un modèle plus léger.
- `Warning: You are sending unauthenticated requests to the HF Hub` : message informatif de Hugging Face au premier téléchargement du modèle, sans conséquence. Si le téléchargement échoue avec une erreur `429` (trop de requêtes, cas d'une IP partagée ou de lancements répétés), créez un compte gratuit sur huggingface.co, générez un jeton de lecture dans Settings > Access Tokens, puis ajoutez `-e HF_TOKEN=hf_votre_jeton` juste après `docker run --rm` (ou exportez `HF_TOKEN` dans votre terminal si vous utilisez le raccourci de la partie 7, qui le transmet automatiquement). Le jeton ne sert qu'à ce téléchargement, rien d'autre ne part vers Hugging Face.
- Le texte sort dans une langue absurde : forcez la langue avec `-l fr`.
- Sur Windows, remplacez `$PWD` par `%cd%` dans l'invite de commandes, ou utilisez PowerShell où `$PWD` fonctionne.
- Mac avec puce Apple (M1 à M4) : l'image est prévue pour x86-64, Docker Desktop l'exécute en émulation, deux à trois fois plus lentement. Préférez `-m medium`.

Mode d'emploi complet, options avancées et construction de l'image depuis les sources : `README.md` dans le même dossier.
