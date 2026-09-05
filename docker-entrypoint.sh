#!/bin/bash
# Script d'entrée Docker pour installer libGLESv2.so.2 avant de lancer l'app

echo "=== Bootstrap: Installation de libGLESv2.so.2 pour MediaPipe ==="

# Installer les paquets qui pourraient contenir libGLESv2
apt-get update > /dev/null 2>&1
apt-get install -y --no-install-recommends libgles2-mesa libegl1 mesa-utils > /dev/null 2>&1 || true

# Chercher le fichier libGLESv2.so.2 ou libGLESv2.so
FOUND_LIB=$(find /usr -name "libGLESv2.so*" 2>/dev/null | head -1)

if [ -n "$FOUND_LIB" ]; then
    echo "Found libGLESv2 at: $FOUND_LIB"
    
    # Créer un lien symbolique dans /usr/local/lib
    if [ ! -f /usr/local/lib/libGLESv2.so.2 ]; then
        mkdir -p /usr/local/lib
        ln -sf "$FOUND_LIB" /usr/local/lib/libGLESv2.so.2
        echo "Created symlink: /usr/local/lib/libGLESv2.so.2 -> $FOUND_LIB"
    fi
else
    echo "WARNING: libGLESv2.so.2 not found by find command"
    # Listing des fichiers libGL pour diagnostic
    echo "Files matching libGL*:"
    find /usr -name "libGL*" 2>/dev/null
fi

# Mettre à jour le cache des bibliothèques
ldconfig

echo "=== Starting FastAPI application ==="

exec "$@"
