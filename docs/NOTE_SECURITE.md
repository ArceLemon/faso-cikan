Note de sécurité

Ce que Faso Cikan protège, contre qui, et ce qu’il ne protège pas. On a préféré écrire noir sur blanc les limites plutôt que de laisser croire que tout est couvert.

Ce qui est protégé

Les messages, face à l’hébergeur ou à un administrateur système. Le chiffrement de bout en bout (Olm et Megolm) se fait uniquement sur les appareils. Le serveur ne stocke que du texte chiffré.

Contre un client mal configuré qui enverrait en clair. Le module serveur faso_cikan refuse tout m.room.message non chiffré, avec une erreur 403.

Contre les personnes extérieures à l’administration. L’inscription est fermée, la fédération coupée, et on ne peut se connecter qu’en passant par Keycloak. Un matricule non enrôlé est rejeté.

En cas de vol de mot de passe. Un code à usage unique (TOTP) est demandé à chaque connexion, et un code ne peut pas servir deux fois.

Contre les essais de mots de passe à la chaîne. Keycloak verrouille de plus en plus longtemps, et bloque le compte une minute après deux échecs rapprochés.

Pour un compte qui existe mais n’a pas d’autorisation. Synapse exige le rôle agent dans le jeton d’identité. Un compte Keycloak sans ce rôle est refusé.

Quand un agent est muté ou radié. La révocation désactive son compte dans Keycloak, ferme ses sessions, désactive son compte Matrix (tous ses jetons et appareils sont supprimés) et le fait sortir de tous les salons.

Pour éviter qu’un document classifié soit transféré. L’option « Transférer » est retirée et la boîte de transfert est bloquée dans le client.

Pour qu’un message confidentiel ne traîne pas. Le serveur l’efface (rédaction) à l’échéance, et le contenu chiffré disparaît de la base au bout d’une minute.

Pour ne pas exposer l’administration du serveur. Le reverse proxy ne publie pas l’API d’administration de Synapse. Seule la console y accède, par le réseau interne.

Contre l’usurpation d’identité dans les conversations. Le nom affiché vient de l’annuaire Keycloak et l’agent ne peut pas le changer.

Ce que le serveur voit

Le chiffrement protège le contenu, pas les métadonnées dont le serveur a besoin pour acheminer les messages. Le serveur connaît donc l’expéditeur, le salon et l’heure de chaque message, la liste des membres de chaque salon et l’adresse IP de connexion. Il voit aussi la taille des pièces jointes, qui sont elles-mêmes chiffrées.

Pour un message classifié, il voit en plus son niveau et son délai d’expiration. L’étiquette voyage en clair à côté du texte chiffré : sans ça, le serveur ne pourrait pas l’effacer à l’échéance.

Pour limiter ce qu’il apprend, on a désactivé la présence en ligne (pas de « en ligne » ni de « vu à »), gardé les adresses IP un jour seulement, et coupé les aperçus de liens pour que le serveur n’aille jamais chercher une page à la place de l’agent. Les messages supprimés sont purgés de la base au bout d’une minute, et les médias locaux ne sont pas gardés plus d’un an.

Limites connues

Elles existent, autant les connaître.

Un agent révoqué peut encore lire les messages déjà reçus sur son appareil, tant qu’il n’a pas fermé l’application ou que le stockage local n’a pas été vidé. La révocation lui coupe l’accès au serveur, mais elle ne peut pas effacer à distance la mémoire de son appareil. Un appareil perdu doit donc aussi être traité par la gestion de flotte du ministère.

La classification est appliquée par le client. Un agent qui utilise un client Matrix modifié, ou qui recopie le texte à la main, peut faire circuler un contenu confidentiel. Le serveur ne lit pas les messages, il ne peut pas savoir qu’un nouveau message reprend un ancien. Faso Cikan évite les erreurs et les gestes trop faciles, pas la malveillance d’un agent habilité.

Les captures d’écran ne sont pas bloquées, parce que le navigateur ne le permet pas. Le blocage est prévu dans une future application mobile.

L’effacement à l’échéance passe par la rédaction Matrix. Les clients conformes retirent le contenu à la synchronisation suivante, mais un appareil hors ligne garde le message jusqu’à ce qu’il se reconnecte.

L’étiquette en clair et l’étiquette chiffrée peuvent ne pas correspondre si un client malveillant les écrit différemment. Le serveur se base sur l’étiquette en clair pour l’expiration, le client sur l’étiquette chiffrée pour l’affichage.

Le TOTP ne protège pas d’un hameçonnage en temps réel. Une clé de sécurité matérielle (WebAuthn) le ferait. Keycloak sait la gérer, et c’est ce qu’on recommande pour les autorités.

Enfin, un administrateur Keycloak peut créer un compte. C’est à l’organisation d’encadrer ce pouvoir : comptes nominatifs, journal Keycloak, séparation entre l’exploitation et l’autorité.

Avant une vraie mise en service

Mettre un vrai domaine dans FASO_DOMAINE. Caddy obtiendra alors des certificats publics.

Supprimer le dossier demo/ et les comptes de démonstration du realm.

Limiter l’accès à /admin de Keycloak au réseau d’exploitation.

Sauvegarder les volumes postgres et synapse (qui contient la clé de signature), chiffrés et hors site.

Activer WebAuthn pour les agents qui ont le rôle d’autorité.

Faire auditer le patch client et le module serveur par l’ANSSI du Burkina Faso ou un tiers de confiance.