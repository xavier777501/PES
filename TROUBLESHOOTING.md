# 🔧 Dépannage Backend

## ❌ Erreur: "col not found" ou "could not find"

### Cause
Problème d'installation des packages Python (souvent OpenCV ou MediaPipe).

### Solutions

#### Solution 1: Installation manuelle étape par étape
```bash
cd d:\pes\pes-pwa\backend

# 1. Créer venv
python -m venv venv

# 2. Activer
venv\Scripts\activate

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Installer un par un
pip install fastapi
pip install uvicorn[standard]
pip install python-multipart
pip install numpy
pip install pillow
pip install mediapipe
pip install opencv-python
```

#### Solution 2: Utiliser les versions de ton système actuel
```bash
# Copier depuis ton environnement qui marche
cd d:\pes
pip freeze > installed_packages.txt

# Copier vers le nouveau projet
copy installed_packages.txt d:\pes\pes-pwa\backend\requirements.txt

# Installer
cd d:\pes\pes-pwa\backend
venv\Scripts\activate
pip install -r requirements.txt
```

#### Solution 3: Utiliser conda au lieu de venv
```bash
conda create -n pes-backend python=3.11
conda activate pes-backend
conda install -c conda-forge fastapi uvicorn opencv mediapipe numpy pillow
pip install python-multipart
```

---

## ❌ Erreur: "Python not found"

### Solution
```bash
# Vérifier Python installé
python --version

# Si pas installé, télécharger depuis:
# https://www.python.org/downloads/

# Ou avec winget
winget install Python.Python.3.11
```

---

## ❌ Erreur: "venv not found"

### Solution
```bash
# Installer venv
python -m pip install virtualenv

# Ou utiliser directement pip sans venv
pip install -r requirements.txt
python main.py
```

---

## ❌ Erreur: "Port already in use"

### Solution
```bash
# Changer le port dans main.py
# Ligne finale, remplacer 8000 par 8001:
uvicorn.run(..., port=8001)
```

---

## ❌ Erreur: "face_landmarker.task not found"

### Solution
```bash
# Vérifier que le fichier existe
dir face_landmarker.task

# Si manquant, copier depuis d:\pes\
copy d:\pes\face_landmarker.task d:\pes\pes-pwa\backend\
```

---

## ❌ Erreur: "templates not loaded"

### Solution
```bash
# Vérifier dossier templates
dir templates\

# Si vide, copier depuis REFERENCE
xcopy d:\pes\REFERENCE\*.* d:\pes\pes-pwa\backend\templates\ /E
```

---

## 🐛 MODE DEBUG

### Voir les erreurs détaillées
```bash
# Au lieu de python main.py, utilise:
python
>>> import main
>>> # Voir l'erreur complète
```

### Tester l'import des modules
```bash
python
>>> import cv2
>>> import mediapipe
>>> import fastapi
>>> print("OK")
```

Si un module ne s'importe pas, réinstalle-le:
```bash
pip install --force-reinstall opencv-python
```

---

## 💡 ALTERNATIVE: Utiliser ton environnement actuel

Si tu as déjà un environnement Python qui marche pour main.py:

```bash
# 1. Active ton environnement actuel (si tu en as un)
# Par exemple: venv\Scripts\activate

# 2. Va dans le dossier backend
cd d:\pes\pes-pwa\backend

# 3. Lance directement (sans créer nouveau venv)
python main.py
```

---

## 🔍 Diagnostic complet

Lance ce script pour voir l'état:

```python
# diagnostic.py
import sys
print(f"Python: {sys.version}")
print(f"Path: {sys.executable}")

try:
    import cv2
    print(f"✅ OpenCV: {cv2.__version__}")
except:
    print("❌ OpenCV non installé")

try:
    import mediapipe
    print(f"✅ MediaPipe: {mediapipe.__version__}")
except:
    print("❌ MediaPipe non installé")

try:
    import fastapi
    print(f"✅ FastAPI installé")
except:
    print("❌ FastAPI non installé")

try:
    import numpy
    print(f"✅ NumPy: {numpy.__version__}")
except:
    print("❌ NumPy non installé")
```

```bash
python diagnostic.py
```

---

## 🚨 SI RIEN NE MARCHE

### Option nucléaire: Réutiliser ton setup actuel

```bash
# 1. Va dans ton dossier qui marche
cd d:\pes

# 2. Lance le serveur depuis là
# Copie juste main.py dans ton dossier actuel
copy d:\pes\pes-pwa\backend\main.py d:\pes\api_main.py

# 3. Lance
python api_main.py
```

Le serveur va démarrer avec ton environnement qui marche déjà !

---

## 📞 Si toujours bloqué

Envoie-moi:
1. La commande exacte que tu lances
2. L'erreur COMPLÈTE (copie tout le texte)
3. Ta version Python: `python --version`
4. Ton OS: Windows 10/11
