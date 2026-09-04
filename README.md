# Backend Python - PES Face UV Generator

## 🎯 Description

API FastAPI qui utilise le code Python exact qui marche déjà (`main.py`).
Garantit la même précision que la version desktop.

## 📦 Installation

### 1. Créer un environnement virtuel
```bash
cd d:\pes\pes-pwa\backend
python -m venv venv
venv\Scripts\activate
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

## 🚀 Lancer le serveur

### Mode développement
```bash
python main.py
```

ou

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Le serveur démarre sur `http://localhost:8000`

## 📡 Endpoints

### `GET /`
Informations sur l'API
```json
{
  "service": "PES Face UV Generator",
  "version": "1.0.0",
  "status": "running",
  "templates_loaded": 9
}
```

### `GET /health`
Health check
```json
{
  "status": "healthy",
  "templates": 9
}
```

### `POST /api/generate-face`
Génère une texture UV depuis une photo

**Request:**
- `image`: Fichier image (multipart/form-data)
- `template_id`: (optionnel) Index du template (0-8)

**Response:**
- Image PNG 512×512
- Headers:
  - `X-Template-Used`: Template utilisé
  - `X-Image-Size`: Dimensions

**Exemple avec curl:**
```bash
curl -X POST "http://localhost:8000/api/generate-face" \
  -F "image=@photo.jpg" \
  --output result.png
```

**Exemple avec Python:**
```python
import requests

with open('photo.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/generate-face',
        files={'image': f}
    )

with open('result.png', 'wb') as f:
    f.write(response.content)
```

## 📁 Structure

```
backend/
├── main.py                 # API FastAPI
├── face_generator.py       # Code de génération (ton main.py)
├── face_utils.py           # Utilitaires
├── face_landmarker.task    # Modèle MediaPipe
├── requirements.txt        # Dépendances
├── templates/              # Templates UV de référence
│   ├── template_1.png
│   ├── template_2.png
│   └── ...
└── temp/                   # Fichiers temporaires (créé auto)
```

## 🔧 Configuration

### Variables d'environnement (optionnel)
```bash
# .env
PORT=8000
HOST=0.0.0.0
TEMP_DIR=temp
TEMPLATES_DIR=templates
```

## 🐛 Debug

### Logs détaillés
```bash
uvicorn main:app --reload --log-level debug
```

### Tester l'endpoint
```bash
# Health check
curl http://localhost:8000/health

# Upload test
curl -X POST "http://localhost:8000/api/generate-face" \
  -F "image=@test.jpg" \
  -o output.png -v
```

## 📊 Performance

- **Temps moyen**: 2-5 secondes par image
- **RAM**: ~500MB (MediaPipe + OpenCV)
- **CPU**: Utilise tous les cœurs disponibles

## 🔒 Sécurité

### En production
1. Limiter la taille des fichiers uploadés
2. Valider les types MIME
3. Ajouter rate limiting
4. Configurer CORS correctement
5. Utiliser HTTPS

### Exemple avec limite de taille
```python
from fastapi import File, UploadFile

@app.post("/api/generate-face")
async def generate_face(
    image: UploadFile = File(..., max_length=10_000_000)  # 10MB max
):
    ...
```

## 🚢 Déploiement

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Installer dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Port
EXPOSE 8000

# Lancer
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Render.com (gratuit)
1. Push sur GitHub
2. Créer nouveau Web Service sur Render
3. Sélectionner le repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Railway.app
```bash
railway login
railway init
railway up
```

## 🧪 Tests

### Test manuel
```bash
# 1. Lancer le serveur
python main.py

# 2. Dans un autre terminal
curl -X POST "http://localhost:8000/api/generate-face" \
  -F "image=@test_photo.jpg" \
  -o test_result.png

# 3. Ouvrir test_result.png
```

## 🎯 Prochaines étapes

- [ ] Ajouter endpoint pour mode dessin
- [ ] Endpoint pour templates list
- [ ] Websocket pour progress en temps réel
- [ ] Cache des résultats
- [ ] Compression des images
