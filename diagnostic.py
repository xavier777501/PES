"""
Diagnostic pour vérifier l'installation
"""
import sys

print("=" * 60)
print("  DIAGNOSTIC BACKEND PES FACE UV")
print("=" * 60)
print()

print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")
print()

modules = [
    ("cv2", "OpenCV"),
    ("mediapipe", "MediaPipe"),
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("numpy", "NumPy"),
    ("PIL", "Pillow"),
]

installed = []
missing = []

for module_name, display_name in modules:
    try:
        mod = __import__(module_name)
        version = getattr(mod, "__version__", "?")
        print(f"✅ {display_name:12} {version}")
        installed.append(display_name)
    except ImportError:
        print(f"❌ {display_name:12} NON INSTALLÉ")
        missing.append(display_name)

print()
print("=" * 60)

if missing:
    print(f"❌ {len(missing)} module(s) manquant(s): {', '.join(missing)}")
    print()
    print("Pour installer:")
    print(f"  pip install {' '.join(missing.lower())}")
else:
    print("✅ Tous les modules sont installés !")
    print()
    print("Tu peux lancer le serveur:")
    print("  python main.py")

print("=" * 60)
