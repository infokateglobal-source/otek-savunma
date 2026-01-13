import os
import time
import shutil
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError as e:
    raise SystemExit("Missing dependency 'watchdog'. Install with: pip install -r requirements.txt") from e

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

        print(f"\n[{APP_NAME}] SCAN: {res.path}")
        print(f"  score: {res.score}")
        for r in res.reasons:
            print(f"   - {r}")

        if res.score >= self.threshold:
            try:
                qpath = quarantine_file(res.path, self.quarantine_dir)
                record["action"] = "quarantine"
                record["quarantine_path"] = str(qpath)
                print(f"[{APP_NAME}] KARANTİNA: {qpath}")
            except Exception as e:
                record["action"] = "error"
                record["error"] = str(e)
                print(f"[{APP_NAME}] HATA: Karantina başarısız: {e}")

        write_log(self.log_path, record)

def user_downloads() -> Path:
    return Path.home() / "Downloads"

def app_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / "OtekSavunma"

def main():
    watch_dir = user_downloads()
    data_dir = app_data_dir()
    quarantine_dir = data_dir / "Quarantine"
    log_path = data_dir / "logs" / "events.ndjson"

    threshold = int(os.environ.get("OTEK_THRESHOLD", DEFAULT_THRESHOLD))

    print(f"{APP_NAME} başlıyor…")
    print(f"İzlenen klasör: {watch_dir}")
    print(f"Karantina: {quarantine_dir}")
    print(f"Log: {log_path}")
    print(f"Eşik (threshold): {threshold}")
    print("Çıkmak için Ctrl+C")

    observer = Observer()
    handler = WatchHandler(quarantine_dir=quarantine_dir, log_path=log_path, threshold=threshold)
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDurduruluyor…")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
