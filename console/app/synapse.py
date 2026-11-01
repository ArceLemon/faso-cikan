"""Accès à l'API d'administration de Synapse, joignable uniquement depuis le réseau interne."""

import hashlib
import hmac
import logging
import secrets
from pathlib import Path
from urllib.parse import quote

import httpx

from .config import Reglages

logger = logging.getLogger(__name__)

COMPTE_TECHNIQUE = "systeme.console"


class ErreurSynapse(Exception):
    pass


class Synapse:
    def __init__(self, reglages: Reglages, client: httpx.AsyncClient):
        self._r = reglages
        self._http = client
        self._fichier_jeton = Path(reglages.dossier_donnees) / "jeton_synapse"
        self._jeton: str | None = None

    async def preparer(self) -> None:
        """Crée au besoin le compte technique administrateur et conserve son jeton."""
        if self._fichier_jeton.exists():
            self._jeton = self._fichier_jeton.read_text().strip()
            return

        base = f"{self._r.synapse_interne}/_synapse/admin/v1/register"
        nonce = (await self._http.get(base)).json()["nonce"]
        mot_de_passe = secrets.token_urlsafe(32)
        mac = hmac.new(
            self._r.secret_enregistrement.encode(),
            b"\x00".join([nonce.encode(), COMPTE_TECHNIQUE.encode(), mot_de_passe.encode(), b"admin"]),
            hashlib.sha1,
        ).hexdigest()
        rep = await self._http.post(
            base,
            json={
                "nonce": nonce,
                "username": COMPTE_TECHNIQUE,
                "displayname": "Console d'administration",
                "password": mot_de_passe,
                "admin": True,
                "mac": mac,
            },
        )
        if rep.status_code != 200:
            raise ErreurSynapse(f"Création du compte technique impossible : {rep.text}")
        self._jeton = rep.json()["access_token"]
        self._fichier_jeton.write_text(self._jeton)
        self._fichier_jeton.chmod(0o600)
        logger.info("Compte technique Synapse créé")

    async def _requete(self, methode: str, chemin: str, **kwargs) -> httpx.Response:
        if self._jeton is None:
            await self.preparer()
        return await self._http.request(
            methode,
            f"{self._r.synapse_interne}/_synapse/admin{chemin}",
            headers={"Authorization": f"Bearer {self._jeton}"},
            **kwargs,
        )

    async def compte(self, mxid: str) -> dict | None:
        rep = await self._requete("GET", f"/v2/users/{quote(mxid)}")
        if rep.status_code == 404:
            return None
        rep.raise_for_status()
        return rep.json()

    async def salons(self, mxid: str) -> list[str]:
        rep = await self._requete("GET", f"/v1/users/{quote(mxid)}/joined_rooms")
        return rep.json().get("joined_rooms", []) if rep.status_code == 200 else []

    async def appareils(self, mxid: str) -> list[dict]:
        rep = await self._requete("GET", f"/v2/users/{quote(mxid)}/devices")
        return rep.json().get("devices", []) if rep.status_code == 200 else []

    async def desactiver(self, mxid: str) -> None:
        # Supprime tous les jetons et appareils et fait quitter tous les salons.
        # erase=False : les messages déjà échangés restent dans les conversations.
        rep = await self._requete("POST", f"/v1/deactivate/{quote(mxid)}", json={"erase": False})
        if rep.status_code != 200:
            raise ErreurSynapse(f"Désactivation de {mxid} impossible : {rep.text}")

    async def reactiver(self, mxid: str) -> None:
        rep = await self._requete("PUT", f"/v2/users/{quote(mxid)}", json={"deactivated": False})
        if rep.status_code not in (200, 201):
            raise ErreurSynapse(f"Réactivation de {mxid} impossible : {rep.text}")
