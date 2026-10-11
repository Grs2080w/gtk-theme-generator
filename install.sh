#!/usr/bin/env bash
# Generate the theme from palette.conf and move it to /usr/share/themes,
# where the whole system (including GTK4/libadwaita apps) can see it.
#
# Usage:
#   ./install.sh                    # generate + move to /usr/share/themes
#   ./install.sh --apply            # generate + move + activate the theme
#   ./install.sh other.conf         # use another palette file
#
# Asks for your administrator password (sudo) to write to /usr/share/themes.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM="${OWN_THEME_DEST:-/usr/share/themes}"   # destination; the variable exists for testing
MARKER=.generated-by-own-theme      # file generate-theme.py puts in every theme it creates
LEGACY_MARKER=.gerado-por-zorin-tema
# a gsettings earlier in PATH (e.g. linuxbrew) may write to a file GNOME never reads;
# the system one writes to dconf
GSETTINGS=gsettings
[ -x /usr/bin/gsettings ] && GSETTINGS=/usr/bin/gsettings

APPLY=0
CONF="$DIR/palette.conf"
for arg in "$@"; do
    case "$arg" in
        --apply) APPLY=1 ;;
        -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "Unknown option: $arg (use --apply)" >&2; exit 1 ;;
        *) CONF="$arg" ;;
    esac
done
[ -f "$CONF" ] || { echo "Error: $CONF not found" >&2; exit 1; }

# same rule as generate-theme.py: first word after "name ="
NAME="$(sed -nE 's/^[[:space:]]*name[[:space:]]*=[[:space:]]*([^[:space:]]+).*/\1/p' "$CONF" | tail -1)"
NAME="${NAME:-ZorinCustom-Dark}"
GENERATED="$HOME/.themes/$NAME"
DEST="$SYSTEM/$NAME"

# never overwrite themes that were not created by this project (Zorin*, Adwaita…)
if [ -e "$DEST" ] && [ ! -e "$DEST/$MARKER" ] && [ ! -e "$DEST/$LEGACY_MARKER" ]; then
    echo "Error: $DEST already exists and was not created by this project." >&2
    echo "Change \"name\" in $(basename "$CONF")." >&2
    exit 1
fi

echo "==> Generating theme \"$NAME\""
python3 "$DIR/generate-theme.py" "$CONF" | grep -v '^To activate'

SUDO=sudo
[ -w "$SYSTEM" ] && SUDO=   # writable destination (tests): no sudo
echo "==> Moving $GENERATED -> $DEST${SUDO:+ (may ask for your password)}"
$SUDO rm -rf --one-file-system "$DEST"
$SUDO mv "$GENERATED" "$DEST"
[ -n "$SUDO" ] && sudo chown -R root:root "$DEST"
$SUDO chmod -R u=rwX,go=rX "$DEST"
echo "    Installed in $DEST"

if [ "$APPLY" = 1 ]; then
    echo "==> Activating"
    $GSETTINGS set org.gnome.desktop.interface color-scheme prefer-dark
    # reset first so GNOME reloads even if the name did not change
    $GSETTINGS set org.gnome.desktop.interface gtk-theme 'Adwaita'
    $GSETTINGS set org.gnome.desktop.interface gtk-theme "$NAME"
    if $GSETTINGS list-schemas | grep -qx org.gnome.shell.extensions.user-theme; then
        $GSETTINGS set org.gnome.shell.extensions.user-theme name ''
        $GSETTINGS set org.gnome.shell.extensions.user-theme name "$NAME"
    fi
    # blur = yes in palette.conf: turn on app blur in Blur my Shell
    python3 "$DIR/generate-theme.py" --blur "$CONF"
    echo "    Done. The top bar changes right away; close and reopen your apps to see the rest."
else
    echo "To activate: ./install.sh --apply  (or pick \"$NAME\" in GNOME Tweaks / Zorin Appearance)"
fi
