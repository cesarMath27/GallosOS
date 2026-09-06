# GallosOS kiosk session launcher (docs/WAYLAND_DESKTOP.md §3).
# Sourced by the contestant's login shell on the autologin tty1; execs labwc
# with the immutable /etc/xdg/labwc configuration directory.
# shellcheck shell=sh
if [ -z "${WAYLAND_DISPLAY:-}" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export XDG_CURRENT_DESKTOP=labwc
    export XDG_SESSION_TYPE=wayland
    export MOZ_ENABLE_WAYLAND=1
    export QT_QPA_PLATFORM=wayland
    export GDK_BACKEND=wayland,x11
    export XDG_CONFIG_DIRS=/etc/xdg
    export GALLOS_WORKSPACE="$HOME/workspace"

    # Keyboard layouts: baked defaults, overridden by gallos-daemon's export of
    # [global].available_keyboard_layouts / default_keyboard_layout
    # (/run/gallos/desktop.env). Super+Space and Alt+Shift cycle the groups —
    # handled by XKB itself, so it works identically in every window.
    export XKB_DEFAULT_LAYOUT="latam,us,es,br"
    export XKB_DEFAULT_OPTIONS="grp:win_space_toggle,grp:alt_shift_toggle"
    _i=0
    while [ ! -r /run/gallos/desktop.env ] && [ "$_i" -lt 10 ]; do
        sleep 0.2
        _i=$((_i + 1))
    done
    if [ -r /run/gallos/desktop.env ]; then
        # shellcheck disable=SC1091
        . /run/gallos/desktop.env
        export XKB_DEFAULT_LAYOUT XKB_DEFAULT_OPTIONS
    fi
    unset _i

    mkdir -p "$GALLOS_WORKSPACE" 2>/dev/null

    # Prefer the systemd user bus (dbus-user-session) so root-side
    # gallos-daemon notifications can reach mako at a well-known address;
    # fall back to a private dbus-run-session bus otherwise.
    if [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus" ]; then
        export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus"
        exec labwc -C /etc/xdg/labwc
    else
        exec dbus-run-session labwc -C /etc/xdg/labwc
    fi
fi
