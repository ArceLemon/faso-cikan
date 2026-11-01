"""Le serveur est fermé : ni fédération, ni inscription, ni mot de passe local."""

from outils import MATRIX, client


def test_api_client_disponible():
    with client() as c:
        assert c.get(f"{MATRIX}/_matrix/client/versions").status_code == 200


def test_federation_desactivee():
    with client() as c:
        assert c.get(f"{MATRIX}/_matrix/federation/v1/version").status_code == 404
        assert c.get(f"{MATRIX}/_matrix/key/v2/server").status_code == 404


def test_api_administration_non_exposee():
    with client() as c:
        assert c.get(f"{MATRIX}/_synapse/admin/v1/server_version").status_code == 404


def test_seule_la_connexion_sso_est_proposee():
    with client() as c:
        flux = {f["type"] for f in c.get(f"{MATRIX}/_matrix/client/v3/login").json()["flows"]}
    assert "m.login.sso" in flux
    assert "m.login.password" not in flux


def test_connexion_par_mot_de_passe_refusee():
    with client() as c:
        rep = c.post(
            f"{MATRIX}/_matrix/client/v3/login",
            json={"type": "m.login.password", "identifier": {"type": "m.id.user", "user": "247851k"},
                  "password": "Cikan-Demo-2026"},
        )
    assert rep.status_code in (400, 403)


def test_inscription_publique_fermee():
    with client() as c:
        rep = c.post(f"{MATRIX}/_matrix/client/v3/register", json={"username": "intrus", "password": "x" * 16})
    assert rep.status_code == 403
