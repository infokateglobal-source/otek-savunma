import os
import time
import shutil
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

APP_NAME = "Otek Savunma"
DEFAULT_THRESHOLD = 60

SUSPICIOUS_EXTS = {".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jar", ".scr", ".lnk"}
MACRO_EXTS = {".docm", ".xlsm", ".pptm"}
SUSPICIOUS_KEYWORDS = {"crack", "keygen", "activator", "patch", "loader", "invoice", "fatura", "teklif", "odeme", "ödeme"}

def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

@dataclass
class ScanResult:
    path: str
    sha256: str
    score: int
    reasons: list

def sha256_file(path: str, max_bytes: int = 50_000_000) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        remaining = max_bytes
        while remaining > 0:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()

def risk_score(path: str) -> ScanResult:
    reasons = []
    score = 0
    p = Path(path)
    name = p.name.lower()
    ext = p.suffix.lower()

    if ext in SUSPICIOUS_EXTS:
        score += 50
        reasons.append(f"Çalıştırılabilir/Script uzantısı: {ext}")

    if ext in MACRO_EXTS:
        score += 30
        reasons.append(f"Makro destekli ofis dosyası: {ext}")

    parts = name.split(".")
    if len(parts) >= 3 and parts[-1] in {"exe","bat","cmd","ps1","js","vbs","scr"}:
        score += 40
        reasons.append("Çift uzantı şüphesi (örn: pdf.exe)")

    if any(k in name for k in SUSPICIOUS_KEYWORDS):
        score += 15
        reasons.append("Şüpheli dosya adı deseni (invoice/fatura/crack vb.)")

    try:
        size = p.stat().st_size
        if ext in SUSPICIOUS_EXTS and size < 200_000:
            score += 15
            reasons.append("Çok küçük çalıştırılabilir (dropper olasılığı)")
    except Exception:
        pass

    file_hash = ""
    try:
        file_hash = sha256_file(path)
    except Exception as e:
        score += 10
        reasons.append(f"Hash alınamadı: {e}")

    return ScanResult(path=str(p), sha256=file_hash, score=score, reasons=reasons)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def quarantine_file(path: str, quarantine_dir: Path) -> Path:
    ensure_dir(quarantine_dir)
    src = Path(path)
    ts = int(time.time())
    dest = quarantine_dir / f"{ts}_{src.name}"
    shutil.move(str(src), str(dest))
    return dest

def write_log(log_path: Path, record: dict):
    ensure_dir(log_path.parent)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

class WatchHandler(FileSystemEventHandler):
    def __init__(self, quarantine_dir: Path, log_path: Path, threshold: int = DEFAULT_THRESHOLD):
        self.quarantine_dir = quarantine_dir
        self.log_path = log_path
        self.threshold = threshold

    def _wait_stable(self, path: Path, tries: int = 12, sleep_s: float = 0.5):
        last = -1
        for _ in range(tries):
            try:
                cur = path.stat().st_size
                if cur == last and cur > 0:
                    return
                last = cur
            except Exception:
                pass
            time.sleep(sleep_s)

    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)

        if p.suffix.lower() in {".crdownload", ".tmp", ".part"}:
            return

        self._wait_stable(p)

        res = risk_score(str(p))
        record = {
            "ts": now_ts(),
            "path": res.path,
            "sha256": res.sha256,
            "score": res.score,
            "reasons": res.reasons,
            "action": "allow"
        }

        if res.score >= self.threshold:
            try:
                qpath = quarantine_file(res.path, self.quarantine_dir)
                record["action"] = "quarantine"
                record["quarantine_path"] = str(qpath)
            except Exception as e:
                record["action"] = "error"
                record["error"] = str(e)

        write_log(self.log_path, record)

def user_downloads() -> Path:
    return Path.home() / "Downloads"

def app_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / "OtekSavunma"

class OtekAgent:
    """
    Start/stop wrapper so GUI and tray can control the observer safely.
    """
    def __init__(self, threshold: int | None = None):
        self.threshold = int(os.environ.get("OTEK_THRESHOLD", threshold or DEFAULT_THRESHOLD))
        self.data_dir = app_data_dir()
        self.quarantine_dir = self.data_dir / "Quarantine"
        self.log_path = self.data_dir / "logs" / "events.ndjson"
        self.watch_dir = user_downloads()
        self._observer: Observer | None = None
        self._lock = Lock()

    @property
    def is_running(self) -> bool:
        return self._observer is not None

    def start(self):
        with self._lock:
            if self._observer is not None:
                return
            handler = WatchHandler(self.quarantine_dir, self.log_path, self.threshold)
            obs = Observer()
            obs.schedule(handler, str(self.watch_dir), recursive=False)
            obs.start()
            self._observer = obs

    def stop(self):
        with self._lock:
            obs = self._observer
            self._observer = None
        if obs:
            obs.stop()
            obs.join(timeout=5)
