# worker.py — Zak's Deo Download
# © 2024 Zak. Tous droits réservés.

import time, threading, os
from collections import deque
from database import get_conn
from downloader import download_video

download_queue: deque = deque()
queue_lock             = threading.Lock()
progress: dict         = {}   # job_id -> {pct, speed, eta}


def _set_status(job_id: str, status: str, filepath: str = None, error: str = None):
    conn = get_conn()
    try:
        if filepath:
            conn.execute(
                "UPDATE jobs SET status=?, filepath=?, filename=?, updated=datetime('now') WHERE id=?",
                (status, filepath, os.path.basename(filepath), job_id)
            )
        elif error:
            conn.execute(
                "UPDATE jobs SET status=?, error_msg=?, updated=datetime('now') WHERE id=?",
                (status, error[:500], job_id)
            )
        else:
            conn.execute(
                "UPDATE jobs SET status=?, updated=datetime('now') WHERE id=?",
                (status, job_id)
            )
        conn.commit()
    finally:
        conn.close()


def worker_loop():
    print("[Worker] Démarré ✓")
    while True:
        job = None
        with queue_lock:
            if download_queue:
                job = download_queue.popleft()

        if job:
            job_id, url, fmt = job
            print(f"[Worker] Job {job_id[:8]}… ({fmt})")
            _set_status(job_id, "downloading")
            progress[job_id] = {"pct": 0, "speed": "—", "eta": "—"}

            def on_prog(pct, speed, eta, jid=job_id):
                progress[jid] = {"pct": round(pct, 1), "speed": speed, "eta": eta}

            try:
                _set_status(job_id, "processing")
                filepath = download_video(url, fmt, job_id, on_progress=on_prog)
                _set_status(job_id, "done", filepath=filepath)
                progress[job_id] = {"pct": 100, "speed": "—", "eta": "0s"}
                print(f"[Worker] ✓ {job_id[:8]} → {os.path.basename(filepath)}")
            except Exception as e:
                # ✅ Log complet de l'erreur (au lieu de 150 chars tronqués)
                err = str(e)
                _set_status(job_id, "error", error=err)
                progress[job_id] = {"pct": 0, "speed": "—", "eta": "—"}
                print(f"[Worker] ✗ {job_id[:8]} — ERREUR COMPLÈTE : {err}")
        else:
            time.sleep(0.5)


def start_worker():
    t = threading.Thread(target=worker_loop, daemon=True, name="DownloadWorker")
    t.start()
    return t
