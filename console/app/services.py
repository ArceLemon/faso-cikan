"""Opérations de l'autorité administrative : révoquer, réintégrer, enrôler.

Chaque opération est inscrite dans un journal d'audit en ajout seul.
"""

import json
import re
import secrets
import string
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .config import Reglages
from .keycloak import Agent, Keycloak
from .synapse import Synapse

MOTIF_MATRICULE = re.compile(r"^[0-9]{6,8}[A-Za-z]$")


class OperationImpossible(Exception):
    pass


@dataclass
class Rapport:
    operation: str
    matricule: str
    agent: str
    auteur: str
    horodatage: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    sessions_fermees: int = 0
    appareils_deconnectes: int = 0
    salons_quittes: int = 0
    details: str = ""


class Journal:
    def __init__(self, dossier: str):
        self._chemin = Path(dossier) / "journal.jsonl"

    def ecrire(self, rapport: Rapport) -> None:
        with self._chemin.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rapport), ensure_ascii=False) + "\n")

    def derniers(self, nombre: int = 30) -> list[Rapport]:
        if not self._chemin.exists():
            return []
        lignes = self._chemin.read_text(encoding="utf-8").splitlines()[-nombre:]
        return [Rapport(**json.loads(l)) for l in reversed(lignes) if l.strip()]


class Administration:
    def __init__(self, reglages: Reglages):
        self.r = reglages
        self.http = httpx.AsyncClient(timeout=15)
        self.keycloak = Keycloak(reglages, self.http)
        self.synapse = Synapse(reglages, self.http)
        self.journal = Journal(reglages.dossier_donnees)

    async def fermer(self) -> None:
        await self.http.aclose()

    async def _agent(self, matricule: str) -> Agent:
        matricule = matricule.strip()
        if not MOTIF_MATRICULE.match(matricule):
            raise OperationImpossible(f"« {matricule} » n'est pas un matricule valide.")
        agent = await self.keycloak.chercher(matricule)
        if agent is None:
            raise OperationImpossible(f"Aucun agent enrôlé sous le matricule {matricule.upper()}.")
        return agent

    async def revoquer(self, matricule: str, auteur: str) -> Rapport:
        agent = await self._agent(matricule)
        mxid = self.r.mxid(agent.matricule)

        sessions = await self.keycloak.sessions_actives(agent)
        appareils = await self.synapse.appareils(mxid)
        salons = await self.synapse.salons(mxid)

        # 1. Plus aucune nouvelle connexion possible
        await self.keycloak.desactiver(agent)
        # 2. Tous les appareils déconnectés, sortie de tous les salons
        compte = await self.synapse.compte(mxid)
        if compte and not compte.get("deactivated"):
            await self.synapse.desactiver(mxid)

        rapport = Rapport(
            operation="revocation",
            matricule=agent.matricule,
            agent=agent.nom_complet,
            auteur=auteur,
            sessions_fermees=sessions,
            appareils_deconnectes=len(appareils),
            salons_quittes=len(salons),
            details="" if compte else "Aucun compte de messagerie encore créé.",
        )
        self.journal.ecrire(rapport)
        return rapport

    async def reintegrer(self, matricule: str, auteur: str) -> Rapport:
        agent = await self._agent(matricule)
        mxid = self.r.mxid(agent.matricule)

        await self.keycloak.activer(agent)
        compte = await self.synapse.compte(mxid)
        if compte and compte.get("deactivated"):
            await self.synapse.reactiver(mxid)

        rapport = Rapport(
            operation="reintegration",
            matricule=agent.matricule,
            agent=agent.nom_complet,
            auteur=auteur,
            details="Les salons doivent être rejoints à nouveau sur invitation.",
        )
        self.journal.ecrire(rapport)
        return rapport

    async def enroler(
        self, matricule: str, prenom: str, nom: str, ministere: str, fonction: str, auteur: str
    ) -> tuple[Rapport, str]:
        matricule = matricule.strip()
        if not MOTIF_MATRICULE.match(matricule):
            raise OperationImpossible(f"« {matricule} » n'est pas un matricule valide.")
        if await self.keycloak.chercher(matricule):
            raise OperationImpossible(f"Le matricule {matricule.upper()} est déjà enrôlé.")
        if not (prenom.strip() and nom.strip() and ministere.strip()):
            raise OperationImpossible("Le prénom, le nom et le ministère sont obligatoires.")

        provisoire = _mot_de_passe_provisoire()
        agent = await self.keycloak.creer(
            matricule, prenom.strip(), nom.strip().upper(), ministere.strip(), fonction.strip(), provisoire
        )
        rapport = Rapport(
            operation="enrolement",
            matricule=agent.matricule,
            agent=agent.nom_complet,
            auteur=auteur,
            details="Mot de passe provisoire remis à l'agent ; second facteur à activer à la première connexion.",
        )
        self.journal.ecrire(rapport)
        return rapport, provisoire


def _mot_de_passe_provisoire() -> str:
    # Lisible à la dictée : pas de 0/O ni de 1/l/I
    alphabet = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
    groupes = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "-".join(groupes)
