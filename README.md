# Zak's Deo Download v3 🎬
**© 2024 Zak. Tous droits réservés.**

Téléchargeur vidéo/audio gratuit — YouTube, TikTok, Instagram, Facebook.
Sans compte. Sans limite. Sans pub.

---

## ▶️ Lancement (3 étapes)

```bash
# 1. Ouvrir un terminal dans ce dossier

# 2. Installer / mettre à jour les dépendances
pip install -r requirements.txt
pip install -U yt-dlp          ← IMPORTANT : toujours avoir la dernière version

# 3. Lancer le serveur
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Puis ouvrir **http://localhost:8000** dans votre navigateur.

> ⚠️ N'ouvrez PAS index.html directement. Passez par http://localhost:8000

---

## Optionnel mais recommandé : ffmpeg (vidéo HD + MP3)

- Windows : https://ffmpeg.org/download.html
- Mac     : `brew install ffmpeg`
- Linux   : `sudo apt install ffmpeg`

Sans ffmpeg : 480p et M4A fonctionnent quand même.

---

## ✅ Résoudre "Sign in to confirm you're not a bot"

### Solution 1 : Mettre à jour yt-dlp (à faire en premier)
```bash
pip install -U yt-dlp
```

### Solution 2 : Fournir vos cookies YouTube (recommandé)
1. Installez l'extension Chrome/Firefox **"Get cookies.txt LOCALLY"**
2. Connectez-vous à YouTube dans votre navigateur
3. Sur youtube.com, cliquez sur l'extension et exportez les cookies
4. Renommez le fichier `cookies.txt` et placez-le dans ce dossier
5. Relancez le serveur — les cookies sont détectés automatiquement ✓

---

## 🆕 Nouveautés v3

- **🌙 Mode sombre / clair** — toggle en haut à droite, persisté en session
- **💡 Recommandation format automatique** — détecte si la vidéo est en 4K ou 1080p et propose le bon format
- **📋 File d'attente multi-liens** — collez plusieurs URLs d'un coup, elles sont traitées en parallèle avec un compteur
- **🕘 Historique de session** — vos 10 derniers téléchargements avec bouton re-télécharger
- **🛡 Anti-bot amélioré** — clients `mweb` et `android` ajoutés, retry automatique
- **🔍 Logs d'erreur complets** — plus de message tronqué, erreur complète dans le terminal

---

## Fichiers

```
main.py          ← serveur FastAPI (lancer celui-là)
database.py      ← SQLite
downloader.py    ← logique yt-dlp (anti-bot amélioré)
worker.py        ← thread de téléchargement (logs complets)
limiter.py       ← (pas de limite — tout gratuit)
utils.py         ← nettoyage auto des fichiers
requirements.txt
index.html       ← page unique (tabs, multi, historique)
style.css        ← thème dark/light
app.js           ← logique front complète
cookies.txt      ← (optionnel) vos cookies YouTube
downloads/       ← fichiers temporaires (auto-créé)
```
