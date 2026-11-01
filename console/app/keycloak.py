"""Accès à l'API d'administration de Keycloak avec le compte de service de la console."""

import time
from dataclasses import dataclass

import httpx

from .config import REALM, ROLE_AGENT, ROLE_AUTORITE, Reglages


@dataclass
class Agent:
    id: str
    matricule: str
    prenom: str
    nom: str
    ministere: str
    fonction: str
    actif: bool
    autorite: bool = False

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom}".strip()

    @classmethod
    def depuis_keycloak(cls, u: dict) -> "Agent":
        attributs = u.get("attributes") or {}
        return cls(
            id=u["id"],
            matricule=u["username"].upper(),
            prenom=u.get("firstName", ""),
            nom=u.get("lastName", ""),
            ministere=(attributs.get("ministere") or [""])[0],
            fonction=(attributs.get("fonction") or [""])[0],
            actif=u.get("enabled", False),
        )


class ErreurKeycloak(Exception):
    pass


class Keycloak:
    def __init__(self, reglages: Reglages, client: httpx.AsyncClient):
        self._r = reglages
        self._http = client
        self._jeton: str | None = None
        self._expire_a = 0.0

    @property
    def _admin(self) -> str:
        return f"{self._r.keycloak_interne}/admin/realms/{REALM}"

    async def _entetes(self) -> dict[str, str]:
        if not self._jeton or time.monotonic() > self._expire_a:
            rep = await self._http.post(
                f"{self._r.keycloak_interne}/realms/{REALM}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": "faso-console",
                    "client_secret": self._r.oidc_secret,
                },
            )
            rep.raise_for_status()
            corps = rep.json()
            self._jeton = corps["access_token"]
            self._expire_a = time.monotonic() + corps.get("expires_in", 60) - 20
        return {"Authorization": f"Bearer {self._jeton}"}

    async def _requete(self, methode: str, chemin: str, **kwargs) -> httpx.Response:
        rep = await self._http.request(methode, self._admin + chemin, headers=await self._entetes(), **kwargs)
        if rep.status_code == 401:
            # Jeton révoqué ou clés du realm renouvelées : on en redemande un.
            self._jeton = None
            rep = await self._http.request(methode, self._admin + chemin, headers=await self._entetes(), **kwargs)
        if rep.status_code >= 400:
            raise ErreurKeycloak(f"{methode} {chemin} : {rep.status_code} {rep.text[:200]}")
        return rep

    async def lister_agents(self) -> list[Agent]:
        rep = await self._requete("GET", "/users", params={"briefRepresentation": "false", "max": 500})
        bruts = [u for u in rep.json() if not u["username"].startswith("service-account-")]
        autorites = await self._membres_du_role(ROLE_AUTORITE)
        agents = []
        for u in bruts:
            agent = Agent.depuis_keycloak(u)
            agent.autorite = u["id"] in autorites
            agents.append(agent)
        return sorted(agents, key=lambda a: (a.ministere, a.nom))

    async def _membres_du_role(self, role: str) -> set[str]:
        rep = await self._requete("GET", f"/roles/{role}/users", params={"max": 500})
        return {u["id"] for u in rep.json()}

    async def chercher(self, matricule: str) -> Agent | None:
        rep = await self._requete(
            "GET", "/users", params={"username": matricule.lower(), "exact": "true", "briefRepresentation": "false"}
        )
        trouves = rep.json()
        return Agent.depuis_keycloak(trouves[0]) if trouves else None

    async def sessions_actives(self, agent: Agent) -> int:
        rep = await self._requete("GET", f"/users/{agent.id}/sessions")
        return len(rep.json())

    async def desactiver(self, agent: Agent) -> None:
        await self._requete("PUT", f"/users/{agent.id}", json={"enabled": False})
        # Ferme toutes les sessions ; Keycloak prévient Synapse par déconnexion « backchannel ».
        await self._requete("POST", f"/users/{agent.id}/logout")

    async def activer(self, agent: Agent) -> None:
        await self._requete("PUT", f"/users/{agent.id}", json={"enabled": True})

    async def creer(self, matricule: str, prenom: str, nom: str, ministere: str, fonction: str, mot_de_passe: str) -> Agent:
        await self._requete(
            "POST",
            "/users",
            json={
                "username": matricule.lower(),
                "enabled": True,
                "firstName": prenom,
                "lastName": nom,
                "attributes": {"ministere": [ministere], "fonction": [fonction]},
                # Première connexion : nouveau mot de passe puis enrôlement du téléphone.
                "requiredActions": ["UPDATE_PASSWORD", "CONFIGURE_TOTP"],
                "credentials": [{"type": "password", "value": mot_de_passe, "temporary": True}],
            },
        )
        agent = await self.chercher(matricule)
        if agent is None:
            raise ErreurKeycloak("Agent introuvable juste après sa création")
        role = (await self._requete("GET", f"/roles/{ROLE_AGENT}")).json()
        await self._requete("POST", f"/users/{agent.id}/role-mappings/realm", json=[role])
        return agent
