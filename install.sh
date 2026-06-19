#!/usr/bin/env bash
# Install lore to ~/.local/bin. Mirrors sandy's installer.
#   Local:  LOCAL_INSTALL=./lore ./install.sh
#   Remote: curl -fsSL <raw-url>/install.sh | bash   (once published)
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
LORE_URL="${LORE_URL:-https://raw.githubusercontent.com/rappdw/lore/main/lore}"

info() { printf '\033[0;32m[lore]\033[0m %s\n' "$*"; }
warn() { printf '\033[0;33m[lore]\033[0m %s\n' "$*"; }

if ! command -v python3 >/dev/null 2>&1; then
    warn "python3 not found — lore needs Python 3.9+ on PATH."
    exit 1
fi

mkdir -p "$INSTALL_DIR"

# Resolve the source, in order: explicit LOCAL_INSTALL, else the `lore`
# executable sitting next to this script (a checked-out repo), else download.
# This means `cd lore && ./install.sh` just works — and we never silently fall
# through to a download when a local copy is right there.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SRC=""
if [ -n "${LOCAL_INSTALL:-}" ]; then
    if [ -f "$LOCAL_INSTALL" ]; then
        SRC="$LOCAL_INSTALL"
    else
        warn "LOCAL_INSTALL=$LOCAL_INSTALL does not exist."
        exit 1
    fi
elif [ -f "$SCRIPT_DIR/lore" ]; then
    SRC="$SCRIPT_DIR/lore"
fi

if [ -n "$SRC" ]; then
    info "Installing lore from $SRC"
    cp "$SRC" "$INSTALL_DIR/lore"
    # Bake the git short hash so `lore --version` shows it (best-effort).
    local_dir="$(cd "$(dirname "$SRC")" && pwd)"
    if commit_hash="$(git -C "$local_dir" rev-parse --short HEAD 2>/dev/null)"; then
        if sed --version >/dev/null 2>&1; then
            sed -i "s/^LORE_COMMIT = \"\"/LORE_COMMIT = \"$commit_hash\"/" "$INSTALL_DIR/lore"
        else
            sed -i '' "s/^LORE_COMMIT = \"\"/LORE_COMMIT = \"$commit_hash\"/" "$INSTALL_DIR/lore"
        fi
    fi
else
    info "Downloading lore from $LORE_URL"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$LORE_URL" -o "$INSTALL_DIR/lore"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$INSTALL_DIR/lore" "$LORE_URL"
    else
        warn "Need curl or wget to download lore."
        exit 1
    fi
fi

chmod +x "$INSTALL_DIR/lore"
info "Installed lore to $INSTALL_DIR/lore"

if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    warn "$INSTALL_DIR is not in your PATH. Add it with:"
    case "$(basename "${SHELL:-}")" in
        zsh)  warn "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
        bash) warn "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.bashrc && source ~/.bashrc" ;;
        fish) warn "  fish_add_path $INSTALL_DIR" ;;
        *)    warn "  export PATH=\"$INSTALL_DIR:\$PATH\"" ;;
    esac
fi

info "Optional: 'sandy' on PATH (for sandbox enumeration) and 'claude' (for v0b+ summarize/relevant)."
