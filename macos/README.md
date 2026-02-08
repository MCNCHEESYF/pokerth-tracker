# Build DMG pour macOS - PokerTH Tracker

Ce répertoire contient l'architecture de build pour créer une image DMG installable de PokerTH Tracker sur macOS.

## Prérequis

- **macOS** : 10.13 (High Sierra) ou plus récent
- **Python 3.12+** : Disponible via Homebrew ou python.org
- **pip** : Gestionnaire de paquets Python (inclus avec Python)
- **PyInstaller** : Sera installé automatiquement par le script de build

### Installation optionnelle pour des icônes personnalisées

Pour créer une icône .icns à partir du fichier SVG, vous pouvez installer :

```bash
brew install librsvg
```

Sans cet outil, l'icône par défaut de Python sera utilisée.

## Structure des fichiers

```
macos/
├── README.md              # Ce fichier
├── Info.plist             # Métadonnées du bundle macOS
├── pokerth-tracker.spec   # Configuration PyInstaller
└── build-dmg.sh           # Script de build principal
```

## Utilisation

### Build complet (recommandé)

Exécutez simplement le script de build depuis la racine du projet :

```bash
./macos/build-dmg.sh
```

Le script effectuera automatiquement :
1. Vérification des prérequis (Python, pip)
2. Installation de PyInstaller si nécessaire
3. Nettoyage des anciens builds
4. Création de l'icône .icns (si les outils sont disponibles)
5. Construction du bundle .app avec PyInstaller
6. Création de l'image DMG finale

### Résultat

Le fichier DMG sera créé à la racine du projet :

```
PokerTH_Tracker-macOS.dmg
```

Taille approximative : 50-80 MB

## Installation de l'application

1. Double-cliquez sur `PokerTH_Tracker-macOS.dmg`
2. Une fenêtre s'ouvrira avec l'application et un raccourci vers Applications
3. Glissez-déposez `PokerTH Tracker.app` dans le dossier Applications
4. Éjectez le volume DMG
5. Lancez l'application depuis le Launchpad ou le dossier Applications

## Première exécution

Lors de la première exécution, macOS peut afficher un avertissement de sécurité car l'application n'est pas signée par un développeur Apple identifié.

Pour autoriser l'application :

1. **Méthode 1** : Ouvrez **Préférences Système** > **Sécurité et confidentialité** > **Général**
   - Cliquez sur "Ouvrir quand même" pour autoriser l'application

2. **Méthode 2** : Faites un clic droit (ou Ctrl+clic) sur l'application
   - Sélectionnez "Ouvrir" dans le menu contextuel
   - Confirmez l'ouverture

## Personnalisation

### Modifier la version

Éditez les fichiers suivants :

- `macos/Info.plist` : Modifiez `CFBundleShortVersionString` et `CFBundleVersion`
- `macos/build-dmg.sh` : Modifiez la variable `VERSION`
- `macos/pokerth-tracker.spec` : Modifiez le paramètre `version` dans la section `BUNDLE`

### Modifier l'icône

L'icône est générée automatiquement à partir du fichier SVG dans `appimage/pokerth-tracker.svg`.

Pour utiliser une icône personnalisée :
1. Créez un fichier `macos/icon.icns`
2. Le script de build l'utilisera automatiquement

### Personnaliser l'apparence du DMG

Le script configure automatiquement :
- Taille de la fenêtre : 500x350 pixels
- Vue : Icônes (128x128)
- Disposition : Application à gauche, lien Applications à droite

Pour une personnalisation avancée, modifiez la section `create_dmg()` dans `build-dmg.sh`.

## Dépannage

### Erreur : "PyInstaller not found"

Installez PyInstaller manuellement :

```bash
pip3 install pyinstaller
```

### Erreur : "Unable to create icon"

L'application fonctionnera quand même avec l'icône par défaut. Pour une icône personnalisée :

```bash
brew install librsvg
```

### Erreur : "hdiutil: create failed"

Assurez-vous d'avoir suffisamment d'espace disque (au moins 200 MB libres).

### L'application ne se lance pas

Vérifiez les logs dans la Console macOS :

1. Ouvrez **Console.app**
2. Recherchez les messages d'erreur liés à "PokerTH Tracker"

## Signature de code (pour distribution)

Pour distribuer l'application en dehors de votre système, vous devrez la signer avec un certificat de développeur Apple :

```bash
# Signer le bundle .app
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" \
  "macos/dist/PokerTH Tracker.app"

# Signer le DMG
codesign --force --verify --verbose --sign "Developer ID Application: Your Name" \
  "PokerTH_Tracker-macOS.dmg"
```

Pour obtenir un certificat de développeur, inscrivez-vous au programme Apple Developer (99 USD/an).

## Notarisation (pour macOS 10.15+)

Pour que l'application s'exécute sans avertissement sur macOS Catalina et plus récent :

```bash
# Soumettre pour notarisation
xcrun notarytool submit "PokerTH_Tracker-macOS.dmg" \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID" \
  --wait

# Agrafer le ticket de notarisation
xcrun stapler staple "PokerTH_Tracker-macOS.dmg"
```

## Support

Pour les problèmes de build ou d'installation, créez une issue sur le dépôt GitHub du projet.
