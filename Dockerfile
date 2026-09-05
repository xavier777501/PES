# Dockerfile pour déployer le backend Python sur Render avec OpenCV headless
FROM python:3.11-slim

# Installer les dépendances système pour MediaPipe (qui a besoin de libGLESv2)
# On installe TOUT ce qui pourrait contenir libGLESv2.so.2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    libgles2 \
    libegl1 \
    libgl1 \
    libglx0 \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    mesa-utils \
    && rm -rf /var/lib/apt/lists/*

# Créer le dossier de travail
WORKDIR /app

# Copier les dépendances Python et les installer
COPY requirements.txt .

# Installer les dépendances Python en EMPÊCHANT l'installation d'opencv-contrib-python
RUN pip install --no-cache-dir opencv-python-headless==4.10.0.84 && \
    pip install --no-cache-dir --no-deps mediapipe>=1.0.0 && \
    pip install --no-cache-dir -r requirements.txt

# Copier tout le code source
COPY . .

# Exposer le port
EXPOSE 10000

# Lancer le serveur FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
