#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
info() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# --- Detección de distro (Arch / Debian) -------------------------------
if command -v pacman >/dev/null 2>&1; then
    DISTRO=arch
elif command -v apt-get >/dev/null 2>&1; then
    DISTRO=debian
else
    echo "Distro no soportada. Solo se admiten derivados de Arch y Debian." >&2
    exit 1
fi
echo "==> Distro detectada: ${DISTRO}"

# --- Paquetes del sistema ----------------------------------------------
info "Instalando paquetes del sistema"
if [ "$DISTRO" = arch ]; then
    sudo pacman -S --needed --noconfirm python python-pip tk ffmpeg
else
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip python3-tk ffmpeg
fi

# --- Entorno virtual + dependencias Python ------------------------------
info "Creando entorno virtual .venv"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# --- yt-dlp (dentro del venv + enlace en ~/.local/bin) ------------------
info "Instalando yt-dlp"
.venv/bin/python -m pip install -U yt-dlp
mkdir -p "$HOME/.local/bin"
ln -sf "$(pwd)/.venv/bin/yt-dlp" "$HOME/.local/bin/yt-dlp"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac

# --- Deno ----------------------------------------------------------------
if [ -x "$HOME/.deno/bin/deno" ] || command -v deno >/dev/null 2>&1; then
    info "Deno ya instalado"
else
    info "Instalando Deno (runtime JS que usa yt-dlp para YouTube)"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL https://deno.land/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://deno.land/install.sh | sh
    else
        warn "Ni curl ni wget disponibles. Instala Deno manualmente:"
        warn "  curl -fsSL https://deno.land/install.sh | sh"
    fi
fi
export PATH="$HOME/.local/bin:$HOME/.deno/bin:$PATH"

# --- Verificación ---------------------------------------------------------
echo
echo "================ RESUMEN ================"
python3 --version
.venv/bin/python -c "import customtkinter; print('customtkinter', customtkinter.__version__)"
if command -v yt-dlp >/dev/null 2>&1; then printf 'yt-dlp '; yt-dlp --version; else warn "yt-dlp no está en el PATH"; fi
if command -v deno >/dev/null 2>&1; then deno --version | head -n1; else warn "Deno no encontrado (revisa ~/.deno/bin)"; fi
if command -v ffmpeg >/dev/null 2>&1; then ffmpeg -version | head -n1; else warn "ffmpeg no encontrado"; fi
echo "========================================="
echo
info "Listo. Ejecuta la app con:  ./launcher.sh"