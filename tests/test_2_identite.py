"""Seul un agent enrôlé, avec son mot de passe et son code à usage unique, obtient un accès."""

import pytest

from outils import MATRIX, Agent, ConnexionRefusee, client, connexion_sso, mxid


def test_matricule_non_enrole_rejete():
    with pytest.raises(ConnexionRefusee) as refus:
        connexion_sso("999999z", otp="000000")
    assert refus.value.etape == "mot de passe"
    assert "incorrect" in refus.value.detail


def test_compte_sans_role_agent_rejete_par_synapse():
    # Le compte existe dans Keycloak mais n'a pas le rôle "agent" : Synapse refuse l'accès.
    with pytest.raises(ConnexionRefusee) as refus:
        connexion_sso("900004d")
    assert refus.value.etape == "retour vers Synapse"


# Les essais ratés portent sur le compte 900004d. Keycloak le verrouille une minute
# après deux échecs rapprochés : ces tests passent donc après celui qui l'utilise.


def test_mauvais_mot_de_passe_rejete():
    with pytest.raises(ConnexionRefusee) as refus:
        connexion_sso("900004d", mot_de_passe="pas-le-bon-mot-de-passe")
    assert refus.value.etape == "mot de passe"


def test_mauvais_code_a_usage_unique_rejete():
    with pytest.raises(ConnexionRefusee) as refus:
        connexion_sso("900004d", otp="000000")
    assert refus.value.etape == "code à usage unique"


def test_agent_enrole_connecte_avec_son_matricule():
    agent = Agent("900001a")
    assert agent.user_id == mxid("900001a")

    with client() as c:
        profil = c.get(
            f"{MATRIX}/_matrix/client/v3/profile/{agent.user_id}",
            headers={"Authorization": f"Bearer {agent.jeton}"},
        ).json()
    assert profil["displayname"] == "Agent RECETTE-A"


def test_nom_affiche_non_modifiable():
    agent = Agent("900001a")
    rep = agent.http.put(f"/profile/{agent.user_id}/displayname", json={"displayname": "Usurpateur"})
    assert rep.status_code in (400, 403)
