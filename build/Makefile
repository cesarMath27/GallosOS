# GallosOS containerized build pipeline (docs/BUILD_SYSTEM.md).
# Run from build/: `make iso CONFIG=profiles/build-icpc.toml`

IMAGE := gallos-builder
CONFIG ?= profiles/build-icpc.toml
REPO_ROOT := $(abspath ..)

.PHONY: image iso clean

image:
	podman build -t $(IMAGE) -f Containerfile .

iso: image
	podman run --rm --privileged \
		-v $(REPO_ROOT):/repo:Z \
		-w /repo/build \
		$(IMAGE) \
		bash scripts/run-pipeline.sh $(CONFIG)

clean:
	podman unshare rm -rf output/ 2>/dev/null || rm -rf output/
