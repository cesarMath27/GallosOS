    # shellcheck shell=sh
    # shellcheck disable=SC2154
    # Not a standalone script — a fragment spliced by casper-gsm-overlay.sh
    # into casper's setup_overlay() function, via awk, right before the
    # "rofsstring=${rofsstring%:}" anchor line. image_directory, croot,
    # roopt, rofsstring, and rofslist are all setup_overlay()'s own
    # variables, already in scope at the splice point — not unassigned.
    # --- GallosOS: mount .gsm SquashFS software modules into the overlay
    # stack (ROADMAP.md Phase 1 "Casper Live Boot Engine"; docs/BUILD_SYSTEM.md
    # Tier 2/3 module layout). Runs after the base-image loop above, so
    # modules take priority over the base image in the resulting lowerdir=
    # chain (overlayfs: leftmost lowerdir wins; rofsstring/rofslist above
    # are built by prepending each newly processed image, so processing
    # order here directly controls final layer priority). Variables are
    # gallos_-prefixed to avoid clashing with this function's own
    # image/imagename/backdev/fstype globals.
    gallos_medium_root=$(dirname "${image_directory}")
    for gallos_module_image in "${gallos_medium_root}/gallos/modules/"*.gsm; do
        [ -f "${gallos_module_image}" ] || continue
        gallos_module_name=$(basename "${gallos_module_image}")
        gallos_module_backdev=$(get_backing_device "$gallos_module_image")
        gallos_module_fstype=$(get_fstype "${gallos_module_backdev}")
        if [ "${gallos_module_fstype}" = "unknown" ]; then
            panic "Unknown file system type on ${gallos_module_backdev} (${gallos_module_image})"
        fi
        mkdir -p "${croot}${gallos_module_name}"
        mount -t "${gallos_module_fstype}" -o ro,noatime "${gallos_module_backdev}" "${croot}${gallos_module_name}" || panic "Can not mount $gallos_module_backdev ($gallos_module_image) on ${croot}${gallos_module_name}" && rofsstring="${croot}${gallos_module_name}=${roopt}:${rofsstring}" && rofslist="${croot}${gallos_module_name} ${rofslist}"
    done

    # Reserved Tier-3 top layer: always wins over regular modules if present.
    gallos_custom_layer="${gallos_medium_root}/gallos/system/99-custom.gsm"
    if [ -f "${gallos_custom_layer}" ]; then
        gallos_custom_name=$(basename "${gallos_custom_layer}")
        gallos_custom_backdev=$(get_backing_device "${gallos_custom_layer}")
        gallos_custom_fstype=$(get_fstype "${gallos_custom_backdev}")
        if [ "${gallos_custom_fstype}" = "unknown" ]; then
            panic "Unknown file system type on ${gallos_custom_backdev} (${gallos_custom_layer})"
        fi
        mkdir -p "${croot}${gallos_custom_name}"
        mount -t "${gallos_custom_fstype}" -o ro,noatime "${gallos_custom_backdev}" "${croot}${gallos_custom_name}" || panic "Can not mount $gallos_custom_backdev (${gallos_custom_layer}) on ${croot}${gallos_custom_name}" && rofsstring="${croot}${gallos_custom_name}=${roopt}:${rofsstring}" && rofslist="${croot}${gallos_custom_name} ${rofslist}"
    fi
    # --- end GallosOS .gsm module mounting
