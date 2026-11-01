# Faso Cikan — démonstration en 5 minutes

## 1. Lancer (une seule fois)
Ouvrir Docker Desktop, attendre qu'il soit vert, puis dans le dossier du projet :

    faso.cmd demarrer

## 2. Les adresses
| Quoi | Adresse |
|---|---|
| Accueil | https://faso.localhost |
| Messagerie | https://faso.localhost/app/ |
| Console de l'autorité | https://console.faso.localhost |

Le navigateur avertit du certificat : « Avancé » puis « Continuer ».

## 3. Se connecter
Mot de passe de tous les comptes : `Cikan-Demo-2026`

| Matricule | Qui |
|---|---|
| 318264B | Issouf (Économie et Finances) |
| 402917M | Mariam (Santé) |
| 247851K | Aminata (autorité : accès à la console) |

Code à usage unique (change toutes les 30 s) :

    code.cmd 318264B

## 4. Le scénario
1. Fenêtre normale : connexion en `318264B`. Fenêtre privée : connexion en `402917M`.
2. `318264B` crée un salon et invite `402917M`.
3. Il choisit **Confidentiel**, effacement après 30 s, et envoie un message.
   Cadre rouge, compte à rebours, plus de « Transférer » ni « Modifier ».
4. Après 30 s le message disparaît chez les deux. Le serveur ne l'a jamais lu.
5. Révocation : `faso.cmd revoquer 402917M` (ou bouton dans la console avec `247851K`).
   Sa session se coupe, il sort du salon, il ne peut plus se reconnecter.
6. `faso.cmd reintegrer 402917M` lui rend l'accès.

## 5. Arrêter / reprendre
    faso.cmd arreter      (les données sont gardées)
    faso.cmd demarrer
