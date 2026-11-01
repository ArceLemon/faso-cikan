Faso Cikan
Une messagerie instantanée chiffrée pour les agents de l'administration publique burkinabè. Elle est hébergée par l'État, ne dépend d'aucun service tiers et fonctionne entièrement en français.
Projet présenté au Hackathon 226, challenge « La messagerie souveraine de l'administration ».
En bref
Un agent se connecte avec son matricule de la fonction publique, son mot de passe et un code à usage unique. Son identifiant de messagerie est tiré du matricule (@247851k:faso.gov.bf) : pas de numéro de téléphone, et personne ne peut s'inscrire seul.
Tous les salons sont chiffrés de bout en bout (Matrix, avec Olm et Megolm). Si un message arrive en clair, le serveur le refuse.
Un message peut être marqué Diffusion restreinte ou Confidentiel. Dans ce cas il ne peut plus être transféré ni modifié, et il s'efface à l'échéance fixée par l'expéditeur. C'est le serveur qui fait l'effacement, sur tous les appareils, sans jamais lire le message.
Enfin, quand un agent est muté ou radié, une commande (ou un bouton dans la console) lui coupe l'accès : ses sessions sont fermées, ses appareils déconnectés et il sort de toutes ses conversations.
Lancer le projet
Il faut Docker avec Compose v2, sous Linux ou WSL 2, et les ports 80 et 443 libres. Comptez une dizaine de minutes et environ 5 Go de mémoire pour la première construction du client web.
./faso demarrer      # crée le .env au premier lancement, construit et lance tout
./faso certificat    # fait approuver le certificat local par Windows ou le navigateur
Ensuite :
•	la page d'accueil est sur https://faso.localhost
•	la messagerie sur https://faso.localhost/app/
•	la console de l'autorité sur https://console.faso.localhost
•	l'administration Keycloak sur https://auth.faso.localhost/admin (identifiants dans .env)
Passez toujours par ./faso demarrer plutôt que docker compose up : le script génère la configuration du client à partir du .env.
Comptes pour tester
Tous les comptes ont le mot de passe Cikan-Demo-2026. Pour le code à usage unique, ./faso code MATRICULE donne le code du moment, ainsi que la clé à ajouter dans Aegis, FreeOTP ou une autre application d'authentification.
Matricule	Agent	Rôle
247851K	Aminata OUÉDRAOGO, Fonction publique	agent, autorité de révocation
318264B	Issouf SAWADOGO, Économie et Finances	agent
402917M	Mariam KABORÉ, Santé	agent
155380T	Boukary ZONGO, Administration territoriale	agent
511734S	Salif COMPAORÉ, Éducation nationale	agent (captures de la page d'accueil)
286045A	Awa TRAORÉ, Direction générale du Trésor	agent (captures de la page d'accueil)
Les comptes en 9000xxX sont réservés aux tests automatisés. Tous ces comptes, et leurs secrets dans demo/, sont à supprimer avant une vraie mise en service.
La démo pas à pas
1.	Ouvrez https://faso.localhost, cliquez sur « Se connecter » et entrez 318264B. Dans une fenêtre privée, connectez-vous en 402917M.
2.	318264B crée une conversation et y invite 402917M.
3.	318264B choisit Confidentiel, effacement après 30 secondes, puis envoie un message. Il s'affiche dans un cadre rouge avec un compte à rebours, et le menu ne propose plus ni « Transférer » ni « Modifier ».
4.	À l'échéance, le message disparaît des deux écrans. Le serveur ne garde que la trace de sa suppression.
5.	Pendant que 402917M est en train d'écrire, on le révoque, depuis la console (connecté en 247851K) ou avec :
./faso revoquer 402917M
Sa session se ferme tout de suite, il sort de la conversation et ne peut plus se reconnecter.
6.	./faso reintegrer 402917M lui rend l'accès.
Comment c'est construit
Le navigateur de l'agent ne parle qu'à Caddy, en HTTPS. Caddy sert la page d'accueil et redirige vers le bon service :
navigateur de l'agent
    Caddy (seul point d'entrée)
        /           page d'accueil
         /app/       Element Web, le client, qui chiffre et déchiffre sur l'appareil
         matrix.     Synapse et son module faso_cikan
        auth.       Keycloak : matricule, code à usage unique, rôles
         console.    console de l'autorité

Synapse <-> Keycloak par OpenID Connect, les deux sur PostgreSQL.
La console pilote Keycloak et Synapse par leurs API d'administration, sur le réseau interne.
Les choix techniques sont détaillés dans docs/ARCHITECTURE.md, les garanties et les limites dans docs/NOTE_SECURITE.md.
Pour installer et utiliser le projet pas à pas, voir docs/GUIDE.md ; pour l'installation technique, l'exploitation et la mise en production, voir docs/GUIDE_TECHNIQUE.pdf (source : docs/GUIDE_TECHNIQUE.md).
Où trouver quoi
docker-compose.yml        tous les services, une seule commande
faso                      script de pilotage
accueil/                  page d'accueil publique (HTML et CSS, sans dépendance externe)
synapse/conf/             configuration durcie de Synapse
synapse/modules/          module serveur : chiffrement imposé, classification, expiration
keycloak/realm/           realm « fonction-publique » importé au démarrage
keycloak/themes/faso/     page de connexion
element/src/faso/         ce qu'on a ajouté à Element (sélecteur, cadre, barre du haut)
element/patches/          les modifications des fichiers d'Element et du SDK Matrix
element/config/           configuration du client (thème, fonctions désactivées)
element/branding/         habillage chargé à chaud : faso.css, police Work Sans, emblème
console/                  console de révocation et d'enrôlement (FastAPI)
caddy/                    reverse proxy et en-têtes de sécurité
tests/                    tests de bout en bout
docs/                     architecture et note de sécurité
Tests
./faso tests
Ce sont 26 tests de bout en bout. Ils passent par les vraies adresses HTTPS et refont le parcours d'un navigateur (page Keycloak, mot de passe, code à usage unique). On y vérifie entre autres que la fédération, l'inscription, la connexion par mot de passe local et l'API d'administration sont inaccessibles, qu'un matricule non enrôlé, un mauvais code ou un compte sans rôle « agent » sont rejetés, qu'un message en clair ou une étiquette invalide sont refusés, qu'un message confidentiel est réellement effacé côté serveur à l'échéance, et qu'une révocation en pleine conversation invalide le jeton, fait sortir du salon et empêche de se reconnecter.
Keycloak bloque un compte pendant une minute après deux échecs rapprochés. Laissez donc une minute entre deux exécutions complètes.
Logiciels utilisés
Composant	Rôle	Licence	Projet
Synapse	Serveur Matrix	AGPL-3.0	github.com/element-hq/synapse
Element Web	Client web et chiffrement	AGPL-3.0	github.com/element-hq/element-web
matrix-js-sdk	SDK Matrix du client	Apache-2.0	github.com/matrix-org/matrix-js-sdk
PostgreSQL	Base de données	Licence PostgreSQL	postgresql.org
Keycloak	Identité, second facteur, rôles	Apache-2.0	github.com/keycloak/keycloak
Caddy	Reverse proxy, TLS	Apache-2.0	github.com/caddyserver/caddy
FastAPI	Console d'administration	MIT	github.com/fastapi/fastapi
Docker Compose	Déploiement en une commande	Apache-2.0	github.com/docker/compose
Work Sans	Police de l'interface	SIL OFL 1.1	github.com/weiweihuanghuang/Work-Sans
Phosphor Icons	Icônes de la page d'accueil	MIT	github.com/phosphor-icons/core
Simple Icons	Logos des logiciels libres	CC0-1.0	github.com/simple-icons/simple-icons
Versions utilisées : Synapse v1.163.2, Element Web v1.12.32, matrix-js-sdk 44.0.0, Keycloak 26.7.5, PostgreSQL 16 et Caddy 2.10.
Ce qu'on a changé dans Element
Notre code est dans element/src/faso/. Dans Element lui-même, on ne touche que de quoi le brancher : 40 lignes sur 10 fichiers, plus 9 lignes dans le SDK.
•	SendMessageComposer.tsx et ContentMessages.ts ajoutent l'étiquette aux messages et aux pièces jointes.
•	MessageComposer.tsx affiche le sélecteur de classification au-dessus de la saisie.
•	MessageEvent.tsx dessine le cadre, le compte à rebours et masque le message à l'échéance.
•	getForwardableEvent.ts et DialogOpener.ts empêchent de transférer un message classifié, et EventUtils.ts empêche de le modifier.
•	MatrixChat.tsx, LoggedInView.tsx et SpacePanel.tsx chargent l'habillage, ajoutent la barre du haut et déplient la navigation.
•	Côté SDK, RoomEncryptor.ts recopie l'étiquette en clair à côté du texte chiffré.
Équipe
•	BANHORO Basséri Arcélia & Doamba beatrice samdubwaoga , serveur et sécurité
•	RUFAI SARATOU, client
Licence
AGPL-3.0, comme Synapse et Element dont le projet dérive. Le texte complet est dans LICENSE.
