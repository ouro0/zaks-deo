# main.py — Zak's Deo Download
# © 2024 Zak. Tous droits réservés.
#
# Lancer : python -m uvicorn main:app --host 0.0.0.0 --port 8000
# Ouvrir : http://localhost:8000

import os, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List

from database import init_db, get_conn
from worker import download_queue, queue_lock, progress, start_worker
from utils import start_cleanup_scheduler
from downloader import validate_url, detect_platform, get_video_info, FORMAT_DEFS, FFMPEG_OK

# ── Pydantic ───────────────────────────────────────────────────────────────────
class DownloadRequest(BaseModel):
    url: str
    format: str = "video_480"

class MultiDownloadRequest(BaseModel):
    urls: List[str]
    format: str = "video_480"

# ── Init ───────────────────────────────────────────────────────────────────────
init_db()
start_worker()
start_cleanup_scheduler()

app = FastAPI(title="Zak's Deo Download", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=THIS_DIR), name="static")


# ── Pages HTML ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def serve_index():
    return FileResponse(os.path.join(THIS_DIR, "index.html"))


# ── API : formats disponibles ─────────────────────────────────────────────────
@app.get("/api/formats")
def list_formats():
    return {
        "ffmpeg_available": FFMPEG_OK,
        "formats": [{"id": k, **v} for k, v in FORMAT_DEFS.items()]
    }


# ── API : preview info vidéo (avec recommandation format) ────────────────────
@app.post("/api/info")
def video_info(data: DownloadRequest):
    if not validate_url(data.url):
        raise HTTPException(400, "URL invalide")
    try:
        info = get_video_info(data.url)
        info["platform"] = detect_platform(data.url)
        return info
    except Exception as e:
        raise HTTPException(400, f"Impossible d'extraire les infos : {str(e)[:200]}")


# ── API : créer un job de téléchargement ──────────────────────────────────────
@app.post("/api/download")
def create_job(data: DownloadRequest):
    if not validate_url(data.url):
        raise HTTPException(400, "URL invalide (doit commencer par https://)")

    job_id = str(uuid.uuid4())

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO jobs (id, url, format, status) VALUES (?,?,?,?)",
            (job_id, data.url, data.format, "pending")
        )
        conn.commit()
    finally:
        conn.close()

    with queue_lock:
        download_queue.append((job_id, data.url, data.format))

    return {"job_id": job_id, "status": "pending"}


# ── API : file d'attente multi-URLs ──────────────────────────────────────────
@app.post("/api/download/batch")
def create_batch(data: MultiDownloadRequest):
    """Envoie plusieurs URLs d'un coup, retourne la liste des job_ids."""
    jobs = []
    conn = get_conn()
    try:
        for url in data.urls:
            if not validate_url(url):
                continue
            job_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO jobs (id, url, format, status) VALUES (?,?,?,?)",
                (job_id, url, data.format, "pending")
            )
            jobs.append({"job_id": job_id, "url": url, "status": "pending"})
        conn.commit()
    finally:
        conn.close()

    with queue_lock:
        for j in jobs:
            download_queue.append((j["job_id"], j["url"], data.format))

    return {"jobs": jobs, "total": len(jobs)}


# ── API : statut d'un job ─────────────────────────────────────────────────────
@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(404, "Job introuvable")

    result = dict(row)
    result["progress"] = progress.get(job_id, {
        "pct": 100 if row["status"] == "done" else 0,
        "speed": "—",
        "eta": "—"
    })
    return result


# ── API : télécharger le fichier final ────────────────────────────────────────
@app.get("/api/download/{job_id}/file")
def download_file(job_id: str):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(404, "Job introuvable")
    if row["status"] != "done":
        raise HTTPException(400, "Fichier pas encore prêt")

    filepath = row["filepath"]
    if not filepath or not os.path.isfile(filepath):
        raise HTTPException(410, "Fichier expiré (supprimé après 30 minutes)")

    return FileResponse(
        filepath,
        filename=row["filename"],
        media_type="application/octet-stream"
    )
