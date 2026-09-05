# Dockerfile pour déployer le backend Python sur Render
# BASE DE UBNTU 22.04 QUI A libGLESv2.so.2 DANS SES PAQUETS
FROM ubuntu:22.04

# Installer les dépendances système avec libGLESv2
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
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
    libgtk-3-0 \
    libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*

# Définir le working directory
WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir opencv-python-headless==4.10.0.84 && \
    pip3 install --no-cache-dir --no-deps mediapipe>=1.0.0 && \
    pip3 install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Exposer le port
EXPOSE 10000

# Lancer le serveur FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
