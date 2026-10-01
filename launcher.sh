#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${0%/*}"
[ "$APP_DIR" = "$0" ] && APP_DIR="."
cd "$APP_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'
info() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[x]${NC} $1" >&2; }

# --- Python: venv del proyecto si existe, si no el del sistema -------------
if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
    warn "No hay .venv; usando el Python del sistema."
elif command -v python >/dev/null 2>&1; then
    PY=python
    warn "No hay .venv; usando el Python del sistema."
else
    fail "No se encontro Python 3 en el sistema."
    echo "  Instala todo con: ./setup_linux.sh"
    exit 1
fi

# --- Comprobaciones de dependencias ---------------------------------------
if ! "$PY" -c "import customtkinter" 2>/dev/null; then
    fail "Falta 'customtkinter' en $PY."
    echo "  Instala todo con: ./setup_linux.sh"
    exit 1
fi

if [ ! -f My-PyTube-DL.py ]; then
    fail "No se encuentra My-PyTube-DL.py en $(pwd)"
    exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
    warn "yt-dlp no esta en el PATH: las descargas fallaran."
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    warn "ffmpeg no esta en el PATH: no se podra fusionar video+audio."
fi

# --- Display: en sesiones Wayland la terminal suele llegar sin DISPLAY ------
# Tk (y por tanto customtkinter) solo habla X11, asi que hace falta apuntar al
# XWayland. Si no hay ninguno, no hay forma de abrir la ventana.
probe_display() {
    DISPLAY="$1" "$PY" -c 'import sys, tkinter
try:
    tkinter.Tk().destroy()
except Exception:
    sys.exit(1)' >/dev/null 2>&1
}

detect_display() {
    local sock cand
    for sock in /tmp/.X11-unix/X*; do
        [ -S "$sock" ] && [ -O "$sock" ] || continue
        cand=":${sock##*/X}"
        if probe_display "$cand"; then echo "$cand"; return 0; fi
    done
    for sock in /tmp/.X11-unix/X*; do
        [ -S "$sock" ] || continue
        cand=":${sock##*/X}"
        if probe_display "$cand"; then echo "$cand"; return 0; fi
    done
    return 1
}

if [ -z "${DISPLAY:-}" ] || ! probe_display "${DISPLAY:-}"; then
    if [ -n "${DISPLAY:-}" ]; then
        warn "DISPLAY='${DISPLAY}' no responde; buscando otro."
    fi
    if found="$(detect_display)"; then
        export DISPLAY="$found"
        info "Usando DISPLAY=${DISPLAY} (XWayland detectado automaticamente)."
    else
        fail "No hay servidor X11 disponible: Tk no puede abrir una ventana."
        echo "  - En Wayland hace falta XWayland activo (niri: 'xwayland enable')."
        echo "  - O exporta DISPLAY=:0 / :1 a mano si ya tienes uno."
        echo "  - Sin servidor X solo podrias usarla con un X virtual (Xvfb)."
        exit 1
    fi
fi

info "Iniciando My PyTube-DL..."
exec "$PY" My-PyTube-DL.py
