# Faso Cikan

Messagerie instantanée chiffrée pour les agents de l'administration publique burkinabè. Elle est hébergée par l'État, ne dépend d'aucun service tiers et fonctionne entièrement en français. Projet présenté au Hackathon 226, challenge « La messagerie souveraine de l'administration ».

## Le concept

Un agent se connecte avec son matricule de la fonction publique, son mot de passe et un code à usage unique. Son identifiant de messagerie vient du matricule (`@318264b:faso.gov.bf`) : pas de numéro de téléphone, et personne ne s'inscrit seul. Tous les salons sont chiffrés de bout en bout, et le serveur refuse un message en clair.

Un message peut être marqué *Diffusion restreinte* ou *Confidentiel* : il ne peut plus être transféré ni modifié, et il s'efface à l'échéance choisie par l'expéditeur. C'est le serveur qui l'efface, sur tous les appareils, sans l'avoir lu. Quand un agent est muté ou radié, une commande (ou un bouton de la console) ferme ses sessions, déconnecte ses appareils et le fait sortir de ses conversations.

## Architecture

Le navigateur ne parle qu'à Caddy, en HTTPS. Les autres services restent sur un réseau Docker interne.

```
navigateur ── Caddy ──┬── /          page d'accueil
                      ├── /app/      Element Web (chiffre et déchiffre sur l'appareil)
                      ├── matrix.    Synapse + notre module faso_cikan
                      ├── auth.      Keycloak (matricule, code à usage unique, rôles)
                      └── console.   console de l'autorité (FastAPI)
```

Synapse délègue la connexion à Keycloak (OpenID Connect), les deux s'appuient sur PostgreSQL. La console pilote les deux par leurs API d'administration, jamais exposées. Détails dans `docs/ARCHITECTURE.md`, garanties et limites dans `docs/NOTE_SECURITE.md`.

## Technologies et licences

Chiffrement : Matrix (Olm et Megolm) via matrix-js-sdk. Nous n'avons écrit aucune cryptographie.

| Composant | Rôle | Licence |
|---|---|---|
| [Synapse](https://github.com/element-hq/synapse) 1.163.2 | serveur Matrix | AGPL-3.0 |
| [Element Web](https://github.com/element-hq/element-web) 1.12.32 | client web | AGPL-3.0 |
| [matrix-js-sdk](https://github.com/matrix-org/matrix-js-sdk) 44.0.0 | SDK et chiffrement | Apache-2.0 |
| [Keycloak](https://github.com/keycloak/keycloak) 26.7.5 | identité, second facteur, rôles | Apache-2.0 |
| [PostgreSQL](https://www.postgresql.org) 16 | base de données | Licence PostgreSQL |
| [Caddy](https://github.com/caddyserver/caddy) 2.10 | proxy, HTTPS | Apache-2.0 |
| [FastAPI](https://github.com/fastapi/fastapi) | console d'administration | MIT |
| [Docker Compose](https://github.com/docker/compose) | déploiement | Apache-2.0 |

Police Work Sans (SIL OFL 1.1), icônes Phosphor (MIT), logos Simple Icons (CC0).

**Niveau d'engagement : étendre et adapter.** Notre code est dans `element/src/faso/` et `synapse/modules/faso_cikan/`. Dans Element, nous ne modifions que ce qu'il faut pour le brancher (40 lignes sur 10 fichiers, plus 9 lignes dans le SDK). Le projet est sous AGPL-3.0, comme Synapse et Element.

## Installer

Il faut Docker avec Compose v2, les ports 80 et 443 libres et environ 5 Go de mémoire (une dizaine de minutes la première fois).

```
cp .env.example .env              # Windows : copy .env.example .env
docker compose up -d --build      # construit et lance tout
```

Le `.env.example` contient des secrets de démonstration. Pour des secrets tirés au hasard et un domaine personnalisé, lancez plutôt `./faso demarrer` (Linux, WSL 2) ou `.\faso.ps1 demarrer` (Windows). Puis : messagerie sur https://faso.localhost/app/, console sur https://console.faso.localhost, Keycloak sur https://auth.faso.localhost/admin (identifiants dans `.env`). Le certificat est signé par Caddy : acceptez l'avertissement du navigateur.

## Comptes de démonstration

Comptes fictifs, mot de passe `Cikan-Demo-2026`. Le code à usage unique vient de `./faso code MATRICULE` (ou `.\faso.ps1 code MATRICULE`).

| Matricule | Agent | Rôle |
|---|---|---|
| 247851K | Aminata OUÉDRAOGO | agent et autorité de révocation |
| 318264B | Issouf SAWADOGO | agent |
| 402917M | Mariam KABORÉ | agent |

Les six comptes, toutes les adresses et le parcours de démonstration sont dans `ACCES.md`. Révocation : `./faso revoquer 402917M`, puis `./faso reintegrer 402917M`. `./faso tests` lance les 26 tests de bout en bout (une minute d'écart entre deux exécutions : Keycloak bloque brièvement un compte après des échecs répétés).

## Limites

- Un agent révoqué garde les messages déjà reçus sur son appareil.
- La classification est appliquée par le client : un client Matrix modifié peut la contourner.
- Les captures d'écran ne sont pas bloquées, le navigateur ne le permet pas.
- Le code à usage unique ne protège pas d'un hameçonnage en temps réel.
- Le code n'a pas été audité. Avant une vraie mise en service, supprimer `demo/` et les comptes de démonstration.

## Équipe

[Prénom NOM], serveur et sécurité · [Prénom NOM], client

## Licence

AGPL-3.0, texte complet dans `LICENSE`.
