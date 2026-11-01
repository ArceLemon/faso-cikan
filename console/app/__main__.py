"""Point d'entrée de la console.

    python -m app                       lance l'interface (8000) et l'API interne (8001)
    python -m app revoquer 318264B      révoque un agent
    python -m app reintegrer 318264B    réintègre un agent
    python -m app agents                liste les agents enrôlés
"""

import asyncio
import os
import sys

import httpx
import uvicorn


async def _servir() -> None:
    from .web import api, interface

    serveurs = [
        uvicorn.Server(uvicorn.Config(interface, host="0.0.0.0", port=8000, proxy_headers=True,
                                      forwarded_allow_ips="*", log_level="info")),
        uvicorn.Server(uvicorn.Config(api, host="0.0.0.0", port=8001, log_level="info")),
    ]
    await asyncio.gather(*(s.serve() for s in serveurs))


def _commande(args: list[str]) -> int:
    entetes = {"Authorization": f"Bearer {os.environ['CONSOLE_API_JETON']}"}
    base = "http://127.0.0.1:8001"
    commande = args[0]

    with httpx.Client(timeout=30, headers=entetes) as client:
        if commande == "agents":
            rep = client.get(f"{base}/agents")
            rep.raise_for_status()
            print(f"{'MATRICULE':<11} {'ÉTAT':<9} {'AGENT':<26} MINISTÈRE")
            for a in rep.json():
                etat = "actif" if a["actif"] else "révoqué"
                print(f"{a['matricule']:<11} {etat:<9} {a['prenom'] + ' ' + a['nom']:<26} {a['ministere']}")
            return 0

        if commande in ("revoquer", "reintegrer") and len(args) == 2:
            rep = client.post(f"{base}/agents/{args[1]}/{commande}")
            corps = rep.json()
            if rep.status_code != 200:
                print(f"Refusé : {corps.get('erreur', corps)}", file=sys.stderr)
                return 1
            if commande == "revoquer":
                print(f"Agent {corps['matricule']} ({corps['agent']}) révoqué.")
                print(f"  sessions d'identité fermées : {corps['sessions_fermees']}")
                print(f"  appareils déconnectés       : {corps['appareils_deconnectes']}")
                print(f"  salons quittés              : {corps['salons_quittes']}")
            else:
                print(f"Agent {corps['matricule']} ({corps['agent']}) réintégré.")
            if corps.get("details"):
                print(f"  {corps['details']}")
            return 0

    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(_commande(sys.argv[1:]))
    asyncio.run(_servir())
