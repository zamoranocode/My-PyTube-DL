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

# --- Comprobación de sudo antes de pedir contraseña ----------------------
# set -e aborta en cuanto sudo falla; con -n fallamos ya con un mensaje claro.
if [ "$(id -u)" -ne 0 ]; then
    if ! sudo -n true 2>/dev/null; then
        echo "Se necesita sudo para instalar paquetes del sistema." >&2
        echo "Ejecuta de nuevo este script con una contraseña disponible, o" >&2
        echo "instala a mano: python3 python3-venv python3-tk ffmpeg" >&2
        exit 1
    fi
fi

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
# requirements.txt ya trae yt-dlp; -U lo deja al día.
info "Instalando/actualizando yt-dlp"
.venv/bin/python -m pip install -U yt-dlp
mkdir -p "$HOME/.local/bin"
# Enlace al ejecutable del venv. La app también lo busca por su cuenta, así que
# si mueves el proyecto basta con borrar este enlace y rehacerlo.
ln -sf "$(pwd)/.venv/bin/yt-dlp" "$HOME/.local/bin/yt-dlp"

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

# --- PATH persistente ----------------------------------------------------
# Sin esto, las carpetas quedan solo en el PATH de esta sesión y una terminal
# nueva (o un .desktop, que no sourcea el rc) se queda sin yt-dlp ni Deno.
persist_path() {
    local dir="$1" marker="# >>> My PyTube-DL >>>"
    mkdir -p "$HOME/.local/bin"
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        [ -f "$rc" ] || continue
        if grep -qF "$dir" "$rc"; then continue; fi
        {
            echo ""
            echo "$marker"
            echo "[ -d \"$dir\" ] && PATH=\"\$PATH:$dir\""
            echo "export PATH"
            echo "# <<< My PyTube-DL <<<"
        } >> "$rc"
        info "PATH actualizado en $(basename "$rc")"
    done
}

persist_path "$HOME/.local/bin"
persist_path "$HOME/.deno/bin"

# Para el resto de este script y para el proceso que lanzamos.
export PATH="$HOME/.local/bin:$HOME/.deno/bin:$PATH"

# --- Verificación ---------------------------------------------------------
echo
echo "================ RESUMEN ================"
.venv/bin/python --version
.venv/bin/python -c "import customtkinter; print('customtkinter', customtkinter.__version__)"
if command -v yt-dlp >/dev/null 2>&1; then printf 'yt-dlp '; yt-dlp --version; else warn "yt-dlp no está en el PATH"; fi
if command -v deno >/dev/null 2>&1; then deno --version | head -n1; else warn "Deno no encontrado (revisa ~/.deno/bin)"; fi
if command -v ffmpeg >/dev/null 2>&1; then ffmpeg -version | head -n1; else warn "ffmpeg no encontrado"; fi
if [ -f My-PyTube-DL.py ]; then echo "app: My-PyTube-DL.py"; else warn "falta My-PyTube-DL.py"; fi
echo "========================================="
echo
info "Listo. Ejecuta la app con:  ./launcher.sh"
