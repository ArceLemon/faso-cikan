"""Outils communs aux tests de bout en bout.

Les tests passent par les vraies adresses publiques (Caddy, TLS) et rejouent
le parcours d'un navigateur : page Keycloak, mot de passe, code à usage unique,
retour vers Synapse.
"""

import hashlib
import hmac
import html
import json
import os
import re
import struct
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, quote, urljoin, urlparse

import httpx

DOMAINE = os.environ["FASO_DOMAINE"]
SERVER_NAME = os.environ["FASO_SERVER_NAME"]
MATRIX = f"https://matrix.{DOMAINE}"
ELEMENT = f"https://{DOMAINE}/"
CA = "/caddy/caddy/pki/authorities/local/root.crt"
CONSOLE_API = "http://console:8001"
MOT_DE_PASSE_DEMO = "Cikan-Demo-2026"

SECRETS_OTP = json.loads(Path("/demo/secrets-otp.json").read_text())

_derniers_pas: dict[str, int] = {}


class ConnexionRefusee(Exception):
    def __init__(self, etape: str, detail: str):
        super().__init__(f"{etape} : {detail}")
        self.etape = etape
        self.detail = detail


def client() -> httpx.Client:
    return httpx.Client(verify=CA, timeout=20, follow_redirects=False)


def mxid(matricule: str) -> str:
    return f"@{matricule.lower()}:{SERVER_NAME}"


def code_otp(matricule: str) -> str:
    """Code TOTP courant. Keycloak refuse un code déjà utilisé : on attend le pas suivant si besoin."""
    cle = SECRETS_OTP[matricule.lower()].encode()
    pas = int(time.time()) // 30
    if _derniers_pas.get(matricule) == pas:
        time.sleep(30 - time.time() % 30 + 0.5)
        pas = int(time.time()) // 30
    _derniers_pas[matricule] = pas
    h = hmac.new(cle, struct.pack(">Q", pas), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def _action_formulaire(page: str, identifiant: str) -> str | None:
    m = re.search(rf'<form[^>]*id="{identifiant}"[^>]*action="([^"]+)"', page) or re.search(
        rf'<form[^>]*action="([^"]+)"[^>]*id="{identifiant}"', page
    )
    return html.unescape(m.group(1)) if m else None


def _message_erreur(page: str) -> str:
    # Message général (bandeau) ou message attaché à un champ du formulaire
    m = re.search(r'class="faso-alerte[^"]*"[^>]*>\s*(.*?)\s*</div>', page, re.S) or re.search(
        r'id="input-error[^"]*".*?kc-feedback-text">\s*(.*?)\s*</span>', page, re.S
    )
    return html.unescape(m.group(1)).strip() if m else page[:300]


def _suivre(c: httpx.Client, rep: httpx.Response, arret: str) -> httpx.Response:
    """Suit les redirections jusqu'à atteindre une adresse qui commence par `arret`."""
    for _ in range(10):
        if rep.status_code not in (301, 302, 303, 307):
            return rep
        cible = urljoin(str(rep.url), rep.headers["location"])
        if cible.startswith(arret):
            return rep
        rep = c.get(cible)
    raise RuntimeError("Trop de redirections")


def connexion_sso(matricule: str, mot_de_passe: str = MOT_DE_PASSE_DEMO, otp: str | None = None) -> dict:
    """Parcours complet de connexion. Renvoie la réponse de /login (access_token, user_id, device_id)."""
    with client() as c:
        rep = c.get(
            f"{MATRIX}/_matrix/client/v3/login/sso/redirect/oidc-keycloak",
            params={"redirectUrl": ELEMENT},
        )
        page = _suivre(c, rep, ELEMENT)
        action = _action_formulaire(page.text, "kc-form-login")
        if not action:
            raise ConnexionRefusee("page de connexion", page.text[:300])

        rep = c.post(action, data={"username": matricule, "password": mot_de_passe, "credentialId": ""})
        action = _action_formulaire(rep.text, "kc-otp-login-form")
        if not action:
            raise ConnexionRefusee("mot de passe", _message_erreur(rep.text))

        rep = c.post(action, data={"otp": otp or code_otp(matricule)})
        if rep.status_code == 200:
            raise ConnexionRefusee("code à usage unique", _message_erreur(rep.text))

        rep = _suivre(c, rep, ELEMENT)
        cible = rep.headers.get("location", "")
        jeton = parse_qs(urlparse(cible).query).get("loginToken", [None])[0]
        if not jeton:
            raise ConnexionRefusee("retour vers Synapse", f"{rep.status_code} {rep.text[:300]}")

        rep = c.post(f"{MATRIX}/_matrix/client/v3/login", json={"type": "m.login.token", "token": jeton})
        rep.raise_for_status()
        return rep.json()


class Agent:
    """Session Matrix d'un agent connecté."""

    def __init__(self, matricule: str):
        self.matricule = matricule
        session = connexion_sso(matricule)
        self.user_id = session["user_id"]
        self.jeton = session["access_token"]
        self.http = httpx.Client(
            base_url=f"{MATRIX}/_matrix/client/v3",
            verify=CA,
            timeout=20,
            headers={"Authorization": f"Bearer {self.jeton}"},
        )

    def creer_salon(self, nom: str, invites: list[str] = ()) -> str:
        rep = self.http.post("/createRoom", json={"name": nom, "preset": "private_chat", "invite": list(invites)})
        rep.raise_for_status()
        return rep.json()["room_id"]

    def rejoindre(self, room_id: str) -> None:
        self.http.post(f"/join/{quote(room_id)}", json={}).raise_for_status()

    def envoyer(self, room_id: str, type_: str, contenu: dict) -> httpx.Response:
        return self.http.put(f"/rooms/{quote(room_id)}/send/{type_}/{uuid.uuid4().hex}", json=contenu)

    def evenement(self, room_id: str, event_id: str) -> dict:
        rep = self.http.get(f"/rooms/{quote(room_id)}/event/{quote(event_id)}")
        rep.raise_for_status()
        return rep.json()

    def membres(self, room_id: str) -> dict[str, str]:
        rep = self.http.get(f"/rooms/{quote(room_id)}/members")
        rep.raise_for_status()
        return {e["state_key"]: e["content"]["membership"] for e in rep.json()["chunk"]}


def faux_message_chiffre(etiquette: dict | None = None) -> dict:
    """Message chiffré factice : le serveur ne peut pas lire le contenu, il ne voit que l'enveloppe."""
    contenu = {
        "algorithm": "m.megolm.v1.aes-sha2",
        "ciphertext": "AwgAEnB5bWJvbGlxdWUtZXQtaWxsaXNpYmxl",
        "sender_key": "recette",
        "session_id": "recette",
        "device_id": "RECETTE",
    }
    if etiquette is not None:
        contenu["bf.faso.classification"] = etiquette
    return contenu


def console(operation: str, matricule: str) -> httpx.Response:
    return httpx.post(
        f"{CONSOLE_API}/agents/{matricule}/{operation}",
        params={"auteur": "tests-automatises"},
        headers={"Authorization": f"Bearer {os.environ['CONSOLE_API_JETON']}"},
        timeout=30,
    )
