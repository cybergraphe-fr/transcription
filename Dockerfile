FROM python:3.11-slim

LABEL org.opencontainers.image.title="Transcription locale" \
      org.opencontainers.image.description="Transcription audio et vidéo locale avec faster-whisper et attribution optionnelle des locuteurs" \
      org.opencontainers.image.source="https://github.com/cybergraphe-fr/cybergraphe" \
      org.opencontainers.image.version="1.0.1" \
      org.opencontainers.image.licenses="MIT"

# Versions stables vérifiées le 17 septembre 2026 ; librosa 0.11.0 est la dernière version stable compatible avec Python 3.11, la 1.0.0 exige Python 3.12.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg build-essential python3-dev \
 && rm -rf /var/lib/apt/lists/*

# L'index CPU doit être utilisé avant les dépendances applicatives pour éviter une roue CUDA.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch==2.8.0" \
 && pip install --no-cache-dir --index-url https://pypi.org/simple \
      "faster-whisper==1.2.1" \
      "resemblyzer==0.1.4" \
      "librosa==0.11.0" \
      "scikit-learn==1.9.1" \
      "yt-dlp==2026.7.4"

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin transcription \
 && mkdir -p /work /in /out /cache \
 && chown -R transcription:transcription /work /in /out /cache

COPY cli/ /opt/transcription/
COPY skill/ /skill/
RUN chmod +x /opt/transcription/transcrire.py \
 && ln -s /opt/transcription/transcrire.py /usr/local/bin/transcrire

WORKDIR /work
VOLUME ["/in", "/out", "/cache"]
ENV HF_HOME=/cache \
    XDG_CACHE_HOME=/cache
USER transcription
ENTRYPOINT ["transcrire"]
CMD ["--help"]
