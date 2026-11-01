"""Console web de l'autorité administrative et API interne.

* Interface (port 8000, publiée par Caddy) : connexion par Keycloak, rôle autorite-revocation exigé.
* API interne (port 8001, jamais publiée) : utilisée par la ligne de commande et les tests,
  protégée par un jeton partagé.
"""

import asyncio
import base64
import hashlib
import json
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import REALM, ROLE_AUTORITE, reglages
from .services import Administration, OperationImpossible

ICI = Path(__file__).parent
gabarits = Jinja2Templates(directory=ICI / "templates")


def _administration(request: Request) -> Administration:
    return request.app.state.administration


# L'interface et l'API partagent la même instance (et le même compte technique Synapse).
_partage: dict[str, Administration] = {}
_verrou = asyncio.Lock()


@asynccontextmanager
async def _cycle_de_vie(app: FastAPI):
    async with _verrou:
        if "admin" not in _partage:
            admin = Administration(reglages())
            await admin.synapse.preparer()
            _partage["admin"] = admin
    app.state.administration = _partage["admin"]
    yield


# ---------------------------------------------------------------------------
# Interface web
# ---------------------------------------------------------------------------

interface = FastAPI(lifespan=_cycle_de_vie, docs_url=None, redoc_url=None, openapi_url=None)
interface.add_middleware(
    SessionMiddleware,
    secret_key=reglages().session_secret,
    session_cookie="faso_console",
    same_site="lax",
    https_only=True,
    max_age=3600,
)
interface.mount("/statique", StaticFiles(directory=ICI / "static"), name="statique")


def _url_oidc(chemin: str) -> str:
    return f"{reglages().keycloak_public}/realms/{REALM}/protocol/openid-connect/{chemin}"


def _decoder_jeton(jeton: str) -> dict:
    # Le jeton vient d'être reçu directement de Keycloak par le réseau interne :
    # on lit son contenu sans revérifier la signature.
    charge = jeton.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(charge + "=" * (-len(charge) % 4)))


@interface.get("/sante")
async def sante() -> dict:
    return {"etat": "ok"}


@interface.get("/connexion")
async def connexion(request: Request):
    verificateur = secrets.token_urlsafe(48)
    etat = secrets.token_urlsafe(24)
    request.session["oidc"] = {"etat": etat, "verificateur": verificateur}
    defi = base64.urlsafe_b64encode(hashlib.sha256(verificateur.encode()).digest()).rstrip(b"=").decode()
    params = {
        "client_id": "faso-console",
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": f"{reglages().url_console}/rappel",
        "state": etat,
        "code_challenge": defi,
        "code_challenge_method": "S256",
    }
    return RedirectResponse(_url_oidc("auth") + "?" + urlencode(params))


@interface.get("/rappel")
async def rappel(request: Request, code: str = "", state: str = ""):
    attendu = request.session.pop("oidc", None)
    if not attendu or not secrets.compare_digest(state, attendu["etat"]):
        raise HTTPException(400, "Réponse de connexion inattendue. Recommencez.")

    r = reglages()
    rep = await _administration(request).http.post(
        f"{r.keycloak_interne}/realms/{REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{r.url_console}/rappel",
            "client_id": "faso-console",
            "client_secret": r.oidc_secret,
            "code_verifier": attendu["verificateur"],
        },
    )
    if rep.status_code != 200:
        raise HTTPException(401, "Connexion refusée par le service d'identité.")
    jetons = rep.json()
    contenu = _decoder_jeton(jetons["access_token"])
    request.session["utilisateur"] = {
        "matricule": contenu.get("preferred_username", "").upper(),
        "nom": contenu.get("name", ""),
        "autorite": ROLE_AUTORITE in contenu.get("faso_roles", []),
        "id_token": jetons.get("id_token", ""),
    }
    request.session["csrf"] = secrets.token_urlsafe(32)
    return RedirectResponse("/", status_code=303)


@interface.post("/deconnexion")
async def deconnexion(request: Request):
    utilisateur = request.session.get("utilisateur") or {}
    request.session.clear()
    params = {"post_logout_redirect_uri": f"{reglages().url_console}/", "client_id": "faso-console"}
    if utilisateur.get("id_token"):
        params["id_token_hint"] = utilisateur["id_token"]
    return RedirectResponse(_url_oidc("logout") + "?" + urlencode(params), status_code=303)


def _session(request: Request) -> dict | None:
    return request.session.get("utilisateur")


def _verifier_csrf(request: Request, jeton: str) -> None:
    if not secrets.compare_digest(jeton, request.session.get("csrf", "")):
        raise HTTPException(403, "Formulaire expiré. Rechargez la page.")


async def _page(request: Request, **contexte) -> HTMLResponse:
    utilisateur = _session(request)
    if not utilisateur:
        return gabarits.TemplateResponse(request, "accueil.html", {"domaine": reglages().domaine})
    if not utilisateur["autorite"]:
        return gabarits.TemplateResponse(request, "refuse.html", {"utilisateur": utilisateur}, status_code=403)

    admin = _administration(request)
    agents = await admin.keycloak.lister_agents()
    return gabarits.TemplateResponse(
        request,
        "console.html",
        {
            "utilisateur": utilisateur,
            "agents": agents,
            "journal": admin.journal.derniers(),
            "csrf": request.session["csrf"],
            "actifs": sum(a.actif for a in agents),
            "revoques": sum(not a.actif for a in agents),
            **contexte,
        },
    )


@interface.get("/", response_class=HTMLResponse)
async def accueil(request: Request):
    return await _page(request)


async def _operation(request: Request, csrf: str, action) -> HTMLResponse:
    utilisateur = _session(request)
    if not utilisateur or not utilisateur["autorite"]:
        return RedirectResponse("/", status_code=303)
    _verifier_csrf(request, csrf)
    try:
        resultat = await action(utilisateur["matricule"])
    except OperationImpossible as e:
        return await _page(request, erreur=str(e))
    return await _page(request, **resultat)


@interface.post("/agents/{matricule}/revoquer", response_class=HTMLResponse)
async def revoquer_web(request: Request, matricule: str, csrf: str = Form(...)):
    async def action(auteur):
        return {"rapport": await _administration(request).revoquer(matricule, auteur)}

    return await _operation(request, csrf, action)


@interface.post("/agents/{matricule}/reintegrer", response_class=HTMLResponse)
async def reintegrer_web(request: Request, matricule: str, csrf: str = Form(...)):
    async def action(auteur):
        return {"rapport": await _administration(request).reintegrer(matricule, auteur)}

    return await _operation(request, csrf, action)


@interface.post("/agents", response_class=HTMLResponse)
async def enroler_web(
    request: Request,
    csrf: str = Form(...),
    matricule: str = Form(...),
    prenom: str = Form(...),
    nom: str = Form(...),
    ministere: str = Form(...),
    fonction: str = Form(""),
):
    async def action(auteur):
        rapport, provisoire = await _administration(request).enroler(
            matricule, prenom, nom, ministere, fonction, auteur
        )
        return {"rapport": rapport, "provisoire": provisoire}

    return await _operation(request, csrf, action)


# ---------------------------------------------------------------------------
# API interne
# ---------------------------------------------------------------------------

api = FastAPI(lifespan=_cycle_de_vie, docs_url=None, redoc_url=None, openapi_url=None)


def _jeton_api(authorization: str = Header("")) -> None:
    attendu = f"Bearer {reglages().api_jeton}"
    if not secrets.compare_digest(authorization, attendu):
        raise HTTPException(401, "Jeton invalide")


@api.exception_handler(OperationImpossible)
async def _refus(request: Request, exc: OperationImpossible):
    return JSONResponse({"erreur": str(exc)}, status_code=409)


@api.post("/agents/{matricule}/revoquer", dependencies=[Depends(_jeton_api)])
async def revoquer_api(request: Request, matricule: str, auteur: str = "ligne-de-commande"):
    return await _administration(request).revoquer(matricule, auteur)


@api.post("/agents/{matricule}/reintegrer", dependencies=[Depends(_jeton_api)])
async def reintegrer_api(request: Request, matricule: str, auteur: str = "ligne-de-commande"):
    return await _administration(request).reintegrer(matricule, auteur)


@api.get("/agents", dependencies=[Depends(_jeton_api)])
async def agents_api(request: Request):
    return await _administration(request).keycloak.lister_agents()
