---
name: transcription
description: Transcris localement un audio, une vidéo ou une URL en verbatim horodaté, avec regroupement des morceaux et attribution relue des locuteurs.
---

# Transcription locale

Ce skill s'invoque lorsqu'un fichier audio, une vidéo, une URL, un message vocal ou un enregistrement de réunion doit être transcrit en verbatim horodaté. L'outil reste local et produit un Markdown lisible ainsi que CSV, SRT, TXT et `segments.json`.

## Commande

```sh
docker run --rm -v "$PWD:/in:ro" -v "$PWD/transcriptions:/out" -v cybergraphe-transcription-cache:/cache registry.cybergraphe.fr/transcription:1.0.2 /in/<fichier> -s auto
```

Passe plusieurs fichiers, un dossier ou une URL après le nom de l'image. Les options principales sont `-l fr|en|auto`, `-m large-v3|medium`, `-s N|auto`, `-t "titre"`, `-w`, `-g 120` et `--names '{"S1":"Alice","S2":"Bob"}'`. Le wrapper `transcrire.sh` du skill ajoute automatiquement les montages et l'UID courant, et transmet `HF_TOKEN` si la variable existe dans le shell. Au premier lancement, la ligne `Warning: You are sending unauthenticated requests to the HF Hub` vient du serveur Hugging Face pendant le téléchargement du modèle : informative, sans action à mener, elle disparaît une fois le modèle en cache ; un jeton n'est utile qu'en cas d'erreur 429.

## Vidéos auto-découpées

Les Ray-Ban Meta, dashcams et dictaphones produisent parfois des morceaux de 1, 3 ou 5 minutes. En passant le dossier entier, le nom de fichier est prioritaire pour l'horodatage, puis viennent `creation_time` et enfin le mtime moins la durée. Les morceaux sont fusionnés quand l'écart entre la fin et le début suivant est compris entre -60 secondes et la tolérance `-g`, avec 120 secondes par défaut. Chaque groupe reçoit un `parts.json` et une table des morceaux dans le Markdown.

## Relecture et garde-fous

Les locuteurs sont étiquetés `S1`, `S2`, etc. dans l'ordre d'apparition. Relis l'audio et renomme-les avec `--names` quand le contexte le permet. Une attribution incertaine doit rester marquée comme telle et ne doit jamais être présentée comme un fait. Le verbatim reste fidèle, sans reformulation ni suppression des hésitations porteuses de sens, et `segments.json` doit être conservé pour toute correction ou nouveau rendu.

Tout le traitement est local. Les seules connexions sortantes sont le téléchargement initial du modèle depuis Hugging Face et le téléchargement demandé pour une URL via yt-dlp. L'attribution des voix devient peu fiable dans le bruit, sur les segments très courts ou pour des voix proches. Avec `large-v3`, prévoir environ une fois la durée audio sur 12 cœurs et 10 Go de RAM ; utiliser `-m medium` pour une machine plus limitée ou un brouillon long.

## Dépannage

- Cache refusé : vérifie que le volume `cybergraphe-transcription-cache` est accessible à l'UID passé au container et laisse le modèle se télécharger de nouveau si un ancien lancement a créé des fichiers root.
- Langue absurde ou sortie vide : force `-l fr` ou la langue attendue au lieu de `auto`.
- Mémoire insuffisante : passe `-m medium` et réduis les autres charges de la machine.
- URL refusée : vérifie l'URL avec yt-dlp, puis télécharge le fichier manuellement et passe son chemin au container.
- Fusion inattendue : passe `-g 0` si les mtimes ont été réécrits ; passe une tolérance plus grande si les noms de fichiers sont fiables.
