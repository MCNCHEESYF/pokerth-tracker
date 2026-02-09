# Build macOS pour PokerTH Tracker

Architecture de build simplifiée pour créer un **DMG pour Apple Silicon** (M1/M2/M3/M4).

## 📋 Prérequis

### Système
- macOS 13.0 (Ventura) ou supérieur
- Mac Apple Silicon (M1/M2/M3/M4)

### Dépendances
```bash
# Python 3.9+
python3 --version

# PyInstaller
pip3 install pyinstaller

# Dépendances de l'application
pip3 install -r ../requirements.txt
```

## 🚀 Build rapide

Pour créer le DMG en une commande :

```bash
cd macos
./build-dmg.sh
```

Le DMG sera créé dans `macos/dist/PokerTH-Tracker-1.0.0-AppleSilicon.dmg`

## 🔧 Build étape par étape

### Étape 1 : Build de l'application

```bash
cd macos
./build.sh
```

Crée `dist/PokerTH Tracker.app`

### Étape 2 : Création du DMG

```bash
./create-dmg.sh
```

Crée le DMG final avec installateur

## 📁 Structure des fichiers

```
macos/
├── README.md              # Ce fichier
├── pokerth-tracker.spec   # Configuration PyInstaller
├── build.sh               # Script de build de l'app
├── create-dmg.sh          # Script de création du DMG
├── build-dmg.sh           # Script tout-en-un
├── create-icns.sh         # Utilitaire pour créer des icônes
└── assets/
    └── icon.icns          # Icône de l'application
```

## 🎨 Créer/Modifier l'icône

Pour créer une icône à partir d'une image PNG 1024x1024 :

```bash
./create-icns.sh mon-icone.png assets/icon.icns
```

Pour recréer à partir du SVG existant :

```bash
rsvg-convert -w 1024 -h 1024 ../appimage/pokerth-tracker.svg -o temp.png
./create-icns.sh temp.png assets/icon.icns
rm temp.png
```

## ⚙️ Configuration

### Modifier les informations de l'application

Éditez [pokerth-tracker.spec](pokerth-tracker.spec) :

```python
app = BUNDLE(
    ...
    bundle_identifier='com.pthtracker.pokerthtacker',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'PokerTH Tracker',
        'CFBundleVersion': '1.0.0',
        'LSMinimumSystemVersion': '13.0',
        ...
    },
)
```

### Mettre à jour le numéro de version

1. Dans `pokerth-tracker.spec` → `version='X.X.X'`
2. Dans `create-dmg.sh` → `VERSION="X.X.X"`

## 🐛 Dépannage

### L'application ne se lance pas

Testez directement :
```bash
open "dist/PokerTH Tracker.app"
```

Vérifiez les logs :
```bash
"dist/PokerTH Tracker.app/Contents/MacOS/PokerTH Tracker"
```

### Erreur PyInstaller

Réinstallez PyInstaller :
```bash
pip3 uninstall pyinstaller
pip3 install pyinstaller
```

### Le DMG ne se monte pas

Démontez les volumes existants :
```bash
hdiutil detach "/Volumes/PokerTH Tracker"
```

## 📦 Distribution

### Sans signature de code

Le DMG peut être distribué directement. Les utilisateurs devront :
1. Télécharger le DMG
2. Ouvrir le DMG
3. Glisser l'app vers Applications
4. Clic droit → Ouvrir (première fois)
5. Autoriser dans Préférences Système → Sécurité

### Avec signature de code (recommandé)

Pour une distribution professionnelle :

1. Obtenez un certificat "Developer ID Application"
2. Ajoutez dans `pokerth-tracker.spec` :
   ```python
   codesign_identity='Developer ID Application: Votre Nom (TEAM_ID)',
   ```
3. Notarisez l'app :
   ```bash
   xcrun notarytool submit "dist/PokerTH-Tracker-X.X.X-AppleSilicon.dmg" \
       --apple-id "votre@email.com" \
       --password "mot-de-passe-app-specifique" \
       --team-id "TEAM_ID" \
       --wait
   ```

## 🔄 Workflow complet

```bash
# 1. Mettre à jour la version
vim pokerth-tracker.spec  # version='1.0.0'
vim create-dmg.sh          # VERSION="1.0.0"

# 2. Builder et créer le DMG
./build-dmg.sh

# 3. Tester
open "dist/PokerTH Tracker.app"

# 4. Distribuer
# Le fichier est dans: dist/PokerTH-Tracker-1.0.0-AppleSilicon.dmg
```

## 📝 Notes

- **Architecture** : arm64 (Apple Silicon uniquement)
- **Compatible** : macOS 13.0+ (Ventura)
- **Processeurs** : M1, M2, M3, M4
- **Taille** : ~80 MB

## ❓ FAQ

### Pourquoi pas Intel (x86_64) ?

- Les Mac Intel sont <5% des ventes depuis 2023
- Architecture simplifiée = moins de bugs
- Fichier plus léger
- Si vraiment nécessaire, créer un build séparé

### Fonctionne sur Mac Intel ?

Non, ce build est optimisé pour Apple Silicon uniquement. Pour les vieux Mac Intel, il faudrait un build séparé.

---

**Bon build! 🚀**
