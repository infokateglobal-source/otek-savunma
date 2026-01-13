import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import pystray
from PIL import Image

from otek_core import OtekAgent, APP_NAME

def app_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / "OtekSavunma"

DATA_DIR = app_data_dir()
QUAR_DIR = DATA_DIR / "Quarantine"
LOG_FILE = DATA_DIR / "logs" / "events.ndjson"
CRASH_LOG = DATA_DIR / "logs" / "crash.log"

def write_crash(msg: str):
    DATA_DIR.joinpath("logs").mkdir(parents=True, exist_ok=True)
    CRASH_LOG.write_text(msg, encoding="utf-8")

def read_last_events(n: int = 10):
    if not LOG_FILE.exists():
        return []
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        out = []
        for ln in lines[-200:][::-1]:
            if not ln.strip():
                continue
            try:
                import json
                j = json.loads(ln)
                if j.get("action") == "quarantine":
                    out.append(j)
                if len(out) >= n:
                    break
            except Exception:
                continue
        return out
    except Exception:
        return []

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("520x340")
        self.root.resizable(False, False)

        self.agent = OtekAgent()
        self.status_var = tk.StringVar(value="Durum: Kapalı")
        self.path_var = tk.StringVar(value=f"İzlenen: {self.agent.watch_dir}")
        self.th_var = tk.StringVar(value=f"Eşik: {self.agent.threshold}")

        # Header
        tk.Label(root, text=APP_NAME, font=("Segoe UI", 14, "bold")).pack(pady=(12,4))
        tk.Label(root, textvariable=self.status_var, font=("Segoe UI", 11)).pack()
        tk.Label(root, textvariable=self.path_var, font=("Segoe UI", 9)).pack(pady=(6,0))
        tk.Label(root, textvariable=self.th_var, font=("Segoe UI", 9)).pack(pady=(2,8))

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=4)

        self.btn_start = tk.Button(btn_frame, text="Koruma Aç", width=14, command=self.start_agent)
        self.btn_stop = tk.Button(btn_frame, text="Koruma Kapat", width=14, command=self.stop_agent, state="disabled")
        self.btn_open_q = tk.Button(btn_frame, text="Karantina Klasörü", width=16, command=self.open_quarantine)
        self.btn_open_log = tk.Button(btn_frame, text="Log'u Aç", width=12, command=self.open_log)

        self.btn_start.grid(row=0, column=0, padx=6, pady=6)
        self.btn_stop.grid(row=0, column=1, padx=6, pady=6)
        self.btn_open_q.grid(row=1, column=0, padx=6, pady=6)
        self.btn_open_log.grid(row=1, column=1, padx=6, pady=6)

        # Last caught list
        tk.Label(root, text="Son yakalananlar (karantina):", font=("Segoe UI", 9, "bold")).pack(pady=(10,4))
        self.listbox = tk.Listbox(root, height=7, width=80)
        self.listbox.pack(padx=14, fill="x")
        self.listbox.bind("<Double-Button-1>", self.on_item_double_click)

        tk.Label(root, text="Not: Uygulamayı kapatırsan tepsiye gizlenir. Çıkış: tepsi menüsü.", font=("Segoe UI", 8)).pack(pady=(10,0))

        # Tray (start after Tk is up)
        self.tray_icon = None
        self.tray_thread = None
        self.root.after(200, self._setup_tray)

        # Start protection by default
        self.start_agent()

        # Refresh list periodically
        self.refresh_last_events()

        # Window close -> hide to tray
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

    def _resource_path(self, relative: str) -> str:
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        return os.path.join(base_path, relative)

    def _setup_tray(self):
        try:
            icon_img_path = self._resource_path("otek_icon_256.png")
            image = Image.open(icon_img_path)

            menu = pystray.Menu(
                pystray.MenuItem("Paneli Aç", self.show_window, default=True),
                pystray.MenuItem("Koruma Aç", lambda: self.start_agent()),
                pystray.MenuItem("Koruma Kapat", lambda: self.stop_agent()),
                pystray.MenuItem("Karantina", lambda: self.open_quarantine()),
                pystray.MenuItem("Çıkış", self.quit_app),
            )
            self.tray_icon = pystray.Icon("otek", image, APP_NAME, menu)

            def run_tray():
                try:
                    self.tray_icon.run()
                except Exception as e:
                    write_crash(f"Tray error: {e}")

            self.tray_thread = threading.Thread(target=run_tray, daemon=True)
            self.tray_thread.start()
        except Exception as e:
            write_crash(f"Tray init failed: {e}")

    def start_agent(self):
        try:
            self.agent.start()
            self.status_var.set("Durum: Açık (Koruma aktif)")
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            if self.tray_icon:
                self.tray_icon.title = f"{APP_NAME} — Açık"
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Koruma başlatılamadı:\n{e}")

    def stop_agent(self):
        try:
            self.agent.stop()
            self.status_var.set("Durum: Kapalı")
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            if self.tray_icon:
                self.tray_icon.title = f"{APP_NAME} — Kapalı"
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Koruma durdurulamadı:\n{e}")

    def open_quarantine(self):
        QUAR_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(QUAR_DIR))

    def open_log(self):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_FILE.exists():
            LOG_FILE.write_text("", encoding="utf-8")
        if os.name == "nt":
            os.startfile(str(LOG_FILE))

    def on_item_double_click(self, event):
        # Open quarantine folder on double click
        self.open_quarantine()

    def refresh_last_events(self):
        try:
            items = read_last_events(10)
            self.listbox.delete(0, tk.END)
            if not items:
                self.listbox.insert(tk.END, "Henüz karantinaya alınan dosya yok.")
            else:
                for j in items:
                    name = Path(j.get("path","")).name
                    score = j.get("score","?")
                    ts = j.get("ts","")
                    self.listbox.insert(tk.END, f"{ts} | Skor {score} | {name}")
        except Exception as e:
            write_crash(f"Refresh error: {e}")
        self.root.after(2500, self.refresh_last_events)

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, *args, **kwargs):
        self.root.after(0, lambda: (self.root.deiconify(), self.root.lift(), self.root.focus_force()))

    def quit_app(self, *args, **kwargs):
        try:
            self.agent.stop()
        except Exception:
            pass
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.root.after(0, self.root.destroy)

def main():
    try:
        root = tk.Tk()
        App(root)
        root.mainloop()
    except Exception as e:
        write_crash(f"Fatal: {e}")
        # In noconsole mode we can't show stack; best-effort dialog:
        try:
            messagebox.showerror(APP_NAME, f"Uygulama başlatılamadı.\nLog: {CRASH_LOG}\nHata: {e}")
        except Exception:
            pass

if __name__ == "__main__":
    main()
