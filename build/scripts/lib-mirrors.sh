#!/usr/bin/env bash
# Apt mirror resolution, sourced by 01-bootstrap.sh.
#
# Investigation this session (see docs/BUILD_SYSTEM.md §3 Stage 1) found
# that Canonical's ubuntu-base tarball is effectively single-source
# (cdimage.ubuntu.com only — a real community mirror that does carry the
# ubuntu-releases tree, mirror.aarnet.edu.au, returned 404 for ubuntu-base),
# so mirror flexibility belongs at the apt-archive layer instead, which
# genuinely is broadly mirrored.

# Ordered fallback list, tried in sequence when [build].apt_mirror is
# "auto"/unset. Each entry verified reachable and serving the `noble`
# (24.04) suite at the time this was written — mirror uptime isn't
# guaranteed indefinitely, hence a short list rather than a single host.
GALLOS_MIRROR_FALLBACKS=(
    "http://archive.ubuntu.com/ubuntu/"
    "http://mirror.kumi.systems/ubuntu/"
    "http://mirror.aarnet.edu.au/pub/ubuntu/archive/"
)

# pick_apt_mirror <suite> <configured>
# Prints the chosen mirror base URL (trailing slash) on stdout. <configured>
# is build.toml's [build].apt_mirror value: "", "auto" -> try the fallback
# list in order; any other value -> treated as an explicit URL and used as
# given (checked, not silently substituted if unreachable — an organizer
# who names a specific mirror should get a clear failure, not a swap).
pick_apt_mirror() {
    local suite="$1"
    local configured="$2"

    if [[ -n "$configured" && "$configured" != "auto" ]]; then
        if curl -sf --max-time 8 -o /dev/null "${configured%/}/dists/$suite/Release"; then
            echo "${configured%/}/"
            return 0
        fi
        echo "pick_apt_mirror: configured mirror '$configured' is unreachable (suite=$suite)" >&2
        return 1
    fi

    local m
    for m in "${GALLOS_MIRROR_FALLBACKS[@]}"; do
        if curl -sf --max-time 8 -o /dev/null "${m}dists/$suite/Release"; then
            echo "$m"
            return 0
        fi
        echo "pick_apt_mirror: $m unreachable, trying next..." >&2
    done
    echo "pick_apt_mirror: no mirror in the fallback list is reachable" >&2
    return 1
}
