# Architecture

## L'idée de départ

On n'écrit pas de cryptographie et on ne refait pas une messagerie. On part de Matrix, qui a fait ses
preuves, et on y ajoute ce dont une administration a besoin : une identité d'État, des niveaux de
classification et un pouvoir de révocation.

Chaque règle est appliquée là où elle est la plus difficile à contourner. Le chiffrement obligatoire est
imposé par le serveur (module Synapse) et par la configuration, qui chiffre les salons par défaut. La
validité de l'étiquette de classification est contrôlée par le serveur, comme l'expiration des messages
classifiés, que le client masque aussi immédiatement de son côté. L'interdiction de transférer ou de
modifier un message classifié ne peut se faire que dans le client, puisque le serveur ne voit pas le
contenu. L'identité, le second facteur et le rôle « agent » sont gérés par Keycloak, puis revérifiés par
Synapse. La révocation touche Keycloak et Synapse, et c'est la console qui orchestre les deux.

## La connexion

1. Element envoie l'agent vers Synapse (`/login/sso/redirect/oidc-keycloak`).
2. Synapse le redirige vers Keycloak, sur `https://auth.<domaine>`.
3. Keycloak déroule le flux `navigateur-2fa` : matricule et mot de passe, puis code TOTP. Les deux étapes
   sont obligatoires.
4. Keycloak renvoie un jeton d'identité avec le matricule (`preferred_username`) et les rôles
   (`faso_roles`).
5. Synapse vérifie que le rôle `agent` est présent, puis en tire l'identifiant `@<matricule>:<serveur>` et le
   nom affiché.
6. Element reçoit un jeton de connexion à usage unique et ouvre la session.

Synapse trouve Keycloak par son adresse publique en HTTPS. En local, Caddy signe les certificats avec sa
propre autorité, et `synapse/conf/demarrer.sh` ajoute cette autorité à celles qu'approuve Synapse au
démarrage. Avec un vrai domaine, il n'y a rien à changer.

## La classification

L'étiquette ressemble à ça :

```json
"bf.faso.classification": { "niveau": "confidentiel", "duree": 300 }
```

Le client l'ajoute au contenu du message avant de le chiffrer. Elle est donc authentifiée par le
chiffrement, et c'est elle qui sert à l'affichage chez le destinataire.

Le SDK patché en recopie une version en clair dans l'enveloppe chiffrée, exactement comme Matrix le fait
déjà pour `m.relates_to`. Le serveur voit cette étiquette, jamais le texte.

Côté serveur, le module Synapse vérifie l'étiquette à l'envoi (`check_event_for_spam`) et note l'échéance
(`on_new_event`). Toutes les cinq secondes, il rédacte les messages arrivés à échéance au nom de leur
expéditeur. Si l'expéditeur a quitté le salon, un modérateur local du salon prend le relais.

Les échéances sont stockées dans une petite base SQLite sur le volume de Synapse, donc un redémarrage ne
fait sauter aucune expiration.

## La révocation

`./faso revoquer 318264B` appelle l'API interne de la console, qui fait dans l'ordre :

1. un relevé des sessions Keycloak, des appareils et des salons de l'agent, pour le rapport ;
2. la désactivation de son compte Keycloak et la fermeture de toutes ses sessions (Keycloak prévient
   Synapse par une déconnexion « backchannel ») ;
3. la désactivation de son compte Synapse, qui supprime tous ses jetons d'accès et appareils et le fait
   sortir de tous les salons. L'option `erase` reste à faux, si bien que les messages déjà échangés restent
   visibles pour les autres membres ;
4. une ligne dans le journal d'audit de la console (`/data/journal.jsonl`, en ajout seul).

La réintégration réactive les deux comptes. Il faut ensuite réinviter l'agent dans ses salons.

## Le réseau

Seul Caddy ouvre des ports, le 80 et le 443. Les autres services ne sont joignables que sur le réseau
Docker interne. L'API d'administration de Synapse et l'API interne de la console (port 8001) ne sont
jamais exposées.

| `https://faso.localhost/app/#/login` | Element, le client web |
| `https://console.faso.localhost` | console de l'autorité |
