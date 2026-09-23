IMAGE ?= registry.cybergraphe.fr/transcription
VERSION ?= 1.0.1

.PHONY: build test push release

build:
	docker build -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

test:
	@mkdir -p tests/data tests/out
	@python3 -c 'import wave; w=wave.open("tests/data/exemple.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\\0\\0" * 16000); w.close()'
	docker run --rm --user "$$(id -u):$$(id -g)" -v "$$(pwd)/tests/data:/in:ro" -v "$$(pwd)/tests/out:/out" -v cybergraphe-transcription-cache:/cache $(IMAGE):$(VERSION) /in/exemple.wav -o /out

push:
	@TMP_TAR=$$(mktemp --suffix=.tar); trap 'rm -f "$$TMP_TAR"' EXIT; docker save $(IMAGE):$(VERSION) > "$$TMP_TAR"; docker run --rm --network apps -v "$$TMP_TAR:/image.tar:ro" gcr.io/go-containerregistry/crane:latest push /image.tar registry:5000/transcription:$(VERSION) --insecure

release: build
	docker tag $(IMAGE):$(VERSION) $(IMAGE):latest
