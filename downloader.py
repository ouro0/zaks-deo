# downloader.py — Zak's Deo Download
# © 2024 Zak. Tous droits réservés.

import os, shutil, re, sys

FFMPEG_OK     = shutil.which("ffmpeg") is not None
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

FORMAT_DEFS = {
    "video_hq"  : {"label": "Vidéo — Meilleure qualité", "emoji": "🎬", "ffmpeg_required": True},
    "video_1080": {"label": "Vidéo — 1080p maximum",     "emoji": "📺", "ffmpeg_required": True},
    "video_480" : {"label": "Vidéo — 480p léger",        "emoji": "🔻", "ffmpeg_required": False},
    "audio_mp3" : {"label": "Audio — MP3 192 kbps",      "emoji": "🎵", "ffmpeg_required": True},
    "audio_m4a" : {"label": "Audio — M4A natif",         "emoji": "🎙", "ffmpeg_required": False},
}


def strip_ansi(s: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', str(s))


def detect_platform(url: str) -> str:
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u: return "YouTube"
    if "tiktok.com" in u:                      return "TikTok"
    if "instagram.com" in u:                   return "Instagram"
    if "facebook.com" in u or "fb.watch" in u: return "Facebook"
    return "Web"


def validate_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _base_opts() -> dict:
    """
    Options communes à tous les appels yt-dlp.
    Stratégie anti-bot améliorée :
      1. mweb       → client mobile web, moins détecté
      2. android    → client Android officiel
      3. tv_embed   → client TV YouTube
      4. ios        → fallback Apple
      5. web        → fallback classique
    """
    opts = {
        "noplaylist"    : True,
        "quiet"         : True,
        "no_warnings"   : True,
        "ignoreerrors"  : False,
        # Simule un vrai navigateur Chrome récent
        "http_headers"  : {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        # ✅ Clients améliorés : mweb + android ajoutés en priorité
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb", "android", "tv_embed", "ios", "web"],
            }
        },
        # Délai léger pour éviter le rate-limit
        "sleep_interval"      : 1,
        "max_sleep_interval"  : 3,
        # Retry automatique en cas d'échec réseau
        "retries"             : 5,
        "fragment_retries"    : 5,
    }

    # Si l'utilisateur a placé un fichier cookies.txt → on l'utilise
    cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    if os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file
        print("[Downloader] Fichier cookies.txt détecté ✓")

    return opts


def build_ydl_opts(fmt_type: str, out_dir: str, hooks: list = None) -> dict:
    base = _base_opts()
    base["outtmpl"]        = os.path.join(out_dir, "%(title)s.%(ext)s")
    base["progress_hooks"] = hooks or []

    if fmt_type == "video_hq":
        if FFMPEG_OK:
            base["format"] = (
                "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[vcodec^=avc1]+bestaudio"
                "/bestvideo[vcodec!^=av01]+bestaudio"
                "/bestvideo+bestaudio/best"
            )
            base["merge_output_format"] = "mp4"
        else:
            base["format"] = "best[ext=mp4]/best[ext=webm]/best"

    elif fmt_type == "video_1080":
        if FFMPEG_OK:
            base["format"] = (
                "bestvideo[height<=1080][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[height<=1080][vcodec^=avc1]+bestaudio"
                "/bestvideo[height<=1080][vcodec!^=av01]+bestaudio"
                "/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            )
            base["merge_output_format"] = "mp4"
        else:
            base["format"] = "best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best"

    elif fmt_type == "video_480":
        if FFMPEG_OK:
            base["format"] = (
                "bestvideo[height<=480][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[height<=480][vcodec^=avc1]+bestaudio"
                "/bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            )
            base["merge_output_format"] = "mp4"
        else:
            base["format"] = "best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best"

    elif fmt_type == "audio_mp3":
        base["format"] = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
        if FFMPEG_OK:
            base["postprocessors"] = [{
                "key"             : "FFmpegExtractAudio",
                "preferredcodec"  : "mp3",
                "preferredquality": "192",
            }]

    elif fmt_type == "audio_m4a":
        base["format"] = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"

    else:
        base["format"] = "best"

    return base


def get_video_info(url: str) -> dict:
    import yt_dlp
    opts = _base_opts()
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # Détection automatique du meilleur format disponible
        formats   = info.get("formats", [])
        max_height = 0
        has_4k     = False
        has_1080   = False
        for f in formats:
            h = f.get("height") or 0
            if h > max_height:
                max_height = h
            if h >= 2160: has_4k   = True
            if h >= 1080: has_1080 = True

        recommended = "video_480"
        rec_label   = "480p (léger)"
        if has_4k:
            recommended = "video_hq"
            rec_label   = "4K disponible ! Meilleure qualité recommandée"
        elif has_1080:
            recommended = "video_1080"
            rec_label   = "1080p disponible"

        return {
            "title"      : info.get("title", "Unknown"),
            "duration"   : info.get("duration_string", "?"),
            "thumbnail"  : info.get("thumbnail", ""),
            "uploader"   : info.get("uploader", ""),
            "platform"   : detect_platform(url),
            "max_height" : max_height,
            "recommended": recommended,
            "rec_label"  : rec_label,
        }


def download_video(url: str, fmt_type: str, job_id: str, on_progress=None) -> str:
    import yt_dlp

    job_dir = os.path.join(DOWNLOADS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    hooks = []
    if on_progress:
        def _hook(d):
            if d.get("status") == "downloading":
                raw   = strip_ansi(d.get("_percent_str", "0")).strip().rstrip("%")
                speed = strip_ansi(d.get("_speed_str", "?")).strip()
                eta   = strip_ansi(d.get("_eta_str", "?")).strip()
                try:    pct = float(raw)
                except: pct = 0.0
                on_progress(pct, speed, eta)
            elif d.get("status") == "finished":
                on_progress(97, "—", "0s")
        hooks.append(_hook)

    opts = build_ydl_opts(fmt_type, job_dir, hooks)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info     = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if fmt_type == "audio_mp3" and FFMPEG_OK:
            filename = os.path.splitext(filename)[0] + ".mp3"

    # Retourne le vrai fichier présent dans le dossier
    files = [f for f in os.listdir(job_dir) if not f.startswith(".")]
    if files:
        return os.path.join(job_dir, files[0])
    return filename
