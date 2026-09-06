# GallosOS containerized build pipeline (docs/BUILD_SYSTEM.md).
# Run from build/: `make iso CONFIG=profiles/icpc.toml`

CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

ifeq ($(strip $(CONTAINER_ENGINE)),)
$(error Neither 'podman' nor 'docker' was found in PATH. Please install Podman or Docker to build GallosOS.)
endif

# WSL2: when Docker Desktop's WSL integration is not active for this distro,
# PATH falls through to the *Windows* docker.exe under /mnt/c/... — its path
# contains a space and, worse, it cannot bind-mount WSL paths into the build
# container. Fail early with the fix instead of a cryptic "No such file".
ifneq (,$(findstring /mnt/,$(CONTAINER_ENGINE)))
$(error CONTAINER_ENGINE resolved to a Windows binary: '$(CONTAINER_ENGINE)'. Start Docker Desktop and enable Settings > Resources > WSL integration for this distro (so /usr/bin/docker exists), then run `which docker` to confirm before retrying)
endif

IMAGE := gallos-builder
CONFIG ?= profiles/icpc.toml
REPO_ROOT := $(abspath ..)

.PHONY: image iso clean

image:
	"$(CONTAINER_ENGINE)" build -t $(IMAGE) -f Containerfile .

iso: image
	"$(CONTAINER_ENGINE)" run --rm --privileged \
		--security-opt label=disable \
		-v $(REPO_ROOT):/repo \
		-w /repo/build \
		$(IMAGE) \
		bash scripts/run-pipeline.sh $(CONFIG)

clean:
	command -v podman >/dev/null 2>&1 && podman unshare rm -rf output/ 2>/dev/null || rm -rf output/
