# -*- coding: utf-8 -*-
"""
Yansıt — Android telefon ekranını ve sesini PC'ye yansıtır.
Normal ekran paylaşımı veya OBS ile canlı yayın için. Arka planda scrcpy kullanır.

https://github.com/Mehmetsndl/yansit
Gerekenler: pip install customtkinter segno
"""
import io
import json
import math
import os
import queue
import random
import re
import shutil
import string
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import wave
import webbrowser
import zipfile
import tkinter as tk

try:
    import customtkinter as ctk
except ImportError:  # ilk çalıştırmada otomatik kur
    subprocess.run([sys.executable.replace("pythonw.exe", "python.exe"), "-m", "pip", "install",
                    "--quiet", "customtkinter", "segno"])
    import customtkinter as ctk

APP_NAME = "Yansıt"
__version__ = "3.0.0"
VERSION = __version__
GITHUB_REPO = "Mehmetsndl/yansit"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SCRCPY_DIR = os.path.join(APP_DIR, "scrcpy")
CONFIG_PATH = os.path.join(APP_DIR, "ayarlar.json")
IS_WIN = os.name == "nt"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
FONT = "Segoe UI" if IS_WIN else "DejaVu Sans"

# ----------------------------------------------------------------- renkler (açık, koyu)
ACCENT = ("#6D5DFC", "#7C6CFF")
ACCENT_H = ("#5A4BE0", "#6A5AF0")
GREEN = ("#16A34A", "#22C55E")
GREEN_H = ("#15803D", "#16A34A")
RED = ("#DC2626", "#EF4444")
RED_H = ("#B91C1C", "#DC2626")
AMBER = ("#B45309", "#FBBF24")
BG = ("#EEF0F6", "#0E1016")
SIDEBAR = ("#E4E7F0", "#13151D")
CARD = ("#FFFFFF", "#1A1D27")
CARD2 = ("#F4F5FA", "#232736")
BORDER = ("#DADDE8", "#2B2F3F")
TEXT = ("#151823", "#E8EAF2")
MUTED = ("#6B7080", "#8A90A3")
PILL_OK = ("#DCFCE7", "#13301F")
PILL_READY = ("#EDE9FE", "#262046")
PILL_WAIT = ("#FEF3C7", "#382C10")

PRESETS = {
    "Normal paylaşım": {"size": "1920", "bitrate": 8, "fps": "60", "codec": "h264", "no_control": False},
    "Oyun yayını · Kablolu": {"size": "1920", "bitrate": 16, "fps": "60", "codec": "h264", "no_control": True},
    "Oyun yayını · Kablosuz": {"size": "1600", "bitrate": 10, "fps": "60", "codec": "h264", "no_control": True},
    "Zayıf Wi-Fi": {"size": "1280", "bitrate": 6, "fps": "60", "codec": "h264", "no_control": None},
    "Özel": None,
}

DEFAULTS = {
    "cfg_version": 3,
    "theme": "Koyu", "sfx": True,
    "preset": "Normal paylaşım",
    "size": "1920", "bitrate": 8, "fps": "60", "codec": "h264",
    "audio": True, "audio_dup": False,
    "stay_awake": True, "on_top": False, "borderless": False,
    "no_control": False, "screen_off": False, "auto_reconnect": True,
    "window_title": "Yansit",
    "wifi_addr": "", "pair_addr": "", "device": "",
    "known": {},
}


# ----------------------------------------------------------------- yardımcılar
def find_tool(name):
    exe = name + (".exe" if IS_WIN else "")
    if os.path.isdir(SCRCPY_DIR):
        for root, _d, files in os.walk(SCRCPY_DIR):
            if exe in files:
                return os.path.join(root, exe)
    return shutil.which(exe)


def tool_env():
    env = os.environ.copy()
    env["ADB_MDNS_OPENSCREEN"] = "1"
    return env


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=tool_env(),
                           creationflags=NO_WINDOW, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "Zaman aşımı"
    except Exception as e:  # noqa
        return -1, str(e)


MDNS_RE = re.compile(r"^\s*(\S+)\s+(_adb[-\w]*\._tcp)\.?\s+(\d+\.\d+\.\d+\.\d+:\d+)")


def mdns_services(adb):
    rc, out = run([adb, "mdns", "services"], 10)
    return [m.groups() for m in map(MDNS_RE.match, out.splitlines()) if m]


def load_cfg():
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            old = json.load(f)
        if old.get("cfg_version", 1) < 3:   # eski sürümden geçiş
            old["audio_dup"] = False
            old.pop("preset", None)
            try:
                old["bitrate"] = int(old.get("bitrate", 8))
            except ValueError:
                old["bitrate"] = 8
            old["cfg_version"] = 3
        cfg.update(old)
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_segno():
    try:
        import segno  # noqa
        return segno
    except ImportError:
        if getattr(sys, "frozen", False):
            return None
        run([sys.executable.replace("pythonw.exe", "python.exe"), "-m", "pip", "install", "--quiet", "segno"], 120)
        try:
            import segno  # noqa
            return segno
        except ImportError:
            return None


def is_dark():
    return ctk.get_appearance_mode() == "Dark"


def mc(c):
    """Tema renginden o anki modun rengini seç."""
    return c[1] if isinstance(c, (tuple, list)) and is_dark() else (c[0] if isinstance(c, (tuple, list)) else c)


def lerp_color(a, b, t):
    a, b = mc(a).lstrip("#"), mc(b).lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{int(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


# ----------------------------------------------------------------- mekanik ses efektleri
class Sfx:
    """Ses dosyası gerektirmez: mekanik klik/röle seslerini program kendisi sentezler."""
    SR = 22050

    def __init__(self):
        self.enabled = True
        self.files = {}
        self.dir = os.path.join(tempfile.gettempdir(), "yansit_sfx")
        threading.Thread(target=self._build_all, daemon=True).start()

    # -- sentez yardımcıları
    def _buf(self, sec):
        return [0.0] * int(sec * self.SR)

    def _click(self, b, t0, amp, freq, decay=420, noise=0.65, dur=0.025):
        s0 = int(t0 * self.SR)
        for i in range(int(dur * self.SR)):
            if s0 + i >= len(b):
                break
            t = i / self.SR
            e = math.exp(-t * decay)
            v = noise * random.uniform(-1, 1) * math.exp(-t * decay * 1.6) + (1 - noise) * math.sin(2 * math.pi * freq * t)
            b[s0 + i] += amp * e * v

    def _thump(self, b, t0, amp, f0, dur=0.06, decay=55, drop=0.5):
        s0 = int(t0 * self.SR)
        ph = 0.0
        for i in range(int(dur * self.SR)):
            if s0 + i >= len(b):
                break
            t = i / self.SR
            f = f0 * (1 - drop * t / dur)
            ph += 2 * math.pi * f / self.SR
            b[s0 + i] += amp * math.exp(-t * decay) * math.sin(ph)

    def _ring(self, b, t0, amp, freq, dur=0.25, decay=18):
        s0 = int(t0 * self.SR)
        for i in range(int(dur * self.SR)):
            if s0 + i >= len(b):
                break
            t = i / self.SR
            b[s0 + i] += amp * math.exp(-t * decay) * (math.sin(2 * math.pi * freq * t) + .35 * math.sin(2 * math.pi * freq * 2.76 * t))

    def _whir(self, b, t0, amp, f0, f1, dur):
        s0 = int(t0 * self.SR)
        ph = 0.0
        n = int(dur * self.SR)
        for i in range(n):
            if s0 + i >= len(b):
                break
            k = i / n
            f = f0 + (f1 - f0) * k
            ph += f / self.SR
            saw = 2 * (ph % 1) - 1
            env = math.sin(math.pi * k) ** 0.7
            b[s0 + i] += amp * env * (saw * .6 + .4 * random.uniform(-1, 1))

    def _make(self, kind):
        b = self._buf(0.45)
        if kind == "click":        # mekanik klavye tuşu: bas + bırak
            self._click(b, 0, .55, 3400, 450)
            self._thump(b, 0, .30, 190, .04, 70)
            self._click(b, .05, .28, 2800, 520, dur=.018)
        elif kind == "nav":        # yumuşak tık
            self._click(b, 0, .40, 4200, 600, .8, .015)
            self._thump(b, 0, .18, 240, .03, 90)
        elif kind == "toggle":     # ağır anahtar
            self._thump(b, 0, .50, 130, .07, 45)
            self._click(b, 0, .45, 2100, 380)
            self._click(b, .028, .30, 3000, 500, dur=.015)
        elif kind == "start":      # röle + servo dönüşü
            self._click(b, 0, .60, 1500, 300, .55, .04)
            self._thump(b, 0, .55, 95, .09, 35)
            self._ring(b, .005, .07, 4200, .2, 30)
            self._whir(b, .06, .10, 180, 620, .28)
            self._click(b, .34, .35, 2600, 500, dur=.02)
        elif kind == "stop":       # servo iniş + röle bırakma
            self._whir(b, 0, .10, 620, 160, .24)
            self._click(b, .25, .55, 1400, 320, .55, .04)
            self._thump(b, .25, .50, 85, .09, 35)
        elif kind == "connect":    # cırcır (ratchet) + kilit
            for k in range(3):
                self._click(b, k * .045, .38 + k * .05, 2400 + k * 500, 520, dur=.018)
            self._thump(b, .15, .45, 120, .07, 40)
            self._click(b, .15, .45, 1800, 350)
        elif kind == "success":    # kilit + metal zil
            self._click(b, 0, .45, 2200, 400)
            self._thump(b, 0, .35, 140, .06, 50)
            self._ring(b, .04, .18, 1318, .38, 9)
            self._ring(b, .10, .14, 1976, .32, 10)
        elif kind == "error":      # iki boğuk vuruş + vızıltı
            self._thump(b, 0, .55, 95, .08, 30)
            self._thump(b, .11, .55, 80, .08, 30)
            s0 = int(.02 * self.SR)
            for i in range(int(.16 * self.SR)):
                t = i / self.SR
                b[s0 + i] += .12 * (1 if math.sin(2 * math.pi * 140 * t) > 0 else -1) * math.exp(-t * 12)
        elif kind == "tick":       # yeni cihaz bulundu
            self._click(b, 0, .30, 5200, 700, .5, .012)
            self._ring(b, .005, .06, 2637, .12, 30)
        # normalize + sondaki sessizliği kes
        peak = max(1e-6, max(abs(x) for x in b))
        b = [x / peak * .75 for x in b]
        end = len(b)
        while end > 100 and abs(b[end - 1]) < 1e-3:
            end -= 1
        b = b[:end]
        for i in range(min(150, len(b))):
            b[-1 - i] *= i / 150
        return b

    def _build_all(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            for kind in ("click", "nav", "toggle", "start", "stop", "connect", "success", "error", "tick"):
                path = os.path.join(self.dir, f"{kind}.wav")
                samples = self._make(kind)
                with wave.open(path, "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(self.SR)
                    w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))
                self.files[kind] = path
        except Exception:
            pass

    def play(self, kind):
        if not self.enabled or kind not in self.files:
            return
        path = self.files[kind]
        try:
            if IS_WIN:
                import winsound
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            else:
                player = shutil.which("paplay") or shutil.which("aplay") or shutil.which("afplay")
                if player:
                    subprocess.Popen([player, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


# ----------------------------------------------------------------- cihaz kartı
class DeviceCard(ctk.CTkFrame):
    def __init__(self, master, app, key):
        super().__init__(master, fg_color=CARD2, corner_radius=12, border_width=1, border_color=BORDER)
        self.app, self.key = app, key
        self.columnconfigure(1, weight=1)
        self.icon = ctk.CTkLabel(self, text="📱", width=44, height=44, corner_radius=10, fg_color=CARD,
                                 font=ctk.CTkFont(FONT, 20))
        self.icon.grid(row=0, column=0, rowspan=2, padx=(12, 10), pady=10)
        self.name = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(FONT, 14, "bold"), text_color=TEXT)
        self.name.grid(row=0, column=1, sticky="sw", pady=(10, 0))
        self.addr = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(FONT, 12), text_color=MUTED)
        self.addr.grid(row=1, column=1, sticky="nw", pady=(0, 10))
        self.pill = ctk.CTkLabel(self, text="", corner_radius=10, height=24, font=ctk.CTkFont(FONT, 11, "bold"))
        self.pill.grid(row=0, column=2, rowspan=2, padx=8)
        self.btn = ctk.CTkButton(self, text="Bağlan", width=110, height=34, corner_radius=10,
                                 font=ctk.CTkFont(FONT, 12, "bold"), command=self._action)
        self.btn.grid(row=0, column=3, rowspan=2, padx=(4, 12))
        self.state = None
        for w in (self, self.icon, self.name, self.addr, self.pill):
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))
            w.bind("<Double-1>", lambda e: self._action())

    def update_info(self, label, addr, state):
        self.name.configure(text=label)
        self.addr.configure(text=addr)
        if state == self.state:
            return
        self.state = state
        if state == "connected":
            self.pill.configure(text="  ● Bağlı  ", fg_color=PILL_OK, text_color=GREEN)
            self.btn.configure(text="Seç", fg_color=CARD, hover_color=BORDER, text_color=TEXT)
        elif state == "ready":
            self.pill.configure(text="  Hazır  ", fg_color=PILL_READY, text_color=ACCENT)
            self.btn.configure(text="Bağlan", fg_color=ACCENT, hover_color=ACCENT_H, text_color="#ffffff")
        else:
            self.pill.configure(text="  Eşleştirme açık  ", fg_color=PILL_WAIT, text_color=AMBER)
            self.btn.configure(text="Kodla eşle", fg_color=CARD, hover_color=BORDER, text_color=TEXT)

    def appear(self):
        self.app.animate(380, lambda t: self.configure(fg_color=lerp_color(CARD, CARD2, t),
                                                       border_color=lerp_color(ACCENT, BORDER, t)),
                         done=lambda: self.configure(fg_color=CARD2, border_color=BORDER))

    def _hover(self, on):
        a, b = (BORDER, ACCENT) if on else (ACCENT, BORDER)
        self.app.animate(140, lambda t: self.winfo_exists() and self.configure(border_color=lerp_color(a, b, t)))

    def _action(self):
        self.app.sfx.play("click")
        self.app.card_action(self.key)


# ----------------------------------------------------------------- QR penceresi
class QrPairWindow(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app, fg_color=BG)
        self.app = app
        self.title("QR ile eşleştir")
        self.geometry("400x590")
        self.resizable(False, False)
        self.transient(app)
        self.done = False
        self.angle = 0
        self.name = "tep-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        self.pwd = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        data = f"WIFI:T:ADB;S:{self.name};P:{self.pwd};;"

        ctk.CTkLabel(self, text="QR ile eşleştir", font=ctk.CTkFont(FONT, 20, "bold"),
                     text_color=TEXT).pack(pady=(20, 2))
        ctk.CTkLabel(self, text="Telefonda: Geliştirici seçenekleri → Kablosuz hata ayıklama\n"
                                "→ \"Cihazı QR koduyla eşle\" → bu kodu okutun",
                     font=ctk.CTkFont(FONT, 12), text_color=MUTED, justify="center").pack(pady=(0, 14))
        box = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=18)
        box.pack()
        self.canvas = tk.Canvas(box, width=272, height=272, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(padx=14, pady=14)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(16, 4))
        self.spin = tk.Canvas(row, width=26, height=26, highlightthickness=0, bg=mc(BG))
        self.spin.pack(side="left", padx=(0, 8))
        self.status = ctk.CTkLabel(row, text="QR hazırlanıyor...", font=ctk.CTkFont(FONT, 13, "bold"),
                                   text_color=ACCENT)
        self.status.pack(side="left")
        ctk.CTkLabel(self, text="Telefon ve bilgisayar aynı Wi-Fi ağında olmalı.",
                     font=ctk.CTkFont(FONT, 11), text_color=MUTED).pack()
        ctk.CTkButton(self, text="Kapat", width=140, height=36, corner_radius=10, fg_color=CARD2,
                      hover_color=BORDER, text_color=TEXT, command=self.close).pack(pady=14)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(150, self.lift)
        self.after(150, self.focus_force)
        self._spin()
        app.bg(self._prepare, data)

    def _spin(self):
        if self.done:
            return
        try:
            self.spin.configure(bg=mc(BG))
            self.spin.delete("all")
            self.spin.create_arc(3, 3, 23, 23, start=self.angle, extent=260, style="arc",
                                 outline=mc(ACCENT), width=3)
            self.angle = (self.angle - 12) % 360
            self.after(30, self._spin)
        except tk.TclError:
            pass

    def set_status(self, t, color=ACCENT):
        def upd():
            try:
                self.status.configure(text=t, text_color=color)
            except tk.TclError:
                pass
        self.app.after(0, upd)

    def _finish(self, ok):
        def upd():
            try:
                self.spin.delete("all")
                self.spin.create_text(13, 13, text="✔" if ok else "✖", fill=mc(GREEN if ok else RED),
                                      font=(FONT, 15, "bold"))
            except tk.TclError:
                pass
        self.app.after(0, upd)

    def _prepare(self, data):
        segno = get_segno()
        if not segno:
            self.done = True
            self._finish(False)
            self.set_status("QR kütüphanesi yüklenemedi.", RED)
            return
        rows = [list(r) for r in segno.make(data, error="l").matrix_iter(scale=1, border=2)]
        self.app.after(0, self._draw, rows)
        self._poll()

    def _draw(self, rows):
        try:
            n = len(rows)
            cell = 272 // n
            off = (272 - cell * n) // 2
            for y, row in enumerate(rows):
                for x, v in enumerate(row):
                    if v:
                        self.canvas.create_rectangle(off + x * cell, off + y * cell, off + (x + 1) * cell,
                                                     off + (y + 1) * cell, fill="#000000", outline="")
            self.set_status("Telefonla okutmanız bekleniyor...")
        except tk.TclError:
            pass

    def _poll(self):
        adb = self.app.adb()
        if not adb:
            return
        run([adb, "start-server"], 20)
        deadline = time.time() + 180
        while not self.done and time.time() < deadline:
            for name, typ, addr in mdns_services(adb):
                if typ.startswith("_adb-tls-pairing") and name == self.name:
                    self.set_status("Telefon bulundu, eşleştiriliyor...")
                    rc, out = run([adb, "pair", addr, self.pwd], 30)
                    self.app.log(out)
                    if "Successfully" not in out:
                        self.done = True
                        self._finish(False)
                        self.set_status("Eşleştirme başarısız, tekrar deneyin.", RED)
                        self.app.after(0, lambda: self.app.sfx.play("error"))
                        return
                    self.set_status("Eşleşti! Bağlanılıyor...")
                    self._connect_after_pair(adb, addr.split(":")[0])
                    return
            time.sleep(1)
        if not self.done:
            self.done = True
            self._finish(False)
            self.set_status("Süre doldu. Tekrar açın.", RED)

    def _connect_after_pair(self, adb, ip):
        for _ in range(15):
            for name, typ, addr in mdns_services(adb):
                if typ.startswith("_adb-tls-connect") and addr.startswith(ip + ":"):
                    self.app.connect_addr(addr, name, sync=True, quiet=True)
                    self.done = True
                    self._finish(True)
                    self.set_status("Bağlandı!", GREEN)
                    self.app.after(0, lambda: (self.app.sfx.play("success"),
                                               self.app.toast("Telefon eşleşti ve bağlandı", "ok")))
                    self.app.after(1600, self.close)
                    return
            time.sleep(1)
        self.done = True
        self._finish(True)
        self.set_status("Eşleşti — listeden bağlanın.", AMBER)

    def close(self):
        self.done = True
        try:
            self.destroy()
        except tk.TclError:
            pass


# ----------------------------------------------------------------- ana uygulama
class App(ctk.CTk):
    def __init__(self):
        self.cfg = load_cfg()
        ctk.set_appearance_mode("dark" if self.cfg["theme"] == "Koyu" else "light")
        super().__init__(fg_color=BG)
        self.title(APP_NAME)
        self.geometry("1060x780")
        self.minsize(1000, 740)
        self.sfx = Sfx()
        self.sfx.enabled = self.cfg["sfx"]
        self.log_q = queue.Queue()
        self.proc = None
        self.running = False
        self.user_stopped = True
        self._restart = False
        self.connected = []
        self.cards = {}
        self.card_meta = {}
        self.page = None
        self.started_at = 0
        self._applying = False
        self._radar_t = 0.0
        self._toast = None

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_vars()
        self._build_sidebar()
        self._build_main()
        self.show_page("conn", animate=False)
        self.after(100, self._drain_log)
        self.after(60, self._tick)
        self.after(300, self.check_scrcpy)
        self.after(2500, lambda: self.bg(self._check_update))
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ================= animasyon motoru
    def animate(self, ms, fn, done=None, ease=ease_out):
        start = time.perf_counter()

        def step():
            t = min(1.0, (time.perf_counter() - start) * 1000 / ms)
            try:
                fn(ease(t))
            except tk.TclError:
                return
            if t < 1:
                self.after(15, step)
            elif done:
                try:
                    done()
                except tk.TclError:
                    pass
        step()

    # ================= bileşen fabrikaları
    def F(self, size=13, weight="normal"):
        return ctk.CTkFont(FONT, size, weight)

    def card(self, parent, title, subtitle=None):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        head = ctk.CTkFrame(f, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(head, text=title, font=self.F(15, "bold"), text_color=TEXT).pack(side="left")
        if subtitle:
            ctk.CTkLabel(f, text=subtitle, font=self.F(12), text_color=MUTED, anchor="w",
                         justify="left").pack(fill="x", padx=18)
        body = ctk.CTkFrame(f, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(10, 16))
        f.head = head
        return f, body

    def button(self, parent, text, cmd, kind="secondary", sound="click", **kw):
        colors = {
            "primary": dict(fg_color=ACCENT, hover_color=ACCENT_H, text_color="#ffffff"),
            "secondary": dict(fg_color=CARD2, hover_color=BORDER, text_color=TEXT, border_width=1, border_color=BORDER),
            "danger": dict(fg_color=CARD2, hover_color=PILL_WAIT, text_color=RED, border_width=1, border_color=BORDER),
        }[kind]
        kw.setdefault("height", 38)
        kw.setdefault("corner_radius", 10)
        kw.setdefault("font", self.F(13, "bold"))

        def wrapped():
            self.sfx.play(sound)
            cmd()
        return ctk.CTkButton(parent, text=text, command=wrapped, **colors, **kw)

    def switch(self, parent, text, var, cmd=None):
        def wrapped():
            self.sfx.play("toggle")
            if cmd:
                cmd()
        return ctk.CTkSwitch(parent, text=text, variable=var, command=wrapped, progress_color=ACCENT,
                             button_color=("#ffffff", "#E8EAF2"), button_hover_color=("#f0f0f0", "#ffffff"),
                             fg_color=BORDER, text_color=TEXT, font=self.F(13), switch_width=42, switch_height=22)

    def segmented(self, parent, values, var, cmd=None):
        def wrapped(v):
            self.sfx.play("nav")
            if cmd:
                cmd(v)
        return ctk.CTkSegmentedButton(parent, values=values, variable=var, command=wrapped, height=34,
                                      font=self.F(12, "bold"), corner_radius=10, fg_color=CARD2,
                                      selected_color=ACCENT, selected_hover_color=ACCENT_H,
                                      unselected_color=CARD2, unselected_hover_color=BORDER,
                                      text_color=(TEXT[0], TEXT[1]))

    def entry(self, parent, placeholder):
        return ctk.CTkEntry(parent, placeholder_text=placeholder, height=38, corner_radius=10,
                            fg_color=CARD2, border_color=BORDER, text_color=TEXT, font=self.F(13))

    # ================= değişkenler
    def _build_vars(self):
        c = self.cfg
        self.v_theme = tk.StringVar(value=c["theme"])
        self.v_sfx = tk.BooleanVar(value=c["sfx"])
        self.v_preset = tk.StringVar(value=c["preset"] if c["preset"] in PRESETS else "Özel")
        self.v_size = tk.StringVar(value=c["size"])
        self.v_bitrate = tk.IntVar(value=int(c["bitrate"]))
        self.v_fps = tk.StringVar(value=c["fps"])
        self.v_codec = tk.StringVar(value=c["codec"])
        self.v_audio = tk.BooleanVar(value=c["audio"])
        self.v_dup = tk.BooleanVar(value=c["audio_dup"])
        self.v_awake = tk.BooleanVar(value=c["stay_awake"])
        self.v_top = tk.BooleanVar(value=c["on_top"])
        self.v_border = tk.BooleanVar(value=c["borderless"])
        self.v_noctl = tk.BooleanVar(value=c["no_control"])
        self.v_screen_off = tk.BooleanVar(value=c["screen_off"])
        self.v_reconn = tk.BooleanVar(value=c["auto_reconnect"])
        self.v_device = tk.StringVar(value="Cihaz yok")

    # ================= kenar çubuğu
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0, width=230)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        sb.pack_propagate(False)
        self.sidebar = sb

        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.pack(fill="x", padx=18, pady=(22, 26))
        ctk.CTkLabel(logo, text="◩", width=42, height=42, corner_radius=12, fg_color=ACCENT,
                     font=self.F(20)).pack(side="left")
        t = ctk.CTkFrame(logo, fg_color="transparent")
        t.pack(side="left", padx=10)
        ctk.CTkLabel(t, text=APP_NAME, font=self.F(16, "bold"), text_color=TEXT, anchor="w").pack(anchor="w")
        self.lbl_ver = ctk.CTkLabel(t, text=f"Sürüm {VERSION}", font=self.F(11), text_color=MUTED,
                                    anchor="w", cursor="hand2")
        self.lbl_ver.pack(anchor="w")
        self.lbl_ver.bind("<Button-1>", lambda e: webbrowser.open(f"https://github.com/{GITHUB_REPO}"))

        self.nav = ctk.CTkFrame(sb, fg_color="transparent")
        self.nav.pack(fill="x", padx=12)
        self.nav_btns = {}
        for key, txt in (("conn", "📡   Bağlantı"), ("settings", "⚙   Ayarlar"), ("log", "📜   Kayıt")):
            b = ctk.CTkButton(self.nav, text=txt, anchor="w", height=42, corner_radius=10,
                              fg_color="transparent", hover_color=CARD2, text_color=TEXT,
                              font=self.F(14, "bold"), command=lambda k=key: (self.sfx.play("nav"), self.show_page(k)))
            b.pack(fill="x", pady=3)
            self.nav_btns[key] = b
        self.indicator = ctk.CTkFrame(self.nav, fg_color=ACCENT, width=4, height=24, corner_radius=2)

        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=18, pady=18)
        # güncelleme bildirimi (yeni sürüm varsa görünür)
        self.upd_box = ctk.CTkFrame(sb, fg_color=PILL_READY, corner_radius=12)
        self.upd_lbl = ctk.CTkLabel(self.upd_box, text="", font=self.F(12, "bold"), text_color=ACCENT,
                                    justify="left", anchor="w")
        self.upd_lbl.pack(fill="x", padx=12, pady=(10, 4))
        self.button(self.upd_box, "İndir", lambda: webbrowser.open(RELEASES_URL), "primary",
                    height=32, font=self.F(12, "bold")).pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(bottom, text="TEMA", font=self.F(11, "bold"), text_color=MUTED).pack(anchor="w")
        self.segmented(bottom, ["Koyu", "Açık"], self.v_theme, self.set_theme).pack(fill="x", pady=(4, 12))
        self.switch(bottom, "Ses efektleri", self.v_sfx, self._sfx_changed).pack(anchor="w", pady=(0, 14))

        ctk.CTkFrame(bottom, height=1, fg_color=BORDER).pack(fill="x", pady=(0, 12))
        self.lbl_scrcpy = ctk.CTkLabel(bottom, text="Kontrol ediliyor...", font=self.F(12), text_color=MUTED,
                                       anchor="w", justify="left", wraplength=190)
        self.lbl_scrcpy.pack(anchor="w")
        self.dl_bar = ctk.CTkProgressBar(bottom, height=6, progress_color=ACCENT, fg_color=CARD2)
        self.dl_bar.set(0)
        self.btn_dl = self.button(bottom, "scrcpy indir / güncelle", self.download_scrcpy, height=34,
                                  font=self.F(12, "bold"))
        self.btn_dl.pack(fill="x", pady=(8, 0))

    def _move_indicator(self, key, animate=True):
        btn = self.nav_btns[key]
        self.update_idletasks()
        y_to = btn.winfo_y() + (btn.winfo_height() - 24) // 2
        y_from = getattr(self, "_ind_y", y_to)
        self._ind_y = y_to
        if not animate:
            self.indicator.place(x=0, y=y_to)
            return
        self.animate(260, lambda t: self.indicator.place(x=0, y=int(y_from + (y_to - y_from) * t)),
                     ease=ease_in_out)

    # ================= ana alan
    def _build_main(self):
        m = ctk.CTkFrame(self, fg_color="transparent")
        m.grid(row=0, column=1, sticky="nsew", padx=22, pady=(18, 18))
        m.columnconfigure(0, weight=1)
        m.rowconfigure(1, weight=1)

        head = ctk.CTkFrame(m, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        head.columnconfigure(0, weight=1)
        self.h_title = ctk.CTkLabel(head, text="", font=self.F(24, "bold"), text_color=TEXT, anchor="w")
        self.h_title.grid(row=0, column=0, sticky="w")
        self.h_sub = ctk.CTkLabel(head, text="", font=self.F(13), text_color=MUTED, anchor="w")
        self.h_sub.grid(row=1, column=0, sticky="w")

        self.container = ctk.CTkFrame(m, fg_color="transparent")
        self.container.grid(row=1, column=0, sticky="nsew")
        self.pages = {
            "conn": self._build_conn_page(self.container),
            "settings": self._build_settings_page(self.container),
            "log": self._build_log_page(self.container),
        }
        self._build_actionbar(m)

    PAGE_INFO = {
        "conn": ("Bağlantı", "Telefonunu kablosuz ya da USB ile bağla"),
        "settings": ("Ayarlar", "Görüntü, ses ve pencere tercihleri"),
        "log": ("Kayıt", "Ayrıntılı işlem kaydı — sorun olursa buradakini gönder"),
    }

    def show_page(self, key, animate=True):
        if key == self.page:
            return
        old = self.pages.get(self.page)
        new = self.pages[key]
        self.page = key
        for k, b in self.nav_btns.items():
            b.configure(fg_color=CARD2 if k == key else "transparent", text_color=ACCENT if k == key else TEXT)
        self._move_indicator(key, animate)
        title, sub = self.PAGE_INFO[key]
        self.h_title.configure(text=title)
        self.h_sub.configure(text=sub)
        if old is not None:
            old.place_forget()
        if not animate:
            new.place(relx=0, rely=0, relwidth=1, relheight=1)
            return
        new.place(relx=0.05, rely=0, relwidth=1, relheight=1)
        self.animate(260, lambda t: new.place(relx=0.05 * (1 - t), rely=0, relwidth=1, relheight=1))

    # ---------- Bağlantı sayfası
    def _build_conn_page(self, parent):
        p = ctk.CTkFrame(parent, fg_color="transparent")
        p.columnconfigure((0, 1), weight=1, uniform="c")
        p.rowconfigure(0, weight=1)

        f, body = self.card(p, "Ağdaki telefonlar", "Kablosuz hata ayıklaması açık olan telefonlar kendiliğinden listelenir")
        f.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.lbl_scan = ctk.CTkLabel(f.head, text="", font=self.F(12), text_color=MUTED)
        self.lbl_scan.pack(side="right")
        self.scan_bar = ctk.CTkProgressBar(body, mode="indeterminate", height=3, progress_color=ACCENT,
                                           fg_color=CARD2, indeterminate_speed=0.6)
        self.scan_bar.pack(fill="x", pady=(0, 10))
        self.scan_bar.start()

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(side="bottom", fill="x", pady=(12, 0))   # butonlar her zaman görünür
        holder = ctk.CTkFrame(body, fg_color="transparent")
        holder.pack(fill="both", expand=True)
        self.dev_list = ctk.CTkScrollableFrame(holder, fg_color="transparent", scrollbar_button_color=BORDER, height=110)
        self.empty = ctk.CTkFrame(holder, fg_color="transparent")
        self.radar = tk.Canvas(self.empty, width=220, height=120, highlightthickness=0, bg=mc(CARD))
        self.radar.pack(expand=True)
        ctk.CTkLabel(self.empty, text="Ağ taranıyor...  Telefonda Kablosuz hata ayıklamayı açın",
                     font=self.F(13, "bold"), text_color=MUTED).pack(pady=(2, 0))
        self.empty.pack(fill="both", expand=True)

        row.columnconfigure((0, 1), weight=1, uniform="b")
        self.button(row, "📷   QR ile yeni telefon eşleştir", self.open_qr, "primary", height=42).grid(
            row=0, column=0, sticky="ew", padx=(0, 6))
        self.button(row, "Bağlantıları kes", self.disconnect_all, "danger", height=42).grid(
            row=0, column=1, sticky="ew", padx=(6, 0))

        f, body = self.card(p, "Kablolu (USB)", "Kabloyu tak, telefonda izin ver, alttan cihazı seç")
        f.grid(row=1, column=0, sticky="nsew", padx=(0, 7), pady=(14, 0))
        ctk.CTkLabel(body, text="Kablosuz hata ayıklaması olmayan eski telefonlarda:\nönce USB ile bağla, sonra tek tıkla kablosuza geç.",
                     font=self.F(12), text_color=MUTED, justify="left", anchor="w").pack(fill="x")
        self.button(body, "USB'den kablosuza geçir", self.usb_to_wifi).pack(fill="x", side="bottom", pady=(10, 0))

        f, body = self.card(p, "Elle bağlan", "Liste çalışmazsa telefondaki bilgileri gir")
        f.grid(row=1, column=1, sticky="nsew", padx=(7, 0), pady=(14, 0))
        body.columnconfigure((0, 1), weight=1, uniform="e")
        self.e_pair = self.entry(body, "Eşleştirme IP:Port")
        self.e_code = self.entry(body, "6 haneli kod")
        self.e_wifi = self.entry(body, "Bağlantı IP:Port")
        if self.cfg["pair_addr"]:
            self.e_pair.insert(0, self.cfg["pair_addr"])
        if self.cfg["wifi_addr"]:
            self.e_wifi.insert(0, self.cfg["wifi_addr"])
        self.e_pair.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.e_code.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.button(body, "Eşleştir", self.pair_code).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.e_wifi.grid(row=2, column=0, sticky="ew", padx=(0, 5), pady=(8, 0))
        self.button(body, "Bağlan", lambda: self.connect_addr(self.e_wifi.get().strip()), "primary").grid(
            row=2, column=1, sticky="ew", padx=(5, 0), pady=(8, 0))
        return p

    # ---------- Ayarlar sayfası
    def _build_settings_page(self, parent):
        p = ctk.CTkScrollableFrame(parent, fg_color="transparent", scrollbar_button_color=BORDER)
        p.columnconfigure((0, 1), weight=1, uniform="s")

        f, body = self.card(p, "Görüntü")
        f.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 7))
        ctk.CTkLabel(body, text="Hazır ayar", font=self.F(12, "bold"), text_color=MUTED, anchor="w").pack(fill="x")
        ctk.CTkOptionMenu(body, values=list(PRESETS), variable=self.v_preset, command=self.apply_preset,
                          height=38, corner_radius=10, fg_color=CARD2, button_color=ACCENT,
                          button_hover_color=ACCENT_H, text_color=TEXT, font=self.F(13),
                          dropdown_font=self.F(13)).pack(fill="x", pady=(4, 14))
        for lbl, var, vals in (("Çözünürlük (uzun kenar)", self.v_size, ["1024", "1280", "1600", "1920", "2400"]),
                               ("FPS", self.v_fps, ["30", "60", "90", "120"]),
                               ("Kodek", self.v_codec, ["h264", "h265"])):
            ctk.CTkLabel(body, text=lbl, font=self.F(12, "bold"), text_color=MUTED, anchor="w").pack(fill="x")
            self.segmented(body, vals, var, lambda v: self._custom()).pack(fill="x", pady=(4, 14))
        r = ctk.CTkFrame(body, fg_color="transparent")
        r.pack(fill="x")
        ctk.CTkLabel(r, text="Bit hızı", font=self.F(12, "bold"), text_color=MUTED).pack(side="left")
        self.lbl_br = ctk.CTkLabel(r, text="", font=self.F(12, "bold"), text_color=ACCENT)
        self.lbl_br.pack(side="right")
        ctk.CTkSlider(body, from_=2, to=24, number_of_steps=22, variable=self.v_bitrate, height=18,
                      progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_H, fg_color=CARD2,
                      command=lambda v: (self._update_br(), self._custom())).pack(fill="x", pady=(6, 0))
        self._update_br()

        f, body = self.card(p, "Ses", "Varsayılan: tüm ses PC'ye gelir, telefon susar")
        f.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.switch(body, "Telefon sesini PC'ye aktar", self.v_audio).pack(anchor="w")
        self.switch(body, "Telefonda da çalsın (Android 13+)", self.v_dup,
                    lambda: self._live_change("Ses modu değişti")).pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(body, text="⚠ Bu modda bazı oyun/uygulamalar sesini engelleyebilir;\n"
                                "ses gelmezse bu seçeneği kapatın.",
                     font=self.F(11), text_color=AMBER, justify="left", anchor="w").pack(fill="x", pady=(6, 0))

        f, body = self.card(p, "Pencere")
        f.grid(row=1, column=1, sticky="nsew", padx=(7, 0), pady=(14, 0))
        ctk.CTkLabel(body, text="Pencere adı (OBS'de bu seçilir)", font=self.F(12, "bold"), text_color=MUTED,
                     anchor="w").pack(fill="x")
        self.e_title = self.entry(body, "Yansit")
        self.e_title.insert(0, self.cfg["window_title"])
        self.e_title.pack(fill="x", pady=(4, 12))
        self.switch(body, "Hep üstte", self.v_top).pack(anchor="w")
        self.switch(body, "Çerçevesiz", self.v_border).pack(anchor="w", pady=(10, 0))

        f, body = self.card(p, "Davranış")
        f.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        body.columnconfigure((0, 1), weight=1, uniform="d")
        for i, (t, v) in enumerate((("PC'den kontrolü kapat (sadece izle)", self.v_noctl),
                                    ("Telefon ekranını kapat (görüntü PC'de)", self.v_screen_off),
                                    ("Telefon uykuya geçmesin", self.v_awake),
                                    ("Koparsa otomatik yeniden bağlan", self.v_reconn))):
            self.switch(body, t, v).grid(row=i // 2, column=i % 2, sticky="w", pady=5)

        f, body = self.card(p, "PC'den kontrol kısayolları")
        f.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        body.columnconfigure((0, 1), weight=1, uniform="k")
        keys = [("Sağ tık", "Geri"), ("Orta tık", "Ana ekran"), ("Alt+S", "Son uygulamalar"),
                ("Alt+F", "Tam ekran"), ("Alt+R", "Döndür"), ("Alt+O", "Telefon ekranı kapat/aç"),
                ("Ctrl+C / V", "Pano paylaşımı"), ("Sürükle-bırak", "Dosyayı telefona gönder")]
        for i, (k, d) in enumerate(keys):
            c = ctk.CTkFrame(body, fg_color="transparent")
            c.grid(row=i // 2, column=i % 2, sticky="w", pady=3)
            ctk.CTkLabel(c, text=k, width=104, height=26, corner_radius=8, fg_color=CARD2, text_color=TEXT,
                         font=self.F(12, "bold")).pack(side="left")
            ctk.CTkLabel(c, text=d, text_color=MUTED, font=self.F(12)).pack(side="left", padx=10)
        return p

    # ---------- Kayıt sayfası
    def _build_log_page(self, parent):
        p = ctk.CTkFrame(parent, fg_color="transparent")
        f, body = self.card(p, "İşlem kaydı")
        f.pack(fill="both", expand=True)
        self.txt = ctk.CTkTextbox(body, font=ctk.CTkFont("Consolas" if IS_WIN else "DejaVu Sans Mono", 12),
                                  fg_color=CARD2, text_color=TEXT, corner_radius=10, border_width=0, wrap="word")
        self.txt.pack(fill="both", expand=True)
        self.txt.configure(state="disabled")
        r = ctk.CTkFrame(body, fg_color="transparent")
        r.pack(fill="x", pady=(10, 0))
        self.button(r, "Kopyala", self.copy_log, width=130).pack(side="right")
        self.button(r, "Temizle", self.clear_log, width=130).pack(side="right", padx=8)
        return p

    # ---------- alt eylem çubuğu
    def _build_actionbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER)
        bar.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        bar.columnconfigure(1, weight=1)
        st = ctk.CTkFrame(bar, fg_color="transparent", width=150)
        st.grid(row=0, column=0, padx=(18, 10), pady=14, sticky="w")
        self.dot = tk.Canvas(st, width=14, height=14, highlightthickness=0, bg=mc(CARD))
        self.dot.pack(side="left")
        self.lbl_state = ctk.CTkLabel(st, text="Hazır", font=self.F(13, "bold"), text_color=TEXT, width=120,
                                      anchor="w")
        self.lbl_state.pack(side="left", padx=(8, 0))

        self.cb_device = ctk.CTkComboBox(bar, variable=self.v_device, values=["Cihaz yok"], state="readonly",
                                         height=40, corner_radius=10, fg_color=CARD2, border_color=BORDER,
                                         button_color=BORDER, button_hover_color=ACCENT, text_color=TEXT,
                                         font=self.F(13), dropdown_font=self.F(13),
                                         command=lambda v: self.sfx.play("nav"))
        self.cb_device.grid(row=0, column=1, sticky="ew", pady=14)
        self.switch(bar, "🔊 Sesi aktar", self.v_audio).grid(row=0, column=2, padx=16)
        self.v_audio.trace_add("write", lambda *_: self._live_change("Ses " + ("açıldı" if self.v_audio.get() else "kapatıldı")))
        self.btn_main = ctk.CTkButton(bar, text="▶   BAŞLAT", width=190, height=46, corner_radius=12,
                                      fg_color=GREEN, hover_color=GREEN_H, text_color="#ffffff",
                                      font=self.F(15, "bold"), command=self.toggle_run)
        self.btn_main.grid(row=0, column=3, padx=(0, 14), pady=12)

    # ================= sürekli animasyonlar (durum noktası, radar, süre)
    def _tick(self):
        now = time.perf_counter()
        try:
            self.dot.configure(bg=mc(CARD))
            self.dot.delete("all")
            if self.running:
                k = (math.sin(now * 5) + 1) / 2
                r = 4 + 3 * k
                self.dot.create_oval(7 - r, 7 - r, 7 + r, 7 + r, fill=lerp_color(RED, CARD, .65 * k), outline="")
                self.dot.create_oval(3, 3, 11, 11, fill=mc(RED), outline="")
                el = int(time.time() - self.started_at)
                self.lbl_state.configure(text=f"Canlı  {el // 3600:02d}:{el % 3600 // 60:02d}:{el % 60:02d}")
            else:
                self.dot.create_oval(3, 3, 11, 11, fill=mc(GREEN if self.connected else MUTED), outline="")
            if self.empty.winfo_ismapped():
                self._draw_radar(now)
        except tk.TclError:
            return
        self.after(40, self._tick)

    def _draw_radar(self, now):
        c = self.radar
        c.configure(bg=mc(CARD))
        c.delete("all")
        cx, cy = 110, 60
        for k in range(3):
            ph = (now / 2.2 + k / 3) % 1
            r = 16 + ph * 42
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=lerp_color(ACCENT, CARD, ph), width=2)
        ang = (now * 140) % 360
        c.create_arc(cx - 50, cy - 50, cx + 50, cy + 50, start=ang, extent=40, style="pieslice",
                     fill=lerp_color(ACCENT, CARD, .82), outline="")
        c.create_oval(cx - 16, cy - 16, cx + 16, cy + 16, fill=mc(ACCENT), outline="")
        c.create_rectangle(cx - 5, cy - 8, cx + 5, cy + 8, outline="#ffffff", width=2)

    # ================= tost bildirimleri
    def toast(self, text, kind="info"):
        color = {"info": ACCENT, "ok": GREEN, "err": RED, "warn": AMBER}[kind]
        icon = {"info": "ℹ", "ok": "✔", "err": "✖", "warn": "⚠"}[kind]
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
        t = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=2, border_color=color)
        ctk.CTkLabel(t, text=icon, text_color=color, font=self.F(16, "bold")).pack(side="left", padx=(14, 6), pady=10)
        ctk.CTkLabel(t, text=text, text_color=TEXT, font=self.F(13, "bold"), wraplength=340,
                     justify="left").pack(side="left", padx=(0, 16), pady=10)
        self._toast = t
        self.animate(320, lambda k: t.place(relx=1.0, rely=1.0, x=-26, y=int(60 - 170 * k), anchor="se"))

        def hide():
            if self._toast is not t:
                return
            self.animate(260, lambda k: t.place(relx=1.0, rely=1.0, x=int(-26 + 420 * k), y=-110, anchor="se"),
                         done=t.destroy, ease=lambda x: x * x)
        self.after(3200, hide)

    # ================= kayıt
    def log(self, msg):
        if msg:
            self.log_q.put(msg)

    def _drain_log(self):
        lines = []
        try:
            while True:
                lines.append(self.log_q.get_nowait().rstrip())
        except queue.Empty:
            pass
        if lines:
            self.txt.configure(state="normal")
            self.txt.insert("end", "\n".join(lines) + "\n")
            self.txt.see("end")
            self.txt.configure(state="disabled")
        self.after(120, self._drain_log)

    def copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.txt.get("1.0", "end"))
        self.toast("Kayıt panoya kopyalandı", "ok")

    def clear_log(self):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")

    def bg(self, fn, *a):
        threading.Thread(target=fn, args=a, daemon=True).start()

    def ui(self, fn, *a):
        self.after(0, lambda: fn(*a))

    # ================= tema / ses efekti
    def set_theme(self, v):
        mode = "dark" if v == "Koyu" else "light"
        ctk.set_appearance_mode(mode)
        self.cfg["theme"] = v
        save_cfg(self.cfg)

    def _sfx_changed(self):
        self.sfx.enabled = self.v_sfx.get()
        self.cfg["sfx"] = self.sfx.enabled
        save_cfg(self.cfg)
        if self.sfx.enabled:
            self.sfx.play("toggle")

    # ================= sürüm takibi: GitHub'daki son sürümü kontrol et
    @staticmethod
    def _ver_tuple(v):
        return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)

    def _check_update(self):
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                                         headers={"User-Agent": f"yansit/{VERSION}",
                                                  "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                rel = json.load(r)
            tag = rel.get("tag_name", "")
            if self._ver_tuple(tag) > self._ver_tuple(VERSION):
                self.log(f"Yeni sürüm var: {tag} (kullanılan: v{VERSION})")

                def show():
                    self.upd_lbl.configure(text=f"⬆ Yeni sürüm: {tag}\nŞu an: v{VERSION}")
                    self.upd_box.pack(side="bottom", fill="x", padx=18, pady=(0, 4))
                    self.toast(f"Yansıt {tag} yayınlandı — sol alttan indirebilirsin", "info")
                self.ui(show)
            else:
                self.log(f"Yansıt güncel (v{VERSION}).")
        except Exception as e:  # internet yoksa sessizce geç
            self.log(f"Güncelleme kontrol edilemedi: {e}")

    # ================= scrcpy kurulumu
    def check_scrcpy(self):
        sc = find_tool("scrcpy")
        if sc:
            rc, out = run([sc, "--version"], 10)
            ver = out.splitlines()[0].replace("scrcpy ", "") if out else "?"
            ver = ver.split(" <")[0]
            self.lbl_scrcpy.configure(text=f"✔ scrcpy {ver}", text_color=GREEN)
            if not getattr(self, "_scanning", False):
                self._scanning = True
                self.bg(self._scan_loop)
        else:
            self.lbl_scrcpy.configure(text="✖ scrcpy yok — ilk sefer için aşağıdan indirin", text_color=RED)

    def download_scrcpy(self):
        if not IS_WIN:
            self.toast("Otomatik indirme sadece Windows'ta. Paket yöneticisinden scrcpy kurun.", "warn")
            return
        if self.running:
            self.toast("Önce yansıtmayı durdurun", "warn")
            return
        self.btn_dl.configure(state="disabled")
        self.dl_bar.set(0)
        self.dl_bar.pack(fill="x", pady=(8, 0), before=self.btn_dl)
        self.bg(self._download_worker)

    def _download_worker(self):
        try:
            self.log("GitHub'dan son scrcpy sürümü aranıyor...")
            hdr = {"User-Agent": f"yansit/{VERSION}"}
            req = urllib.request.Request("https://api.github.com/repos/Genymobile/scrcpy/releases/latest", headers=hdr)
            with urllib.request.urlopen(req, timeout=30) as r:
                rel = json.load(r)
            asset = next(a for a in rel["assets"] if re.match(r"scrcpy-win64-.*\.zip$", a["name"]))
            total = asset["size"] or 1
            self.log(f"İndiriliyor: {asset['name']}")
            req = urllib.request.Request(asset["browser_download_url"], headers=hdr)
            data = bytearray()
            with urllib.request.urlopen(req, timeout=180) as r:
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    data += chunk
                    self.ui(self.dl_bar.set, min(1.0, len(data) / total))
            old = find_tool("adb")
            if old:
                run([old, "kill-server"], 10)
            if os.path.isdir(SCRCPY_DIR):
                shutil.rmtree(SCRCPY_DIR, ignore_errors=True)
            os.makedirs(SCRCPY_DIR, exist_ok=True)
            zipfile.ZipFile(io.BytesIO(bytes(data))).extractall(SCRCPY_DIR)
            self.log(f"Kuruldu: {rel['tag_name']}")
            self.ui(lambda: (self.sfx.play("success"), self.toast(f"scrcpy {rel['tag_name']} kuruldu", "ok"),
                             self.check_scrcpy()))
        except Exception as e:
            self.log(f"İndirme hatası: {e}")
            self.ui(lambda: (self.sfx.play("error"), self.toast("İndirme başarısız. Kayıt sayfasına bakın.", "err")))
        finally:
            self.ui(lambda: (self.dl_bar.pack_forget(), self.btn_dl.configure(state="normal")))

    # ================= adb / tarama
    def adb(self):
        a = find_tool("adb")
        if not a:
            self.log("adb bulunamadı. Önce scrcpy'yi indirin.")
        return a

    def _scan_loop(self):
        adb = find_tool("adb")
        if not adb:
            self._scanning = False
            return
        run([adb, "start-server"], 30)
        rc, out = run([adb, "mdns", "check"], 10)
        if rc != 0 or "error" in out.lower() or "unavailable" in out.lower():
            self.log("Uyarı: ağ taraması kullanılamıyor (" + out + "). Elle bağlanmayı kullanın.")
        while True:
            try:
                self._refresh_devices(adb)
                self._refresh_network(adb)
            except Exception as e:  # noqa
                self.log(f"Tarama hatası: {e}")
            time.sleep(3)

    def _refresh_devices(self, adb):
        rc, out = run([adb, "devices", "-l"])
        devs, serials = [], []
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            model = next((x.split(":", 1)[1] for x in parts if x.startswith("model:")), "").replace("_", " ")
            tag = "Wi-Fi" if (":" in serial or "_adb-tls" in serial) else "USB"
            label = f"{model or 'Android'}  ·  {tag}  ·  {serial}"
            if state != "device":
                label += "  (telefonda izin ver!)" if state == "unauthorized" else f"  ({state})"
            else:
                serials.append(serial)
            devs.append(label)
        self.connected = serials

        def upd():
            self.cb_device.configure(values=devs or ["Cihaz yok"])
            cur = self.selected_serial()
            if cur and any(d.endswith(cur) or f"· {cur}" in d for d in devs):
                return
            prev = self.cfg.get("device", "")
            pick = next((d for d in devs if f"· {prev}" in d), devs[0] if devs else "Cihaz yok")
            self.v_device.set(pick)
        self.ui(upd)

    def _refresh_network(self, adb):
        svcs = mdns_services(adb)
        rows = {}
        for name, typ, addr in svcs:
            if typ.startswith("_adb-tls-connect"):
                ip = addr.split(":")[0]
                conn = any(s == addr or s.startswith(name) or s.startswith(ip + ":") for s in self.connected)
                rows[name] = (self.cfg["known"].get(name) or self._pretty(name), addr,
                              "connected" if conn else "ready", name)
        for name, typ, addr in svcs:
            if typ.startswith("_adb-tls-pairing") and not name.startswith("tep-"):
                rows.setdefault("pair:" + name, (self._pretty(name), addr, "pairing", name))
        self.ui(self._sync_cards, rows)

    def _sync_cards(self, rows):
        new_found = False
        for key in list(self.cards):
            if key not in rows:
                self.cards.pop(key).destroy()
                self.card_meta.pop(key, None)
        for key, (label, addr, state, name) in sorted(rows.items(), key=lambda kv: kv[1][0].lower()):
            if key not in self.cards:
                card = DeviceCard(self.dev_list, self, key)
                card.pack(fill="x", pady=4, padx=(0, 4))
                self.cards[key] = card
                card.update_info(label, addr, state)
                card.appear()
                new_found = True
            else:
                self.cards[key].update_info(label, addr, state)
            self.card_meta[key] = (name, addr, state)
        if rows and not self.dev_list.winfo_ismapped():
            self.empty.pack_forget()
            self.dev_list.pack(fill="both", expand=True)
        elif not rows and not self.empty.winfo_ismapped():
            self.dev_list.pack_forget()
            self.empty.pack(fill="both", expand=True)
        if new_found and getattr(self, "_scanned_once", False):
            self.sfx.play("tick")
        self._scanned_once = True
        self.lbl_scan.configure(text=f"{len(rows)} telefon · {time.strftime('%H:%M:%S')}")

    @staticmethod
    def _pretty(name):
        m = re.match(r"adb-(.+?)-\w+$", name)
        return f"Android ({m.group(1)})" if m else name

    # ================= bağlanma
    def card_action(self, key):
        name, addr, state = self.card_meta.get(key, (None, None, None))
        if not addr:
            return
        if state == "pairing":
            self.e_pair.delete(0, "end")
            self.e_pair.insert(0, addr)
            self.e_code.focus_set()
            self.toast("Telefondaki 6 haneli kodu 'Elle bağlan' kartına girip Eşleştir'e basın", "info")
        elif state == "connected":
            ip = addr.split(":")[0]
            serial = next((s for s in self.connected if s == addr or s.startswith(name) or s.startswith(ip + ":")), "")
            for v in self.cb_device.cget("values"):
                if serial and v.endswith(serial):
                    self.v_device.set(v)
                    self.toast("Cihaz seçildi — Başlat'a basabilirsin", "ok")
        else:
            self.connect_addr(addr, name)

    def connect_addr(self, addr, mdns_name=None, sync=False, quiet=False):
        if not addr:
            self.toast("IP:Port girin", "warn")
            return

        def w():
            adb = self.adb()
            if not adb:
                return
            self.log(f"Bağlanılıyor: {addr}")
            rc, out = run([adb, "connect", addr], 20)
            self.log(out)
            low = out.lower()
            if "connected to" in low and "failed" not in low:
                self.cfg["device"] = addr
                rc, model = run([adb, "-s", addr, "shell", "getprop", "ro.product.model"], 10)
                rc2, brand = run([adb, "-s", addr, "shell", "getprop", "ro.product.manufacturer"], 10)
                nice = f"{brand.strip().title()} {model.strip()}".strip() if rc == 0 else addr
                if mdns_name and rc == 0:
                    self.cfg["known"][mdns_name] = nice
                save_cfg(self.cfg)
                self._refresh_devices(adb)
                if not quiet:
                    self.ui(lambda: (self.sfx.play("connect"), self.toast(f"Bağlandı: {nice}", "ok")))
            else:
                self.ui(lambda: (self.sfx.play("error"),
                                 self.toast("Bağlanılamadı. Telefon eşleşmemiş olabilir → QR ile eşleştir.", "err")))
        if sync:
            w()
        else:
            self.bg(w)

    def open_qr(self):
        if not find_tool("adb"):
            self.toast("Önce scrcpy'yi indirin (sol alttaki buton)", "warn")
            return
        QrPairWindow(self)

    def pair_code(self):
        addr, code = self.e_pair.get().strip(), self.e_code.get().strip()
        if not addr or not code:
            self.toast("Telefonda 'Cihazı eşleme koduyla eşle' → IP:Port ve kodu girin", "warn")
            return

        def w():
            adb = self.adb()
            if not adb:
                return
            rc, out = run([adb, "pair", addr, code], 30)
            self.log(out)
            if "Successfully" in out:
                self.ui(lambda: (self.sfx.play("success"), self.toast("Eşleşti! Telefon birazdan listede görünür", "ok")))
            else:
                self.ui(lambda: (self.sfx.play("error"), self.toast("Eşleştirme başarısız. Kodu kontrol edin.", "err")))
        self.bg(w)

    def disconnect_all(self):
        def w():
            adb = self.adb()
            if adb:
                self.log(run([adb, "disconnect"], 10)[1])
                self.ui(self.toast, "Kablosuz bağlantılar kesildi", "info")
        self.bg(w)

    def usb_to_wifi(self):
        serial = self.selected_serial()
        if not serial or ":" in serial or "_adb-tls" in serial:
            self.toast("Önce telefonu USB ile bağlayıp alttan seçin", "warn")
            return

        def w():
            adb = self.adb()
            if not adb:
                return
            rc, out = run([adb, "-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"])
            m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
            if not m:
                self.ui(self.toast, "Telefonun Wi-Fi IP'si bulunamadı. Wi-Fi açık mı?", "err")
                return
            ip = m.group(1)
            self.log(run([adb, "-s", serial, "tcpip", "5555"])[1])
            time.sleep(2)
            self.connect_addr(f"{ip}:5555", sync=True)
            self.ui(self.toast, "USB kablosunu çıkarabilirsiniz", "info")
        self.bg(w)

    def selected_serial(self):
        v = self.v_device.get().strip()
        if not v or v == "Cihaz yok":
            return ""
        return v.split("·")[-1].split("(")[0].strip()

    # ================= ayarlar
    def _update_br(self):
        self.lbl_br.configure(text=f"{self.v_bitrate.get()} Mbps")

    def _custom(self):
        if not self._applying:
            self.v_preset.set("Özel")

    def apply_preset(self, name):
        self.sfx.play("nav")
        p = PRESETS.get(name)
        if not p:
            return
        self._applying = True
        self.v_size.set(p["size"])
        self.v_bitrate.set(p["bitrate"])
        self.v_fps.set(p["fps"])
        self.v_codec.set(p["codec"])
        if p["no_control"] is not None:
            self.v_noctl.set(p["no_control"])
        self._update_br()
        self._applying = False

    def collect_cfg(self):
        self.cfg.update({
            "preset": self.v_preset.get(), "size": self.v_size.get(), "bitrate": int(self.v_bitrate.get()),
            "fps": self.v_fps.get(), "codec": self.v_codec.get(),
            "audio": self.v_audio.get(), "audio_dup": self.v_dup.get(),
            "stay_awake": self.v_awake.get(), "on_top": self.v_top.get(),
            "borderless": self.v_border.get(), "no_control": self.v_noctl.get(),
            "screen_off": self.v_screen_off.get(), "auto_reconnect": self.v_reconn.get(),
            "window_title": self.e_title.get().strip() or "Yansit",
            "wifi_addr": self.e_wifi.get().strip(), "pair_addr": self.e_pair.get().strip(),
            "device": self.selected_serial() or self.cfg.get("device", ""),
            "theme": self.v_theme.get(), "sfx": self.v_sfx.get(),
        })
        save_cfg(self.cfg)

    # ---- ses modu: 0=telefonda da çal (playback+dup), 1=tüm ses (output), 2=output+AAC, 3=sessiz
    def build_cmd(self, audio_level):
        c = self.cfg
        cmd = [find_tool("scrcpy"), "--window-title", c["window_title"], "--serial", c["device"]]
        if c["size"].isdigit():
            cmd += ["--max-size", c["size"]]
        cmd += ["--video-bit-rate", f"{c['bitrate']}M", "--max-fps", c["fps"], "--video-codec", c["codec"]]
        if audio_level == 0:
            cmd += ["--audio-dup", "--require-audio", "--audio-bit-rate", "160K"]
        elif audio_level == 1:
            cmd += ["--audio-source=output", "--require-audio", "--audio-bit-rate", "160K"]
        elif audio_level == 2:
            cmd += ["--audio-source=output", "--audio-codec=aac", "--require-audio", "--audio-bit-rate", "160K"]
        else:
            cmd.append("--no-audio")
        if c["stay_awake"]:
            cmd.append("--stay-awake")
        if c["no_control"]:
            cmd.append("--no-control")
        elif c["screen_off"]:
            cmd.append("--turn-screen-off")
        if c["on_top"]:
            cmd.append("--always-on-top")
        if c["borderless"]:
            cmd.append("--window-borderless")
        return cmd

    def _first_audio_level(self, adb, serial):
        """Telefonun Android sürümüne göre en uygun ses yöntemini seç."""
        if not self.cfg["audio"]:
            return 3
        rc, sdk = run([adb, "-s", serial, "shell", "getprop", "ro.build.version.sdk"], 10)
        try:
            sdk = int(sdk.strip())
        except ValueError:
            sdk = 0
        rc, rel = run([adb, "-s", serial, "shell", "getprop", "ro.build.version.release"], 10)
        self.log(f"Telefon: Android {rel.strip()} (API {sdk})")
        if sdk and sdk < 30:
            self.ui(self.toast, f"Android {rel.strip()}: ses aktarımı için Android 11+ gerekir. Sadece görüntü.", "warn")
            return 3
        if sdk == 30:
            self.log("Android 11: ses için telefonun kilidi açık olmalı.")
        if self.cfg["audio_dup"] and sdk >= 33:
            return 0
        if self.cfg["audio_dup"]:
            self.log("'Telefonda da çalsın' Android 13+ ister; tüm-ses moduna geçildi.")
        return 1

    # ================= yansıtma
    def toggle_run(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def _set_running(self, on):
        if on == self.running:
            return
        self.running = on
        a, b = (GREEN, RED) if on else (RED, GREEN)
        self.btn_main.configure(text="■   DURDUR" if on else "▶   BAŞLAT", hover_color=RED_H if on else GREEN_H)
        self.animate(300, lambda t: self.btn_main.configure(fg_color=lerp_color(a, b, t)),
                     done=lambda: self.btn_main.configure(fg_color=b))
        if not on:
            self.lbl_state.configure(text="Hazır")

    def start(self):
        if not find_tool("scrcpy"):
            self.sfx.play("error")
            self.toast("Önce scrcpy'yi indirin (sol alttaki buton)", "warn")
            return
        if self.proc and self.proc.poll() is None:
            return
        self.collect_cfg()
        if not self.selected_serial():
            self.sfx.play("error")
            self.toast("Önce bir telefona bağlanın ve alttan seçin", "warn")
            return
        self.cfg["device"] = self.selected_serial()
        self.sfx.play("start")
        self.user_stopped = False
        self.started_at = time.time()
        self._set_running(True)
        self.bg(self._run_loop)

    def _run_loop(self):
        adb = find_tool("adb")
        level = self._first_audio_level(adb, self.cfg["device"]) if adb else (1 if self.cfg["audio"] else 3)
        while not self.user_stopped:
            cmd = self.build_cmd(level)
            self.log("> scrcpy " + " ".join(cmd[1:]))
            t0 = time.time()
            audio_err = False
            try:
                self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                             text=True, encoding="utf-8", errors="replace", env=tool_env(),
                                             creationflags=NO_WINDOW, cwd=os.path.dirname(cmd[0]))
                for line in self.proc.stdout:
                    self.log(line)
                    low = line.lower()
                    if "audio" in low and any(w in low for w in ("error", "fail", "not supported", "disabled", "could not")):
                        audio_err = True
                self.proc.wait()
            except Exception as e:
                self.log(f"Başlatma hatası: {e}")
                break
            rcode = self.proc.returncode
            if self.user_stopped:
                break
            if self._restart:
                self._restart = False
                level = self._first_audio_level(adb, self.cfg["device"]) if adb else level
                continue
            if rcode == 0:
                break  # kullanıcı scrcpy penceresini kapattı
            if audio_err and level < 3 and time.time() - t0 < 20:
                level += 1
                msg = {1: "Bu uygulama/telefon 'telefonda da çalsın' modunda sesi vermiyor → tüm-ses moduna geçiliyor",
                       2: "Ses kodlayıcı sorunu → AAC ile deneniyor",
                       3: "Bu telefondan ses alınamadı → sadece görüntü"}[level]
                self.log(msg)
                self.ui(self.toast, msg, "warn")
                continue
            if not self.cfg["auto_reconnect"]:
                self.ui(lambda: (self.sfx.play("error"), self.toast("Yansıtma durdu. Kayıt sayfasına bakın.", "err")))
                break
            self.log("Bağlantı koptu, yeniden deneniyor... (Durdur ile iptal)")
            self.ui(self.toast, "Bağlantı koptu — yeniden bağlanılıyor", "warn")
            dev = self.cfg["device"]
            if adb and ":" in dev:
                run([adb, "connect", dev], 10)
            for _ in range(40):
                if self.user_stopped:
                    break
                time.sleep(0.1)
        self.proc = None
        self.ui(self._set_running, False)
        self.log("Yansıtma durdu.")

    def _live_change(self, what):
        self.collect_cfg()
        if self.proc and self.proc.poll() is None and not self.user_stopped:
            self.log(f"{what} — yeni ayarla yeniden başlatılıyor...")
            self.toast(f"{what} — yeniden başlatılıyor", "info")
            self._restart = True
            self.proc.terminate()

    def stop(self):
        if self.running:
            self.sfx.play("stop")
        self.user_stopped = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        else:
            self._set_running(False)

    def on_close(self):
        self.collect_cfg()
        self.user_stopped = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
