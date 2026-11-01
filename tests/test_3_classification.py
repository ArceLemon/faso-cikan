"""Chiffrement imposé et règles de classification appliquées par le serveur."""

import time
from urllib.parse import quote

import pytest

from outils import Agent, faux_message_chiffre


@pytest.fixture(scope="module")
def agent():
    return Agent("900002b")


@pytest.fixture(scope="module")
def salon(agent):
    return agent.creer_salon("Recette classification")


def test_salon_chiffre_par_defaut(agent, salon):
    rep = agent.http.get(f"/rooms/{quote(salon)}/state/m.room.encryption/")
    assert rep.status_code == 200
    assert rep.json()["algorithm"] == "m.megolm.v1.aes-sha2"


def test_message_en_clair_refuse(agent, salon):
    rep = agent.envoyer(salon, "m.room.message", {"msgtype": "m.text", "body": "en clair"})
    assert rep.status_code == 403


def test_message_chiffre_ordinaire_accepte(agent, salon):
    assert agent.envoyer(salon, "m.room.encrypted", faux_message_chiffre()).status_code == 200


@pytest.mark.parametrize(
    "etiquette",
    [
        {"niveau": "confidentiel"},                      # délai obligatoire manquant
        {"niveau": "secret-defense", "duree": 60},       # niveau inconnu
        {"niveau": "confidentiel", "duree": 5},          # délai trop court
        {"niveau": "confidentiel", "duree": 10_000_000}, # délai trop long
        {"niveau": "confidentiel", "duree": "60"},       # délai mal typé
        "confidentiel",                                  # étiquette mal formée
    ],
)
def test_etiquette_invalide_refusee(agent, salon, etiquette):
    assert agent.envoyer(salon, "m.room.encrypted", faux_message_chiffre(etiquette)).status_code == 403


def test_diffusion_restreinte_sans_delai_acceptee(agent, salon):
    rep = agent.envoyer(salon, "m.room.encrypted", faux_message_chiffre({"niveau": "restreint"}))
    assert rep.status_code == 200


def test_message_confidentiel_expire_cote_serveur(agent, salon):
    rep = agent.envoyer(salon, "m.room.encrypted", faux_message_chiffre({"niveau": "confidentiel", "duree": 30}))
    assert rep.status_code == 200
    event_id = rep.json()["event_id"]

    assert agent.evenement(salon, event_id)["content"]["ciphertext"]

    time.sleep(30)
    for _ in range(20):
        ev = agent.evenement(salon, event_id)
        if "redacted_because" in ev.get("unsigned", {}):
            break
        time.sleep(2)

    assert ev["content"] == {}, "le contenu chiffré doit avoir disparu"
    assert ev["unsigned"]["redacted_because"]["content"]["reason"].startswith("Expiration automatique")
