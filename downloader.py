# downloader.py — Zak's Deo Download v3
# © 2024 Zak. Tous droits réservés.

import os, shutil, re, subprocess

def _check_ffmpeg() -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

FFMPEG_OK     = _check_ffmpeg()
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

if FFMPEG_OK:
    print("[Downloader] ffmpeg détecté ✓")
else:
    print("[Downloader] ⚠ ffmpeg introuvable")

FORMAT_DEFS = {
    "video_hq"  : {"label": "Meilleure qualité", "emoji": "🎬", "ffmpeg_required": False},
    "video_1080": {"label": "1080p HD",           "emoji": "📺", "ffmpeg_required": False},
    "video_720" : {"label": "720p",               "emoji": "🖥",  "ffmpeg_required": False},
    "video_480" : {"label": "480p léger",         "emoji": "🔻", "ffmpeg_required": False},
    "audio_mp3" : {"label": "MP3 320 kbps",       "emoji": "🎵", "ffmpeg_required": True},
    "audio_m4a" : {"label": "M4A natif",          "emoji": "🎙", "ffmpeg_required": False},
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
    opts = {
        "noplaylist"  : True,
        "quiet"       : True,
        "no_warnings" : True,
        "ignoreerrors": False,
        "concurrent_fragment_downloads": 4,
        "retries"            : 10,
        "fragment_retries"   : 10,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        # android_vr = le client le moins bloqué sur les serveurs cloud
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "android", "mweb", "tv_embed", "ios", "web"],
            }
        },
    }

    cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    if os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file
        print("[Downloader] cookies.txt détecté ✓")

    return opts


def build_ydl_opts(fmt_type: str, out_dir: str, hooks: list = None) -> dict:
    base = _base_opts()
    base["outtmpl"]        = os.path.join(out_dir, "%(title)s.%(ext)s")
    base["progress_hooks"] = hooks or []

    if fmt_type == "video_hq":
        if FFMPEG_OK:
            base["format"] = "bestvideo+bestaudio/best"
            base["merge_output_format"] = "mp4"
        else:
            base["format"] = "best[ext=mp4]/best[ext=webm]/best"

    elif fmt_type == "video_1080":
        if FFMPEG_OK:
            base["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            base["merge_output_format"] = "mp4"
        else:
            base["format"] = "best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best"

    elif fmt_type == "video_720":
        if FFMPEG_OK:
            base["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            base["merge_output_format"] = "mp4"
        else:
            base["format"] = "best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best"

    elif fmt_type == "video_480":
        if FFMPEG_OK:
            base["format"] = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            base["merge_output_format"] = "mp4"
        else:
            base["format"] = "best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best"

    elif fmt_type == "audio_mp3":
        if not FFMPEG_OK:
            raise RuntimeError("MP3 nécessite ffmpeg. Utilisez M4A à la place.")
        base["format"] = "bestaudio/best"
        base["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"},
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ]
        base["writethumbnail"] = True

    elif fmt_type == "audio_m4a":
        base["format"] = "bestaudio[ext=m4a]/bestaudio/best"

    else:
        base["format"] = "best"

    return base


def get_video_info(url: str) -> dict:
    import yt_dlp
    opts = _base_opts()
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats    = info.get("formats", [])
        max_height = max((f.get("height") or 0 for f in formats), default=0)

        if max_height >= 1440:
            recommended, rec_label = "video_hq",   f"🔥 {max_height}p disponible !"
        elif max_height >= 1080:
            recommended, rec_label = "video_1080", "✨ 1080p disponible"
        elif max_height >= 720:
            recommended, rec_label = "video_720",  "📺 720p disponible"
        else:
            recommended, rec_label = "video_480",  "480p (qualité max)"

        return {
            "title"      : info.get("title", "Unknown"),
            "duration"   : info.get("duration_string", "?"),
            "thumbnail"  : info.get("thumbnail", ""),
            "uploader"   : info.get("uploader", ""),
            "platform"   : detect_platform(url),
            "max_height" : max_height,
            "recommended": recommended,
            "rec_label"  : rec_label,
            "ffmpeg_ok"  : FFMPEG_OK,
        }


def download_video(url: str, fmt_type: str, job_id: str, on_progress=None) -> str:
    import yt_dlp

    job_dir = os.path.join(DOWNLOADS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    hooks = []
    if on_progress:
        def _hook(d):
            s = d.get("status")
            if s == "downloading":
                raw   = strip_ansi(d.get("_percent_str", "0")).strip().rstrip("%")
                speed = strip_ansi(d.get("_speed_str", "—")).strip()
                eta   = strip_ansi(d.get("_eta_str",   "—")).strip()
                try:    pct = float(raw)
                except: pct = 0.0
                on_progress(pct, speed, eta)
            elif s == "finished":
                on_progress(95, "⚙ Conversion…", "~5s")
        hooks.append(_hook)

    opts = build_ydl_opts(fmt_type, job_dir, hooks)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info     = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if fmt_type == "audio_mp3" and FFMPEG_OK:
            filename = os.path.splitext(filename)[0] + ".mp3"

    valid_exts = {".mp4", ".webm", ".mkv", ".mp3", ".m4a", ".opus", ".ogg", ".flv", ".mov"}
    files = [
        f for f in os.listdir(job_dir)
        if not f.startswith(".")
        and os.path.splitext(f)[1].lower() in valid_exts
    ]

    if files:
        priority = [".mp3", ".mp4", ".m4a", ".webm", ".mkv"]
        files.sort(key=lambda f: next(
            (i for i, ext in enumerate(priority) if f.lower().endswith(ext)), 99
        ))
        return os.path.join(job_dir, files[0])

    return filename
