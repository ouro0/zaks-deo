# utils.py — Zak's Deo Download
# © 2024 Zak. Tous droits réservés.

import os, shutil, time, threading
from database import get_conn

DOWNLOADS_DIR         = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
CLEANUP_AFTER_SECONDS = 30 * 60  # 30 minutes


def cleanup_old_files():
    if not os.path.isdir(DOWNLOADS_DIR):
        return
    now = time.time()
    for job_dir in os.listdir(DOWNLOADS_DIR):
        full = os.path.join(DOWNLOADS_DIR, job_dir)
        if os.path.isdir(full) and now - os.path.getmtime(full) > CLEANUP_AFTER_SECONDS:
            try:
                shutil.rmtree(full)
                conn = get_conn()
                try:
                    conn.execute("UPDATE jobs SET filepath=NULL, filename=NULL WHERE id=?", (job_dir,))
                    conn.commit()
                finally:
                    conn.close()
                print(f"[Cleanup] Supprimé : {job_dir[:8]}")
            except Exception as e:
                print(f"[Cleanup] Erreur : {e}")


def start_cleanup_scheduler():
    def loop():
        while True:
            time.sleep(600)
            cleanup_old_files()
    threading.Thread(target=loop, daemon=True, name="Cleanup").start()
    print("[Cleanup] Scheduler démarré ✓")
