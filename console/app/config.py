import os
from dataclasses import dataclass
from functools import cache

REALM = "fonction-publique"
ROLE_AGENT = "agent"
ROLE_AUTORITE = "autorite-revocation"


@dataclass(frozen=True)
class Reglages:
    domaine: str
    server_name: str
    oidc_secret: str
    session_secret: str
    api_jeton: str
    secret_enregistrement: str
    keycloak_interne: str = "http://keycloak:8080"
    synapse_interne: str = "http://synapse:8008"
    dossier_donnees: str = "/data"

    @property
    def keycloak_public(self) -> str:
        return f"https://auth.{self.domaine}"

    @property
    def url_console(self) -> str:
        return f"https://console.{self.domaine}"

    def mxid(self, matricule: str) -> str:
        return f"@{matricule.lower()}:{self.server_name}"


@cache
def reglages() -> Reglages:
    return Reglages(
        domaine=os.environ["FASO_DOMAINE"],
        server_name=os.environ["FASO_SERVER_NAME"],
        oidc_secret=os.environ["CONSOLE_OIDC_SECRET"],
        session_secret=os.environ["CONSOLE_SESSION_SECRET"],
        api_jeton=os.environ["CONSOLE_API_JETON"],
        secret_enregistrement=os.environ["SYNAPSE_REGISTRATION_SHARED_SECRET"],
    )
