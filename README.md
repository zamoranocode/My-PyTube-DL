# My PyTube-DL

Descargador de vídeos de YouTube con interfaz gráfica, en Linux y Windows.
Envuelve [yt-dlp](https://github.com/yt-dlp/yt-dlp) y muestra el progreso, la
velocidad y el tiempo estimado en la propia ventana.

![customtkinter](https://img.shields.io/badge/GUI-customtkinter-24a148) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Licencia](https://img.shields.io/badge/licencia-MIT-green)

## Características

- Descarga de un vídeo o de una playlist completa.
- Elección de calidad y opción de extraer solo el audio.
- **Descargar solo una parte**: delimitas el inicio y el final con *Desde* y
  *Hasta*.
- Subtítulos en español o inglés (`--write-subs`), en `.srt` o el mejor formato
  disponible.
- Guardar la miniatura (`--write-thumbnail`).
- Sobrescribir el archivo si ya existe (`--force-overwrites`).
- Cookies del navegador (Firefox, Chrome, Edge…) para vídeos con restricción de
  edad o que exigen sesión iniciada.
- Progreso con porcentaje, velocidad y ETA, y registro de la descarga.
- Botón para **actualizar yt-dlp** sin tocar la terminal.
- Abrir el último archivo descargado con un clic.
- Menú contextual en el campo de URL: cortar, copiar, pegar y seleccionar todo.

## Requisitos

| Dependencia | Para qué | Obligatoria |
|---|---|---|
| Python 3.10 o superior | la app | sí |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | descarga | sí |
| [ffmpeg](https://ffmpeg.org/) | fusionar vídeo + audio | muy recomendable |
| [Deno](https://deno.com/) | runtime JS que yt-dlp necesita para YouTube | muy recomendable |
| Python `tkinter` | viene con Python en Linux vía paquete aparte | sí |

> En YouTube, `yt-dlp` necesita un runtime JavaScript. Sin Deno, muchas
> descargas fallarán aunque el vídeo sea público. La app comprueba si está
> disponible y lo avisa.

## Instalación

### Linux

```bash
./setup_linux.sh
```

Instala los paquetes del sistema (`python`, `tk`, `ffmpeg`), crea el entorno
`.venv`, instala las dependencias de `requirements.txt`, actualiza `yt-dlp`,
lo enlaza en `~/.local/bin` e instala Deno si falta.

### Windows

```bat
setup_windows.bat
```

Abre PowerShell y ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```

Instala `yt-dlp` con `pip --user`, crea el entorno `.venv` e instala las
dependencias de `requirements.txt`.

## Uso

```bash
./launcher.sh          # Linux
```

```bat
launcher.bat           # Windows
```

Los dos lanzadores eligen el intérprete por este orden: el `.exe` ya compilado
(solo en Windows), el entorno `.venv` del proyecto y, si no existe, el Python
del sistema. Además comprueban que falte `customtkinter`, avisan si `yt-dlp` o
`ffmpeg` no están en el `PATH` y, en Linux, buscan un servidor X11.

También puedes arrancarla directamente:

```bash
.venv/bin/python yt_gui.py
```

## Compilar a .exe (Windows)

```bat
build_windows.bat
```

Genera `dist\My-PyTube-DL.exe` en un entorno aparte (`.venv-build`)
para no tocar el de desarrollo. Usa los iconos `icono-app.ico` y
`icono-app.png` del propio
proyecto y `--clean`, así que no reutiliza nada de compilaciones anteriores.

En la máquina donde se use el `.exe` deben estar `yt-dlp` y `ffmpeg` en el
`PATH`:

```bat
pip install yt-dlp
winget install DenoLand.Deno
```

## Problemas frecuentes

### `TclError: no display name and no $DISPLAY environment variable`

La sesión es Wayland y la terminal no trae `DISPLAY`. Tk solo habla X11, así que
necesita apuntar al XWayland. `launcher.sh` lo detecta solo, pero si lo ejecutas
a mano:

```bash
DISPLAY=:1 .venv/bin/python yt_gui.py
```

En niri, comprueba que XWayland esté activo con `xwayland enable`. Sin ningún
servidor X la app no puede abrir ventana; solo funcionaría con un X virtual
(`Xvfb`), sin mostrar nada.

### `yt-dlp no está instalado o no está en el PATH`

```bash
pip install -U yt-dlp        # dentro del venv
.venv/bin/python -m pip install -U yt-dlp
```

Comprueba que `.venv/bin` esté en el `PATH` o usa siempre `launcher.sh`, que
añade esa ruta.

### La descarga falla en vídeos con restricción de edad

Elige tu navegador en *Cookies del navegador*. Requiere que ese navegador esté
abierto con la sesión iniciada.

### Faltan vídeos en una playlist

YouTube devuelve playlists incompletas. Desmarca *Cookies del navegador* o
actualiza yt-dlp desde el botón de la app.

## Estructura del proyecto

| Fichero | Función |
|---|---|
| `yt_gui.py` | toda la aplicación |
| `launcher.sh` / `launcher.bat` | lanzadores para Linux y Windows |
| `setup_linux.sh` | instalación en Linux |
| `setup_windows.bat` / `setup_windows.ps1` | instalación en Windows |
| `build_windows.bat` | empaquetado a `.exe` con PyInstaller |
| `requirements.txt` | dependencias de Python |
| `icono-app.ico` / `icono-app.png` | iconos del ejecutable y de la ventana |

La configuración se guarda en `~/.config/yt-dlp-gui/config.json`, fuera del
repositorio.

## Licencia

MIT.
