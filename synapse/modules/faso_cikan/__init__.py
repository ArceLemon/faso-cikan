

import logging
import sqlite3
import time
from typing import Any

from synapse.api.errors import Codes
from synapse.events import EventBase
from synapse.module_api import NOT_SPAM, ModuleApi
from synapse.types import StateMap

from .etiquette import CLE_ETIQUETTE, BornesDuree, valider_etiquette

logger = logging.getLogger(__name__)

# Types de messages qui doivent obligatoirement être chiffrés.
TYPES_A_CHIFFRER = {"m.room.message", "m.sticker"}

# Au-delà, une expiration impossible est abandonnée et signalée dans les journaux.
TENTATIVES_MAX = 20

MOTIF_REDACTION = "Expiration automatique d'un message classifié"


class ModuleFasoCikan:
    def __init__(self, config: dict[str, Any], api: ModuleApi):
        self._api = api
        self._bornes = BornesDuree(config["duree_min_secondes"], config["duree_max_secondes"])
        self._comptes_techniques = set(config["comptes_techniques"])
        self._base = self._ouvrir_base(config["base"])

        api.register_spam_checker_callbacks(check_event_for_spam=self.verifier_evenement)
        api.register_third_party_rules_callbacks(on_new_event=self.enregistrer_evenement)
        api.looping_background_call(
            self.faire_expirer,
            config["intervalle_secondes"] * 1000,
            desc="faso_cikan_expiration",
        )

    @staticmethod
    def parse_config(config: dict[str, Any]) -> dict[str, Any]:
        valeurs = {
            "base": config.get("base", "/data/faso_expirations.sqlite3"),
            "intervalle_secondes": int(config.get("intervalle_secondes", 5)),
            "duree_min_secondes": int(config.get("duree_min_secondes", 30)),
            "duree_max_secondes": int(config.get("duree_max_secondes", 7 * 86400)),
            "comptes_techniques": list(config.get("comptes_techniques", [])),
        }
        if valeurs["duree_min_secondes"] > valeurs["duree_max_secondes"]:
            raise ValueError("duree_min_secondes doit être inférieure à duree_max_secondes")
        return valeurs

    @staticmethod
    def _ouvrir_base(chemin: str) -> sqlite3.Connection:
        base = sqlite3.connect(chemin, check_same_thread=False, isolation_level=None)
        base.execute(
            """
            CREATE TABLE IF NOT EXISTS expirations (
                event_id   TEXT PRIMARY KEY,
                room_id    TEXT NOT NULL,
                expediteur TEXT NOT NULL,
                niveau     TEXT NOT NULL,
                echeance   INTEGER NOT NULL,
                tentatives INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        base.execute("CREATE INDEX IF NOT EXISTS expirations_echeance ON expirations (echeance)")
        return base

    # ------------------------------------------------------------------
    # Contrôle à l'envoi
    # ------------------------------------------------------------------

    async def verifier_evenement(self, event: EventBase) -> Any:
        if event.sender in self._comptes_techniques or event.is_state():
            return NOT_SPAM

        if event.type in TYPES_A_CHIFFRER:
            logger.info("Message en clair refusé : %s dans %s", event.sender, event.room_id)
            return Codes.FORBIDDEN, {"error": "Le chiffrement de bout en bout est obligatoire."}

        etiquette = event.content.get(CLE_ETIQUETTE)
        if etiquette is None:
            return NOT_SPAM

        if event.type != "m.room.encrypted":
            return Codes.FORBIDDEN, {"error": "Seul un message chiffré peut être classifié."}

        erreur = valider_etiquette(etiquette, self._bornes)
        if erreur:
            logger.info("Étiquette refusée pour %s : %s", event.sender, erreur)
            return Codes.FORBIDDEN, {"error": f"Classification invalide : {erreur}."}

        return NOT_SPAM

    # ------------------------------------------------------------------
    # Programmation des expirations
    # ------------------------------------------------------------------

    async def enregistrer_evenement(self, event: EventBase, state: StateMap[EventBase]) -> None:
        if event.type != "m.room.encrypted":
            return
        etiquette = event.content.get(CLE_ETIQUETTE)
        if not isinstance(etiquette, dict) or valider_etiquette(etiquette, self._bornes):
            return
        duree = etiquette.get("duree")
        if duree is None:
            return

        echeance = event.origin_server_ts + duree * 1000
        self._base.execute(
            "INSERT OR IGNORE INTO expirations (event_id, room_id, expediteur, niveau, echeance) "
            "VALUES (?, ?, ?, ?, ?)",
            (event.event_id, event.room_id, event.sender, etiquette["niveau"], echeance),
        )
        logger.info(
            "Expiration programmée : %s (%s) dans %s s",
            event.event_id,
            etiquette["niveau"],
            duree,
        )

    async def faire_expirer(self) -> None:
        maintenant = int(time.time() * 1000)
        echues = self._base.execute(
            "SELECT event_id, room_id, expediteur, tentatives FROM expirations "
            "WHERE echeance <= ? ORDER BY echeance LIMIT 100",
            (maintenant,),
        ).fetchall()

        for event_id, room_id, expediteur, tentatives in echues:
            if await self._rediger(event_id, room_id, expediteur):
                self._base.execute("DELETE FROM expirations WHERE event_id = ?", (event_id,))
                logger.info("Message expiré et rédacté : %s", event_id)
            elif tentatives + 1 >= TENTATIVES_MAX:
                self._base.execute("DELETE FROM expirations WHERE event_id = ?", (event_id,))
                logger.error("Expiration abandonnée après %s tentatives : %s", TENTATIVES_MAX, event_id)
            else:
                self._base.execute(
                    "UPDATE expirations SET tentatives = tentatives + 1 WHERE event_id = ?",
                    (event_id,),
                )

    async def _rediger(self, event_id: str, room_id: str, expediteur: str) -> bool:
        # L'expéditeur peut toujours rédacter son propre message. S'il a quitté le salon
        # (agent révoqué par exemple), un modérateur local du salon prend le relais.
        auteurs = [expediteur] + await self._moderateurs_locaux(room_id, sauf=expediteur)
        for auteur in auteurs:
            try:
                await self._api.create_and_send_event_into_room(
                    {
                        "type": "m.room.redaction",
                        "room_id": room_id,
                        "sender": auteur,
                        "redacts": event_id,
                        "content": {"redacts": event_id, "reason": MOTIF_REDACTION},
                    }
                )
                return True
            except Exception as e:  # noqa: BLE001, on essaie l'auteur suivant
                logger.info("Rédaction de %s par %s impossible : %s", event_id, auteur, e)
        return False

    async def _moderateurs_locaux(self, room_id: str, sauf: str) -> list[str]:
        etat = await self._api.get_room_state(
            room_id, [("m.room.power_levels", ""), ("m.room.member", None)]
        )
        niveaux = etat.get(("m.room.power_levels", ""))
        contenu = niveaux.content if niveaux else {}
        seuil = contenu.get("redact", 50)
        utilisateurs = contenu.get("users", {})
        defaut = contenu.get("users_default", 0)

        candidats = [
            cle
            for (type_, cle), ev in etat.items()
            if type_ == "m.room.member"
            and cle != sauf
            and ev.content.get("membership") == "join"
            and self._api.is_mine(cle)
            and utilisateurs.get(cle, defaut) >= seuil
        ]
        return sorted(candidats, key=lambda u: utilisateurs.get(u, defaut), reverse=True)
