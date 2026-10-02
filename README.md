# Raccourcis Espanso

Une petite application Windows pour gérer ses raccourcis texte [Espanso](https://espanso.org) **sans jamais toucher à du code**.

Tu tapes `-mail`, et ton adresse e-mail s'écrit toute seule. Ça marche partout : Word, Outlook, navigateur, Bloc-notes…

## Ce que fait l'app

- **Voir tous tes raccourcis** sur un seul écran, avec une recherche
- **Activer / désactiver** un raccourci en 1 clic, sans le supprimer
- **Créer, modifier, supprimer** un raccourci avec un simple formulaire
- **Réglages** expliqués simplement : pause d'Espanso, lancement au démarrage, recherche rapide (Alt + Espace), touche ⌫ pour annuler, notifications…
- Interface sombre aux couleurs d'Espanso

## Installation

1. Installer [Espanso](https://espanso.org/install/) (Windows)
2. Installer [Python](https://www.python.org/downloads/) (3.10 ou plus récent). Rien d'autre à installer : l'app n'utilise que ce qui est fourni avec Python.
3. Avoir **Google Chrome** ou **Microsoft Edge** (l'app s'ouvre dans une fenêtre sans barre d'adresse)
4. Télécharger ce dossier et double-cliquer sur `espanso-gui.pyw`

Astuce : clic droit sur `espanso-gui.pyw` → *Envoyer vers* → *Bureau (créer un raccourci)* pour l'avoir sur le bureau.

## Comment ça marche (pour les curieux)

- Chaque raccourci est un fichier dans `%APPDATA%\espanso\match\` (format JSON, qu'Espanso lit comme du YAML).
- Un raccourci désactivé est simplement renommé avec un `_` devant : Espanso ignore ces fichiers.
- Les réglages sont écrits dans `%APPDATA%\espanso\config\default.yml`.
- L'app lance un petit serveur local (`127.0.0.1`, port aléatoire, protégé par un jeton) et l'affiche dans une fenêtre Chrome/Edge en mode application. Fermer la fenêtre arrête l'app.

### Limites

- Les raccourcis écrits à la main en YAML classique (ex. l'ancien `base.yml`) ne sont pas affichés : il faut les découper en un fichier par raccourci.
- Ne pas ouvrir l'app deux fois en même temps (fermer la première fenêtre avant).

## Crédits

Logo et nom © [Espanso](https://github.com/espanso/espanso) (Federico Terzi). Cette app est un outil non officiel.
