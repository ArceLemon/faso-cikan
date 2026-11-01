# Faso Cikan : accès et comptes de démonstration

Cette page rassemble tout ce qu'il faut pour se connecter et tester. Le concept, l'architecture et les licences sont dans le `README.md`.

## 1. Lancer

```
copy .env.example .env            (Linux ou WSL : cp .env.example .env)
docker compose up -d --build
```

La première construction prend une dizaine de minutes. Il faut Docker avec Compose v2, les ports 80 et 443 libres, et environ 8 Go de mémoire alloués à Docker. Pour vérifier que tout est prêt :

```
docker compose ps
```

Les services `console`, `element`, `keycloak`, `postgres` et `synapse` doivent être `healthy` (Caddy affiche seulement `running`).

## 2. Les adresses

| Adresse | Ce que c'est |
|---|---|
| https://faso.localhost | page d'accueil |
| https://faso.localhost/app/ | la messagerie |
| https://console.faso.localhost | console de l'autorité (enrôler, révoquer, réintégrer) |
| https://auth.faso.localhost/admin | administration de Keycloak |

Le certificat est signé par l'autorité locale de Caddy : le navigateur affiche un avertissement. Cliquez sur « Avancé », puis « Continuer ».

## 3. Comptes de démonstration

Comptes fictifs. Mot de passe de tous : `Cikan-Demo-2026`.

| Matricule | Agent | Ministère | Rôle |
|---|---|---|---|
| 247851K | Aminata OUÉDRAOGO | Fonction publique | agent et **autorité** (accès à la console) |
| 318264B | Issouf SAWADOGO | Économie et Finances | agent |
| 402917M | Mariam KABORÉ | Santé | agent |
| 155380T | Boukary ZONGO | Administration territoriale | agent |
| 511734S | Salif COMPAORÉ | Éducation nationale | agent |
| 286045A | Awa TRAORÉ | Direction générale du Trésor | agent |

Seul `247851K` peut ouvrir la console. Les comptes `900001A` à `900004D` sont réservés aux tests automatisés.

## 4. Le code à usage unique

Chaque connexion demande, après le mot de passe, un code à six chiffres qui change toutes les 30 secondes et ne sert qu'une fois. Pour les comptes de démonstration, il se génère avec :

```
code.cmd 318264B                  (Linux ou WSL : ./faso code 318264B)
```

La commande affiche le code du moment et le temps pendant lequel il reste valable. Elle donne aussi la clé à saisir dans une application d'authentification (Aegis, FreeOTP, Google Authenticator) si vous préférez votre téléphone.

## 5. Administration de Keycloak

L'identifiant et le mot de passe sont dans le fichier `.env`, aux lignes `KEYCLOAK_ADMIN` et `KEYCLOAK_ADMIN_PASSWORD`. Avec le `.env.example` fourni, ce sont `admin-faso` et `demo-admin-a-remplacer`.

## 6. Parcours de démonstration

1. Ouvrez https://faso.localhost/app/ et connectez `318264B`. Dans une fenêtre de navigation privée, connectez `402917M`.
2. `318264B` crée un salon et invite `402917M`, qui accepte l'invitation.
3. Ils s'écrivent dans les deux sens.
4. `318264B` choisit **Confidentiel**, un effacement après 30 secondes, puis envoie un message. Chez `402917M`, il s'affiche dans un cadre rouge avec un compte à rebours, et le menu ne propose ni « Transférer » ni « Modifier ». À l'échéance, il disparaît.
5. Révocation, au choix :
   - dans la console, connecté en `247851K`, bouton **Révoquer** sur `402917M` ;
   - ou en ligne de commande : `faso.cmd revoquer 402917M` (Linux ou WSL : `./faso revoquer 402917M`).

   La session de `402917M` se ferme, il sort du salon et ne peut plus se reconnecter.
6. `faso.cmd reintegrer 402917M` lui rend l'accès. Il faut ensuite l'inviter de nouveau dans le salon.
7. Pour tester un intrus, tentez de vous connecter avec un matricule inconnu, par exemple `999999Z` : il est rejeté.

## 7. Voir que le serveur ne lit rien

Cette commande affiche les derniers messages tels que la base de Synapse les contient :

```
docker compose exec postgres psql -U synapse -d synapse -c "select e.type, left(j.json, 160) from events e join event_json j using (event_id) where e.type = 'm.room.encrypted' order by e.stream_ordering desc limit 2;"
```

On y voit du texte chiffré, jamais le contenu des messages. Cette autre commande doit afficher `0`, car aucun message n'est stocké en clair :

```
docker compose exec postgres psql -U synapse -d synapse -tc "select count(*) from events where type = 'm.room.message';"
```

## 8. Commandes utiles

| Commande | Effet |
|---|---|
| `docker compose ps` | état des services |
| `docker compose logs -f --tail 100 synapse` | suivre les journaux d'un service |
| `docker compose stop` | arrêter, les données sont conservées |
| `docker compose up -d` | reprendre |
| `faso.cmd tests` (ou `./faso tests`) | lancer les 26 tests de bout en bout |
| `faso.cmd agents` (ou `./faso agents`) | liste des agents enrôlés |

Attention : `docker compose down -v` supprime toutes les données (messages, comptes, journal).

## 9. En cas de problème

| Problème | Solution |
|---|---|
| `failed to connect to the docker API` | Docker Desktop n'est pas lancé : attendez que son icône soit verte |
| La construction d'Element échoue (« cannot allocate memory ») | Donnez au moins 8 Go à Docker (*Settings*, puis *Resources*) |
| « L'exécution de scripts est désactivée » | Utilisez `faso.cmd` au lieu de `faso.ps1` |
| « Code incorrect ou expiré » | Le code dure 30 secondes et ne sert qu'une fois : générez-en un nouveau |
| Compte bloqué | Keycloak bloque un compte une minute après deux échecs rapprochés : patientez |
| Element demande de vérifier l'appareil | Choisissez « Confirmation impossible ? », puis « Je ferai la vérification plus tard ». N'acceptez pas de réinitialiser l'identité numérique. |
| Une page ne s'ouvre pas | Vérifiez `docker compose ps` : tout doit être `healthy` |
