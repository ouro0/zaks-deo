# limiter.py — Zak's Deo Download
# © 2024 Zak. Tous droits réservés.
#
# Pas de limite. Pas de plan payant.
# Tout le monde télécharge librement.

def check_limit(user_id=None, fmt: str = ""):
    """Aucune restriction — tout est gratuit."""
    pass

def increment_count(user_id=None):
    """Pas de compteur nécessaire."""
    pass

def get_remaining(user_id=None) -> dict:
    return {"used": 0, "limit": 999, "remaining": 999, "plan": "gratuit"}
