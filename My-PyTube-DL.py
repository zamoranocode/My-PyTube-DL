#!/usr/bin/env python3
import glob
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

APP_NAME = "My PyTube-DL"
CONFIG_PATH = Path.home() / ".config" / "yt-dlp-gui" / "config.json"
YTDLP_GH_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

QUALITY_PRESETS = {
    "720p (MKV)": {
        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[height<=720]",
        "container": "mkv",
        "audio": False,
        "height": 720,
    },
    "1080p (MKV)": {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[height<=1080]",
        "container": "mkv",
        "audio": False,
        "height": 1080,
    },
    "4K / 2160p (MKV)": {
        "format": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        "container": "mkv",
        "audio": False,
        "height": 2160,
    },
    "Mejor calidad (MKV)": {
        "format": "bestvideo+bestaudio/best",
        "container": "mkv",
        "audio": False,
    },
    "Solo audio (MP3)": {
        "format": "bestaudio/best",
        "container": "mp3",
        "audio": True,
    },
}

PROGRESS_PREFIX = "@@YTDLP_PROGRESS@@"
FINAL_PREFIX = "@@YTDLP_FINAL@@:"
VIDEO_TEMPLATE = "%(uploader)s/%(uploader)s - %(upload_date>%Y%m%d)s - %(title)s - [%(height)sp].%(ext)s"
AUDIO_TEMPLATE = "%(uploader)s/%(uploader)s - %(upload_date>%Y%m%d)s - %(title)s.%(ext)s"

NO_WINDOW_KWARGS = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)


def default_dir():
    home = Path.home()
    if sys.platform == "win32":
        base = Path(os.environ.get("USERPROFILE", home))
    else:
        base = home
    return base / "Vídeos" / "YouTube"


def normalize_version(v):
    return str(v or "").strip().lower().lstrip("v")


def version_tuple(v):
    parts = []
    for p in re.split(r"[.\-_]+", normalize_version(v)):
        parts.append(int(p) if p.isdigit() else p)
    return parts


def is_newer(a, b):
    a, b = version_tuple(a), version_tuple(b)
    n = max(len(a), len(b))
    a += [0] * (n - len(a))
    b += [0] * (n - len(b))
    return a > b


def fetch_latest_version():
    try:
        req = urllib.request.Request(YTDLP_GH_API, headers={"User-Agent": "yt-dlp-gui/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        return normalize_version(data.get("tag_name"))
    except Exception:
        return None


def get_local_version():
    try:
        out = subprocess.run(
            ["yt-dlp", "--version"], capture_output=True, text=True, timeout=30,
            **NO_WINDOW_KWARGS
        )
        if out.returncode == 0:
            return normalize_version(out.stdout.strip() or out.stderr.strip())
    except Exception:
        pass
    return None


def find_deno():
    p = shutil.which("deno")
    if p:
        return p
    for cand in (
        Path.home() / ".deno" / "bin" / "deno",
        Path.home() / ".deno" / "bin" / "deno.exe",
    ):
        if cand.exists():
            return str(cand)
    return None


def get_deno_version():
    deno = find_deno()
    if not deno:
        return None
    try:
        out = subprocess.run(
            [deno, "--version"], capture_output=True, text=True, timeout=15,
            **NO_WINDOW_KWARGS
        )
        first = (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else ""
        m = re.search(r"deno[\s]+([\d.]+)", first, re.I)
        return m.group(1) if m else first.strip()
    except Exception:
        return None


def _resource_path(name):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / name
    return Path(__file__).resolve().parent / name


def find_ytdlp():
    p = shutil.which("yt-dlp")
    if p:
        return p
    for cand in (
        Path(sys.executable).parent / "yt-dlp",
        Path(sys.executable).parent / "yt-dlp.exe",
        _resource_path("yt-dlp"),
        _resource_path("yt-dlp.exe"),
    ):
        if cand.exists():
            return str(cand)
    return None


# Perfiles de navegador donde yt-dlp puede buscar la base de cookies. Los
# navegadores ausentes de esta tabla no se ofrecen, porque cualquier otro
# nombre hace fallar la extracción con "unsupported browser specified for
# cookies".
#
# "key" es la clave que yt-dlp acepta. Los navegadores que yt-dlp no conoce
# (Brave Origin Beta, Zen) o cuya carpeta de perfiles no es la que busca por su
# cuenta se resuelven siempre con la sintaxis "clave:ruta_absoluta", que
# yt-dlp admite cuando la parte tras ":" es una ruta.
#
# "home" marca las rutas relativas a la carpeta de configuración del sistema;
# las de "~" se expanden directamente desde el directorio personal.
COOKIE_BROWSER_PROFILES = {
    "Brave": {
        "key": "brave",
        "home": {
            "linux": ["BraveSoftware/Brave-Browser"],
            "darwin": ["BraveSoftware/Brave-Browser", "BraveSoftware/Brave-Browser-Beta",
                       "BraveSoftware/Brave-Browser-Nightly"],
            "win32": [r"BraveSoftware\Brave-Browser\User Data"],
        },
    },
    "Brave (Origin Beta)": {
        "key": "brave",
        "home": {"linux": ["BraveSoftware/Brave-Origin-Beta"]},
    },
    "Chromium": {
        "key": "chromium",
        "home": {
            "linux": ["chromium"],
            "darwin": ["Chromium"],
            "win32": [r"Chromium\User Data"],
        },
    },
    "Edge": {
        "key": "edge",
        "home": {
            "linux": ["microsoft-edge", "microsoft-edge-beta", "microsoft-edge-dev"],
            "darwin": ["Microsoft Edge", "Microsoft Edge Beta"],
            "win32": [r"Microsoft\Edge\User Data"],
        },
    },
    "Firefox": {
        "key": "firefox",
        "home": {"linux": ["mozilla/firefox"], "darwin": [], "win32": []},
        "~": [".mozilla/firefox",
              ".var/app/org.mozilla.firefox/config/mozilla/firefox",
              ".var/app/org.mozilla.firefox/.mozilla/firefox",
              "snap/firefox/common/.mozilla/firefox",
              "Library/Application Support/Firefox/Profiles"],
    },
    "Google Chrome": {
        "key": "chrome",
        "home": {
            "linux": ["google-chrome", "google-chrome-beta", "google-chrome-unstable"],
            "darwin": ["Google/Chrome", "Google/Chrome Beta", "Google/Chrome Canary"],
            "win32": [r"Google\Chrome\User Data"],
        },
    },
    "Opera": {
        "key": "opera",
        "home": {
            "linux": ["opera"],
            "darwin": ["com.operasoftware.Opera", "com.operasoftware.OperaNext"],
            "win32": [r"Opera Software\Opera Stable"],
        },
    },
    "Vivaldi": {
        "key": "vivaldi",
        "home": {
            "linux": ["vivaldi"],
            "darwin": ["Vivaldi"],
            "win32": [r"Vivaldi\User Data"],
        },
    },
    "Zen Browser": {
        # Derivado de Firefox con su propia carpeta de perfiles: yt-dlp no lo
        # conoce, así que se le pasa la ruta explícita con la clave de firefox.
        "key": "firefox",
        "home": {"linux": [], "darwin": [], "win32": []},
        "~": [".zen"],
    },
}

_COOKIE_DB_NAMES = ("Cookies", "cookies.sqlite")


def _cookie_home():
    if sys.platform == "win32":
        return os.path.expandvars("%LOCALAPPDATA%")
    if sys.platform == "darwin":
        return str(Path.home() / "Library" / "Application Support")
    return os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")


def _has_cookie_db(root):
    """True si hay una base de cookies de perfil dentro de `root`."""
    root = os.path.expanduser(root)
    if not os.path.isdir(root):
        return False
    for name in _COOKIE_DB_NAMES:
        for depth in ("", "*/", "*/*/"):
            pattern = os.path.join(root, depth, name)
            try:
                if glob.glob(pattern):
                    return True
            except OSError:
                continue
    return False


def find_cookie_browsers():
    """Navegadores con base de cookies real en este equipo.

    Devuelve {nombre visible: valor para --cookies-from-browser}, con "Ninguno"
    primero y el resto en orden alfabético. Se omiten los navegadores
    instalados pero nunca utilizados, porque en ellos la extracción falla con
    "could not find ... cookies database".
    """
    found = {}
    for name, spec in COOKIE_BROWSER_PROFILES.items():
        key = spec["key"]
        candidates = [os.path.join(_cookie_home(), r)
                      for r in spec["home"].get(sys.platform, [])]
        candidates += [os.path.expanduser("~/" + r) for r in spec.get("~", ())]
        for root in candidates:
            if not _has_cookie_db(root):
                continue
            found[name] = f"{key}:{os.path.abspath(root)}"
            break
    return {"Ninguno": None, **dict(sorted(found.items()))}


MENU_BG = "#2b2b2b"
MENU_BORDER = "#454545"
MENU_FG = "#e6e6e6"
MENU_HOVER = "#3d3d3d"
MENU_DISABLED = "#7f7f7f"


class DarkMenu(ctk.CTkToplevel):
    """Menú contextual con el tema oscuro de la app.

    tk.Menu usa los colores del sistema y rompía el aspecto, así que se
    reemplaza por una ventana sin marco con botones de customtkinter.

    `items` es una lista de tuplas (etiqueta, comando, habilitada) o None para
    un separador. `habilitada` es un booleano o un callable sin argumentos que
    se evalúa cada vez que se abre el menú, para poder activar o desactivar
    "Cortar"/"Copiar" según haya selección.
    """

    ITEM_HEIGHT = 30
    PADDING = 6

    def __init__(self, master, items):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.resizable(False, False)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        self._closed = False
        self._items = items
        self._buttons = {}

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True)
        panel = ctk.CTkFrame(
            outer, fg_color=MENU_BG, corner_radius=8, border_width=1, border_color=MENU_BORDER
        )
        panel.pack(fill="both", expand=True, padx=2, pady=2)

        for item in items:
            if item is None:
                ctk.CTkFrame(panel, height=1, fg_color="#4d4d4d").pack(
                    fill="x", padx=10, pady=4
                )
                continue
            label, command, enabled = item
            btn = ctk.CTkButton(
                panel, text=label, command=self._wrap(command), height=self.ITEM_HEIGHT,
                width=190, fg_color="transparent", hover_color=MENU_HOVER,
                text_color=MENU_FG, text_color_disabled=MENU_DISABLED, anchor="w",
                corner_radius=6,
            )
            btn.pack(fill="x", padx=6, pady=1)
            self._buttons[label] = (btn, enabled)

        self.bind("<Escape>", lambda e: self.close())
        # El grab envía aquí los clics que caen fuera del panel; cualquier otro
        # clic debe cerrar el menú para no bloquear la ventana principal.
        self.bind("<Button-1>", lambda e: self.close())
        self.bind("<FocusOut>", lambda e: self.close())

    def _wrap(self, command):
        def run():
            self.close()
            if command:
                command()

        return run

    def _refresh_states(self):
        for label, (btn, enabled) in self._buttons.items():
            state = bool(enabled() if callable(enabled) else enabled)
            btn.configure(state="normal" if state else "disabled")

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def popup_at(self, x, y):
        self.update_idletasks()
        self._refresh_states()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = max(self.PADDING, min(int(x), self.winfo_screenwidth() - w - self.PADDING))
        y = max(self.PADDING, min(int(y), self.winfo_screenheight() - h - self.PADDING))
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.lift()
        try:
            self.grab_set()
        except Exception:
            pass
        self.focus_force()


class YTDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("700x710")
        self.minsize(640, 660)
        self.resizable(True, True)

        self.ui_queue = queue.Queue()
        self.config = self.load_config()
        self.cookie_browsers = find_cookie_browsers()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.url_var = ctk.StringVar()
        quality = self.config.get("quality")
        if quality not in QUALITY_PRESETS:
            quality = "1080p (MKV)"
        self.quality_var = ctk.StringVar(value=quality)
        cookies = self.config.get("cookies")
        if cookies not in self.cookie_browsers:
            cookies = "Ninguno"
        self.cookies_var = ctk.StringVar(value=cookies)
        self.dir_var = ctk.StringVar(value=self.config.get("download_dir", str(default_dir())))
        self.write_thumb_var = ctk.BooleanVar(value=bool(self.config.get("write_thumb", True)))
        self.overwrite_var = ctk.BooleanVar(value=bool(self.config.get("overwrite", False)))
        self.subs_es_var = ctk.BooleanVar(value=bool(self.config.get("subs_es", False)))
        self.subs_en_var = ctk.BooleanVar(value=bool(self.config.get("subs_en", False)))
        self.range_enabled = ctk.BooleanVar(value=False)
        self.start_var = ctk.StringVar()
        self.end_var = ctk.StringVar()
        self.pct_var = ctk.StringVar(value="0.0%")
        self.speed_var = ctk.StringVar(value="Velocidad: --")
        self.eta_var = ctk.StringVar(value="ETA: --")
        self.status_var = ctk.StringVar(value="Preparado.")
        self.version_var = ctk.StringVar(value="Comprobando yt-dlp...")
        self.deno_var = ctk.StringVar(value="Deno: detectando...")
        self.last_file = None
        self.proc = None

        self._build_ui()
        self._center_window()
        self._set_icon()
        self.bind_all("<Control-w>", lambda e: self.request_close())
        self.protocol("WM_DELETE_WINDOW", self.request_close)

        self.downloading = False
        self.after(50, self._poll_queue)
        threading.Thread(target=self._version_check_worker, daemon=True).start()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=16)

        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.pack(fill="x", side="bottom")
        ctk.CTkLabel(footer, textvariable=self.version_var, font=ctk.CTkFont(size=12)).pack(side="left")
        self.deno_label = ctk.CTkLabel(footer, textvariable=self.deno_var, font=ctk.CTkFont(size=12))
        self.deno_label.pack(side="right")

        self.update_btn = ctk.CTkButton(
            footer, text="Actualizar yt-dlp", width=150, height=28, command=self.start_update
        )

        ctk.CTkLabel(
            container, text="📥 " + APP_NAME, font=ctk.CTkFont(size=24, weight="bold")
        ).pack(anchor="w")

        url_frame = ctk.CTkFrame(container, fg_color="transparent")
        url_frame.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(url_frame, text="URL del video / playlist", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self.url_entry = ctk.CTkEntry(url_frame, textvariable=self.url_var, placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.pack(fill="x", pady=(6, 0))
        self._add_edit_menu(self.url_entry)

        row1 = ctk.CTkFrame(container, fg_color="transparent")
        row1.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(row1, text="Calidad", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.quality_menu = ctk.CTkOptionMenu(
            row1, values=list(QUALITY_PRESETS), variable=self.quality_var, width=200
        )
        self.quality_menu.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(row1, text="Cookies del navegador", font=ctk.CTkFont(size=13)).grid(row=0, column=2, sticky="w", padx=(24, 8))
        self.cookies_menu = ctk.CTkOptionMenu(
            row1, values=list(self.cookie_browsers), variable=self.cookies_var, width=180
        )
        self.cookies_menu.grid(row=0, column=3, sticky="w")
        row1.grid_columnconfigure(1, weight=0)
        row1.grid_columnconfigure(3, weight=1)

        dir_frame = ctk.CTkFrame(container, fg_color="transparent")
        dir_frame.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(dir_frame, text="Carpeta de descarga", font=ctk.CTkFont(size=13)).pack(anchor="w")
        dir_row = ctk.CTkFrame(dir_frame, fg_color="transparent")
        dir_row.pack(fill="x", pady=(6, 0))
        self.dir_entry = ctk.CTkEntry(dir_row, textvariable=self.dir_var)
        self.dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_row, text="Buscar...", width=90, command=self.choose_dir).pack(side="left", padx=(8, 0))

        range_frame = ctk.CTkFrame(container, fg_color="transparent")
        range_frame.pack(fill="x", pady=(14, 0))
        ctk.CTkCheckBox(
            range_frame, text="Descargar solo una parte del video", variable=self.range_enabled,
            command=self._toggle_range,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ctk.CTkLabel(range_frame, text="Desde:").grid(row=0, column=2, sticky="w", padx=(20, 4))
        self.start_entry = ctk.CTkEntry(range_frame, textvariable=self.start_var, width=88, placeholder_text="00:00")
        self.start_entry.grid(row=0, column=3, sticky="w")
        ctk.CTkLabel(range_frame, text="Hasta:").grid(row=0, column=4, sticky="w", padx=(12, 4))
        self.end_entry = ctk.CTkEntry(range_frame, textvariable=self.end_var, width=88, placeholder_text="10:30")
        self.end_entry.grid(row=0, column=5, sticky="w")
        range_frame.grid_columnconfigure(1, weight=1)
        self.start_entry.configure(state="disabled")
        self.end_entry.configure(state="disabled")

        opt_frame = ctk.CTkFrame(container, fg_color="transparent")
        opt_frame.pack(fill="x", pady=(14, 0))
        opt_left = ctk.CTkFrame(opt_frame, fg_color="transparent")
        opt_left.grid(row=0, column=0, sticky="w")
        opt_right = ctk.CTkFrame(opt_frame, fg_color="transparent")
        opt_right.grid(row=0, column=1, sticky="w", padx=(24, 0))
        ctk.CTkCheckBox(
            opt_left, text="Guardar miniatura (--write-thumbnail)", variable=self.write_thumb_var
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkCheckBox(
            opt_left, text="Sobrescribir si ya existe (--force-overwrites)", variable=self.overwrite_var
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ctk.CTkCheckBox(
            opt_right, text="Subtítulos en español", variable=self.subs_es_var
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkCheckBox(
            opt_right, text="Subtítulos en inglés", variable=self.subs_en_var
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(16, 0))
        self.download_btn = ctk.CTkButton(
            btn_row, text="⬇️  Descargar", height=44, font=ctk.CTkFont(size=16, weight="bold"),
            command=self.start_download,
        )
        self.download_btn.pack(side="left", fill="x", expand=True)
        self.open_btn = ctk.CTkButton(
            btn_row, text="Abrir archivo", width=120, height=44, state="disabled",
            command=self.open_last_file,
        )
        self.open_btn.pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btn_row, text="Limpiar", width=100, height=44, fg_color="#494b52",
            hover_color="#5a5c66", command=self.clear_fields,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btn_row, text="Cerrar", width=90, height=44, fg_color="#8b2f2f",
            hover_color="#a53a3a", command=self.request_close,
        ).pack(side="left", padx=(8, 0))

        progress_frame = ctk.CTkFrame(container, fg_color="transparent")
        progress_frame.pack(fill="x", pady=(14, 0))
        stats = ctk.CTkFrame(progress_frame, fg_color="transparent")
        stats.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(stats, textvariable=self.pct_var, font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkLabel(stats, textvariable=self.speed_var).pack(side="left", padx=16)
        ctk.CTkLabel(stats, textvariable=self.eta_var).pack(side="left")
        self.progress = ctk.CTkProgressBar(progress_frame, height=14)
        self.progress.set(0)
        self.progress.pack(side="right", fill="x", expand=True)

        log_frame = ctk.CTkFrame(container, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, pady=(12, 0))
        ctk.CTkLabel(log_frame, text="Registro", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self.log_box = ctk.CTkTextbox(
            log_frame, height=110, wrap="word",
            font=ctk.CTkFont(family="monospace", size=12),
            fg_color="#000000", text_color="#00FF00",
            border_width=1, border_color="#2b2b2b", corner_radius=4,
        )
        self.log_box.pack(fill="both", expand=True, pady=(6, 0))
        self.log_box.configure(state="disabled")
        self.log_box._textbox.tag_configure("sel", foreground="#00FF00", background="#1f4d1f")

        ctk.CTkLabel(
            container, textvariable=self.status_var, wraplength=660, justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(fill="x", pady=(10, 0), anchor="w")

    def _toggle_range(self):
        state = "normal" if self.range_enabled.get() else "disabled"
        self.start_entry.configure(state=state)
        self.end_entry.configure(state=state)

    def _log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text.rstrip() + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_fields(self):
        self.last_file = None
        self.open_btn.configure(state="disabled")
        self.url_var.set("")
        self.range_enabled.set(False)
        self.start_var.set("")
        self.end_var.set("")
        self._toggle_range()
        self.progress.set(0)
        self.pct_var.set("0.0%")
        self.speed_var.set("Velocidad: --")
        self.eta_var.set("ETA: --")
        self.status_var.set("Campos limpiados.")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def request_close(self):
        if self.downloading:
            if not messagebox.askyesno("Cerrar", "Hay una descarga en curso. ¿Cerrar de todos modos?"):
                return
        self._stop_proc()
        self.destroy()

    def _stop_proc(self):
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _add_edit_menu(self, widget):
        # CTkEntry es un Frame que envuelve un tkinter.Entry en _entry, y el clic
        # cae sobre ese Entry interno. En Tk los bindings no suben al padre, asi
        # que hay que enlazarlos al Entry de dentro, no al wrapper. Se comprueba
        # por duck-typing: un Frame no tiene insert/selection_range, un Entry si.
        inner = getattr(widget, "_entry", None)
        if inner is not None and hasattr(inner, "insert") and hasattr(inner, "selection_range"):
            target = inner
        else:
            target = widget

        state = {"entry": target}

        def entry():
            return state.get("entry")

        def get_clipboard():
            ent = entry()
            if ent is None:
                return None
            try:
                return ent.clipboard_get()
            except tk.TclError:
                pass
            if sys.platform.startswith("linux"):
                try:
                    return ent.selection_get(selection="PRIMARY")
                except tk.TclError:
                    pass
            return None

        def get_selection():
            ent = entry()
            if ent is None:
                return None
            try:
                return ent.selection_get()
            except tk.TclError:
                return None

        def put_clipboard(text):
            ent = entry()
            if ent is None or text is None:
                return False
            ent.clipboard_clear()
            ent.clipboard_append(text)
            return True

        def do_cut():
            ent = entry()
            if ent is not None and put_clipboard(get_selection()):
                ent.delete("sel.first", "sel.last")

        def do_copy():
            put_clipboard(get_selection())

        def do_paste():
            ent = entry()
            text = get_clipboard()
            if ent is None or not text:
                return
            if ent.selection_present():
                ent.delete("sel.first", "sel.last")
            ent.insert("insert", text)

        def do_select_all():
            ent = entry()
            if ent is not None:
                ent.selection_range(0, "end")

        def ent_has_selection():
            ent = entry()
            return bool(ent is not None and ent.selection_present())

        def ent_has_clipboard():
            return bool(get_clipboard())

        menu_items = (
            ("Cortar", do_cut, ent_has_selection),
            ("Copiar", do_copy, ent_has_selection),
            ("Pegar", do_paste, ent_has_clipboard),
            None,
            ("Seleccionar todo", do_select_all, True),
        )

        def popup(event):
            try:
                ent = state["entry"]
                if ent.focus_get() is not ent:
                    ent.focus_set()
                # x_root/y_root son atributos del Event (coordenadas de pantalla);
                # el widget no los tiene, para eso esta winfo_rootx/winfo_rooty.
                x = getattr(event, "x_root", None)
                y = getattr(event, "y_root", None)
                if x is None or y is None:
                    x = ent.winfo_rootx() + getattr(event, "x", 0)
                    y = ent.winfo_rooty() + getattr(event, "y", 0)
                menu = DarkMenu(self, menu_items)
                menu.popup_at(x, y)
            except tk.TclError as exc:
                messagebox.showerror("Menú", f"No se pudo abrir el menú:\n{exc}")

        target.bind("<Button-3>", popup)
        target.bind("<Control-Button-1>", popup)

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _set_icon(self):
        try:
            if sys.platform == "win32":
                ico = _resource_path("icono-app.ico")
                if ico.exists():
                    self.iconbitmap(str(ico))
            else:
                png = _resource_path("icono-app.png")
                if png.exists():
                    self._icon_img = tk.PhotoImage(file=str(png))
                    self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def open_last_file(self):
        p = self.last_file
        if not p:
            messagebox.showinfo("Sin archivo", "Aún no hay ningún archivo descargado en esta sesión.")
            return
        if Path(p).exists():
            self._open_path(p)
            return
        self.status_var.set(f"⚠️ Ya no existe: {Path(p).name}")
        self._log(f"⚠️ El archivo ya no existe: {p}")
        if messagebox.askyesno(
            "Archivo no encontrado",
            f"El archivo ya no existe:\n{p}\n\n¿Abrir la carpeta de descarga?",
        ):
            folder = Path(p).parent if Path(p).parent.exists() else Path(self.dir_var.get())
            self._open_path(str(folder))

    def _open_path(self, p):
        try:
            if sys.platform == "win32":
                os.startfile(p)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", p])
            else:
                subprocess.Popen(["xdg-open", p])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir:\n{e}")

    def load_config(self):
        try:
            if CONFIG_PATH.exists():
                return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def save_config(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(
                json.dumps(
                    {
                        "download_dir": self.dir_var.get().strip(),
                        "quality": self.quality_var.get(),
                        "cookies": self.cookies_var.get(),
                        "write_thumb": bool(self.write_thumb_var.get()),
                        "overwrite": bool(self.overwrite_var.get()),
                        "subs_es": bool(self.subs_es_var.get()),
                        "subs_en": bool(self.subs_en_var.get()),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def choose_dir(self):
        initial = self.dir_var.get().strip() or str(default_dir())
        chosen = filedialog.askdirectory(title="Carpeta de descarga", initialdir=initial)
        if chosen:
            self.dir_var.set(chosen)
            self.save_config()

    def _build_command(self, url):
        preset = QUALITY_PRESETS[self.quality_var.get()]
        dest = Path(self.dir_var.get().strip() or default_dir())
        dest.mkdir(parents=True, exist_ok=True)

        cmd = [
            "yt-dlp",
            "-f", preset["format"],
            "--newline",
            "--encoding", "utf-8",
            "--print", f"after_move:{FINAL_PREFIX}%(filepath)s",
            "--no-quiet",
            "--remote-components", "ejs:github",
            "--progress-template",
            f"download:{PROGRESS_PREFIX}%(progress._percent_str)s|%(progress._eta_str)s|%(progress._speed_str)s",
        ]

        if preset["audio"]:
            cmd += ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            cmd += ["--merge-output-format", preset["container"], "--remux-video", preset["container"]]

        cmd += ["--embed-chapters", "--windows-filenames"]

        if self.write_thumb_var.get():
            cmd += ["--write-thumbnail", "--embed-thumbnail"]

        if self.overwrite_var.get():
            cmd += ["--force-overwrites"]

        subs = []
        if self.subs_es_var.get():
            subs.append("es.*")
        if self.subs_en_var.get():
            subs.append("en.*")
        if subs:
            cmd += ["--write-subs", "--sub-format", "srt/best", "--sub-langs", ",".join(subs)]

        if self.range_enabled.get():
            start = self.start_var.get().strip()
            end = self.end_var.get().strip()
            if start and end:
                cmd += ["--download-sections", f"*{start}-{end}"]

        browser = self.cookie_browsers[self.cookies_var.get()]
        if browser:
            cmd += ["--cookies-from-browser", browser]

        tpl = AUDIO_TEMPLATE if preset["audio"] else VIDEO_TEMPLATE
        cmd += ["-o", str(dest / tpl), url]
        return cmd

    def start_download(self):
        if self.downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Introduce una URL.")
            return
        if self.range_enabled.get():
            if not (self.start_var.get().strip() and self.end_var.get().strip()):
                messagebox.showerror("Error", "Indica tanto el inicio como el final del rango (formato MM:SS o HH:MM:SS).")
                return
        self.save_config()
        cmd = self._build_command(url)
        self.downloading = True
        self.download_btn.configure(state="disabled", text="⏳  Descargando...")
        self.status_var.set("Iniciando descarga...")
        self.progress.set(0)
        self.pct_var.set("0.0%")
        threading.Thread(target=self._run_worker, args=(cmd,), daemon=True).start()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self._log(f"▶ Iniciando descarga → {url}")

    def _run_worker(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
                **NO_WINDOW_KWARGS
            )
        except FileNotFoundError:
            self.ui_queue.put(("error", "yt-dlp no está instalado o no está en el PATH."))
            self.ui_queue.put(("done", False))
            return
        self.proc = proc

        last_error = None
        saw_progress = False
        saw_file = False
        sabr_hint = False
        for line in proc.stdout:
            line = line.rstrip()
            low = line.lower()
            if "sabr" in low or "missing a url" in low or "missing url" in low:
                sabr_hint = True
            if PROGRESS_PREFIX in line:
                try:
                    data = line.split(PROGRESS_PREFIX, 1)[1]
                    percent_str, eta, speed = data.split("|", 2)
                    pct = float(percent_str.strip()[:-1])
                    saw_progress = True
                    self.ui_queue.put(("progress", min(pct, 100.0), eta.strip(), speed.strip()))
                    self.ui_queue.put(("log", f"[descarga] {percent_str.strip()}  |  velocidad {speed.strip()}  |  ETA {eta.strip()}"))
                except (ValueError, IndexError):
                    pass
            elif FINAL_PREFIX in line:
                path = line.split(FINAL_PREFIX, 1)[1].strip()
                if path and path != "NA":
                    saw_file = True
                    self.ui_queue.put(("file", path))
            else:
                if line.strip():
                    self.ui_queue.put(("log", line))
            if line.startswith("ERROR"):
                last_error = line

        proc.wait()
        ok = proc.returncode == 0
        if ok:
            if not saw_file and not saw_progress:
                if sabr_hint:
                    self.ui_queue.put((
                        "status",
                        "⚠️ No se descargó nada: YouTube está forzando el protocolo SABR "
                        "en este vídeo/conexión, que la versión estable de yt-dlp todavía no soporta. "
                        "Prueba otro vídeo o actualiza yt-dlp cuando salga el soporte SABR.",
                    ))
                else:
                    self.ui_queue.put((
                        "status",
                        "⚠️ No se descargó nada nuevo. Posibles causas: (1) el archivo ya existe "
                        "en la carpeta de destino (marca 'Sobrescribir si ya existe'); (2) YouTube "
                        "está forzando el protocolo SABR en este vídeo (todavía no soportado por "
                        "yt-dlp). Revisa el Registro para más detalles.",
                    ))
            else:
                self.ui_queue.put(("status", "✅ Descarga completada."))
            if saw_progress:
                self.ui_queue.put(("progress", 100.0, "--", "--"))
        else:
            detail = f"\n\n{last_error}" if last_error else ""
            self.ui_queue.put(("error", f"Error durante la descarga.{detail}"))
        self.proc = None
        self.ui_queue.put(("done", ok))

    def _version_check_worker(self):
        local = get_local_version()
        latest = fetch_latest_version()
        deno = get_deno_version()
        self.ui_queue.put(("version_check", local, latest, deno))

    def _start_update(self):
        self.version_var.set("Actualizando yt-dlp...")
        self.update_btn.configure(state="disabled", text="Actualizando...")
        threading.Thread(target=self._do_update, daemon=True).start()

    def _do_update(self):
        try:
            out = subprocess.run(
                ["yt-dlp", "-U"], capture_output=True, text=True, timeout=180,
                **NO_WINDOW_KWARGS
            )
            tail = (out.stdout or out.stderr or "").strip().splitlines()
            msg = tail[-1] if tail else "yt-dlp actualizado."
            self.ui_queue.put(("update_result", f"✅ {msg}"))
        except Exception as e:
            self.ui_queue.put(("update_result", f"❌ No se pudo actualizar: {e}"))

    def _warn_low_quality(self, path):
        """YouTube puede no servir la calidad pedida si la sesión está en el
        experimento de streaming SABR: en ese caso sólo ofrece 360p y el
        archivo baja por debajo de lo elegido en el desplegable."""
        target = QUALITY_PRESETS.get(self.quality_var.get(), {}).get("height")
        m = re.search(r"\[(\d+)p\]", Path(path).name)
        if not target or not m:
            return
        got = int(m.group(1))
        if got >= target:
            return
        browser = self.cookies_var.get()
        messagebox.showwarning(
            "Calidad menor de la esperada",
            f"YouTube sólo ha servido {got}p en lugar de {target}p.\n\n"
            f"Causa habitual: con las cookies de «{browser}» esa sesión está en el "
            "experimento de streaming SABR, que sólo publica el formato progresivo "
            "de 360p. Ningún ajuste de la app puede evitarlo.\n\n"
            "Prueba con las cookies de otro navegador o quita las cookies: "
            "los vídeos con restricción de edad ya se resuelven sin ellas.",
        )

    def _poll_queue(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, pct, eta, speed = msg
                    self.progress.set(pct / 100.0)
                    self.pct_var.set(f"{pct:.1f}%")
                    self.eta_var.set(f"ETA: {eta}")
                    self.speed_var.set(f"{speed}")
                elif kind == "log":
                    self._log(msg[1])
                elif kind == "status":
                    self.status_var.set(msg[1])
                    self._log(msg[1])
                elif kind == "error":
                    self.status_var.set("❌ " + msg[1])
                    self._log("❌ " + msg[1])
                    messagebox.showerror("Error", msg[1])
                elif kind == "file":
                    self.last_file = msg[1]
                    self.open_btn.configure(state="normal")
                    self.status_var.set(f"📂 Archivo: {Path(msg[1]).name}")
                    self._warn_low_quality(msg[1])
                elif kind == "done":
                    self.downloading = False
                    self.download_btn.configure(state="normal", text="⬇️  Descargar")
                elif kind == "version_check":
                    _, local, latest, deno = msg
                    if deno:
                        self.deno_var.set(f"Deno: {deno}")
                    else:
                        self.deno_var.set("Deno: NO detectado")
                    if local is None:
                        self.version_var.set("⚠️ yt-dlp NO encontrado en el PATH")
                        self.update_btn.pack(side="left", padx=(10, 0))
                    elif latest is None:
                        self.version_var.set(f"yt-dlp: {local} (no se pudo verificar en GitHub)")
                    elif is_newer(latest, local):
                        self.version_var.set(f"⚠️ yt-dlp desactualizado: {local} → {latest}")
                        self.update_btn.pack(side="left", padx=(10, 0))
                    else:
                        self.version_var.set(f"✅ yt-dlp: {local}")
                elif kind == "update_result":
                    self.version_var.set(msg[1])
                    self.update_btn.pack_forget()
                    self.update_btn.configure(state="normal", text="Actualizar yt-dlp")
                    self._version_check_worker()
        except queue.Empty:
            pass
        try:
            self.after(50, self._poll_queue)
        except Exception:
            pass

    def start_update(self):
        self._start_update()


def main():
    app = YTDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
