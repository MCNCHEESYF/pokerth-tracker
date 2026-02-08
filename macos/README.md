# Build macOS pour PokerTH Tracker

Ce dossier contient tous les scripts et configurations nécessaires pour créer un **binaire universel** (Intel + Apple Silicon) et un **DMG distributable** pour macOS 13+.

## 📋 Prérequis

### Système
- macOS 13.0 (Ventura) ou supérieur
- Xcode Command Line Tools installé : `xcode-select --install`

### Python et dépendances
```bash
# Python 3.9+ recommandé
python3 --version

# Installation de PyInstaller
pip3 install pyinstaller

# Installation des dépendances de l'application
pip3 install -r ../requirements.txt
```

## 🚀 Build rapide (Méthode recommandée)

Pour créer le binaire universel ET le DMG en une seule commande :

```bash
cd macos
chmod +x build-all.sh
./build-all.sh
```

Le DMG final sera créé dans `macos/dist/PokerTH-Tracker-X.X.X-Universal.dmg`

## 🔧 Build étape par étape

### Étape 1: Créer le binaire universel

```bash
cd macos
chmod +x build-universal.sh
./build-universal.sh
```

Ce script :
- Nettoie les builds précédents
- Compile pour Intel (x86_64)
- Compile pour Apple Silicon (arm64)
- Fusionne les deux binaires avec `lipo`
- Crée `dist/PokerTH Tracker.app` universel

### Étape 2: Créer le DMG

```bash
cd macos
chmod +x create-dmg.sh
./create-dmg.sh
```

Ce script :
- Crée un DMG avec l'application
- Ajoute un lien vers le dossier Applications
- Configure la présentation du DMG
- Compresse le DMG final

## 📁 Structure des fichiers

```
macos/
├── README.md                    # Ce fichier
├── pokerth-tracker.spec        # Configuration PyInstaller
├── build-universal.sh          # Script de build universel
├── create-dmg.sh               # Script de création du DMG
├── build-all.sh                # Script complet (build + DMG)
├── create-icns.sh              # Utilitaire pour créer des icônes
├── assets/                     # Ressources
│   ├── .gitkeep
│   ├── icon.icns              # Icône de l'app (à créer)
│   └── dmg-background.png     # Fond du DMG (optionnel)
├── build/                      # Fichiers temporaires (gitignored)
└── dist/                       # Applications et DMG générés
    ├── PokerTH Tracker.app
    └── PokerTH-Tracker-X.X.X-Universal.dmg
```

## 🎨 Création des ressources

### Icône de l'application (icon.icns)

1. Créez ou trouvez une image PNG de 1024x1024 pixels
2. Utilisez le script fourni :

```bash
cd macos
chmod +x create-icns.sh
./create-icns.sh mon-icone.png assets/icon.icns
```

### Image de fond du DMG (optionnel)

1. Créez une image PNG de 640x400 pixels
2. Placez-la dans `assets/dmg-background.png`
3. Le script `create-dmg.sh` l'utilisera automatiquement

## 🏗️ Architecture universelle

Le binaire créé contient du code pour les deux architectures :

- **Intel (x86_64)** : Mac avec processeur Intel
- **Apple Silicon (arm64)** : Mac M1, M2, M3, M4, etc.

Vérification :
```bash
lipo -info "dist/PokerTH Tracker.app/Contents/MacOS/PokerTH Tracker"
# Output: Architectures in the fat file: x86_64 arm64
```

## 🎯 Configuration minimale

Le binaire requiert **macOS 13.0 (Ventura)** minimum. Pour changer cette version :

1. Éditez `pokerth-tracker.spec`
2. Modifiez la valeur `LSMinimumSystemVersion` dans `info_plist`

## ⚙️ Personnalisation

### Modifier les informations de l'application

Éditez `pokerth-tracker.spec` :

```python
app = BUNDLE(
    ...
    bundle_identifier='com.votre-entreprise.pokerth-tracker',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'PokerTH Tracker',
        'CFBundleVersion': '1.0.0',
        'LSMinimumSystemVersion': '13.0',
        # Autres paramètres...
    },
)
```

### Exclure des modules inutiles

Dans `pokerth-tracker.spec`, section `excludes` :

```python
excludes=[
    'tkinter',      # Interface Tk/Tcl
    'matplotlib',   # Graphiques
    'numpy',        # Calculs scientifiques
    'pandas',       # DataFrames
    # Ajoutez d'autres modules à exclure
],
```

## 🐛 Dépannage

### Erreur: "PyInstaller not found"
```bash
pip3 install pyinstaller
```

### Erreur: "command not found: lipo"
```bash
xcode-select --install
```

### L'application ne se lance pas
1. Testez directement l'app : `open "dist/PokerTH Tracker.app"`
2. Vérifiez les logs : `Console.app` → Rechercher "PokerTH"
3. Lancez en mode debug :
```bash
"dist/PokerTH Tracker.app/Contents/MacOS/PokerTH Tracker"
```

### Le DMG ne se crée pas correctement
- Assurez-vous qu'aucun volume "PokerTH Tracker" n'est déjà monté
- Démontez manuellement : `hdiutil detach "/Volumes/PokerTH Tracker"`

### Problème de permissions
```bash
chmod +x macos/*.sh
```

## 📦 Distribution

### Signature de code (pour distribution publique)

Pour distribuer en dehors du Mac App Store :

1. Obtenez un certificat "Developer ID Application"
2. Ajoutez dans `pokerth-tracker.spec` :
```python
codesign_identity='Developer ID Application: Votre Nom (TEAM_ID)',
```

3. Notarize l'application :
```bash
xcrun notarytool submit "dist/PokerTH-Tracker-X.X.X-Universal.dmg" \
    --apple-id "votre@email.com" \
    --password "mot-de-passe-app-specifique" \
    --team-id "TEAM_ID" \
    --wait
```

### Distribution simple (sans signature)

Le DMG peut être distribué directement, mais les utilisateurs devront :
1. Clic droit → Ouvrir (première fois)
2. Autoriser dans Préférences Système → Confidentialité et sécurité

## 🔄 Workflow de release

1. Mettez à jour le numéro de version dans :
   - `pokerth-tracker.spec` (`version=`)
   - `create-dmg.sh` (`VERSION=`)

2. Créez le build :
```bash
./macos/build-all.sh
```

3. Testez l'application :
```bash
open "macos/dist/PokerTH Tracker.app"
```

4. Distribuez le DMG :
```bash
macos/dist/PokerTH-Tracker-X.X.X-Universal.dmg
```

## 📝 Notes

- Les builds sont créés dans `macos/dist/`
- Les fichiers temporaires sont dans `macos/build/`
- Les deux dossiers sont ignorés par git (via `.gitignore`)
- Le binaire universel fonctionne automatiquement selon l'architecture du Mac

## 🆘 Support

En cas de problème :
1. Vérifiez les logs de build
2. Testez l'application avant de créer le DMG
3. Assurez-vous que toutes les dépendances sont installées

---

**Bon build! 🚀**
