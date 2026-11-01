"""Révocation centralisée : une commande coupe l'accès sur tous les appareils."""

import time

import pytest

from outils import Agent, ConnexionRefusee, connexion_sso, console


@pytest.fixture
def b_toujours_reintegre():
    yield
    console("reintegrer", "900003c")


def test_revocation_en_cours_de_conversation(b_toujours_reintegre):
    a = Agent("900001a")
    b = Agent("900003c")
    salon = a.creer_salon("Recette révocation", invites=[b.user_id])
    b.rejoindre(salon)
    assert a.membres(salon)[b.user_id] == "join"
    assert b.http.get("/account/whoami").status_code == 200

    rep = console("revoquer", "900003c")
    assert rep.status_code == 200, rep.text
    rapport = rep.json()
    assert rapport["appareils_deconnectes"] >= 1
    assert rapport["salons_quittes"] >= 1

    # Le jeton de B ne vaut plus rien
    rep = b.http.get("/account/whoami")
    assert rep.status_code == 401
    assert rep.json()["errcode"] == "M_UNKNOWN_TOKEN"

    # B a quitté la conversation (Synapse traite la sortie des salons en tâche de fond)
    for _ in range(20):
        if a.membres(salon)[b.user_id] == "leave":
            break
        time.sleep(0.5)
    assert a.membres(salon)[b.user_id] == "leave"

    # B ne peut plus se reconnecter
    with pytest.raises(ConnexionRefusee) as refus:
        connexion_sso("900003c")
    assert "désactivé" in refus.value.detail


def test_reintegration_retablit_l_acces():
    assert console("revoquer", "900003c").status_code == 200
    assert console("reintegrer", "900003c").status_code == 200
    b = Agent("900003c")
    assert b.http.get("/account/whoami").status_code == 200


def test_matricule_inconnu_refuse_par_la_console():
    rep = console("revoquer", "999999z")
    assert rep.status_code == 409
    assert "Aucun agent" in rep.json()["erreur"]
