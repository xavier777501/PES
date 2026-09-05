# Dockerfile pour déployer le backend Python sur Render
FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Créer le dossier de travail
WORKDIR /app

# Copier les dépendances Python et les installer
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir opencv-python-headless==4.10.0.84 && \
    pip install --no-cache-dir --no-deps mediapipe>=1.0.0 && \
    pip install --no-cache-dir -r requirements.txt

# Copier tout le code source
COPY . .

# Créer un script qui va s'exécuter au démarrage pour installer libGLESv2
RUN echo '#!/bin/bash\n\
# Script de bootstrap pour installer libGLESv2.so.2\n\
# Installer le paquet libgles2-mesa qui devrait fournir la bibliothèque\n\
apt-get update && apt-get install -y --no-install-recommends libgles2-mesa libegl1 mesa-utils\n\
# Chercher le fichier libGLESv2.so.2\n\
FOUND_LIB=$(find /usr -name "libGLESv2.so*" 2>/dev/null | head -1)\n\
if [ -n "$FOUND_LIB" ]; then\n\
    echo "Found libGLESv2: $FOUND_LIB"\n\
    # Créer un lien symbolique dans /usr/local/lib si nécessaire\n\
    if [ ! -f /usr/local/lib/libGLESv2.so.2 ]; then\n\
        ln -sf "$FOUND_LIB" /usr/local/lib/libGLESv2.so.2\n\
        echo "Created symlink /usr/local/lib/libGLESv2.so.2 -> $FOUND_LIB"\n\
    fi\n\
fi\n\
# Mettre à jour le cache des bibliothèques\n\
ldconfig\n\
# Lancer uvicorn\n\
exec "$@"' > /docker-startup.sh && chmod +x /docker-startup.sh

# Copier le script dans le conteneur
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Exposer le port
EXPOSE 10000

# Utiliser le script d'entrée
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
