"""
Script de test pour l'API PES Face UV
"""
import requests
import sys
from pathlib import Path

API_URL = "http://localhost:8000"

def test_health():
    """Test du health check"""
    print("🔍 Test health check...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API OK - {data['templates']} templates chargés")
            return True
        else:
            print(f"❌ Erreur {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Impossible de se connecter à l'API")
        print("   Assure-toi que le serveur est lancé (python main.py)")
        return False

def test_generate(image_path: str):
    """Test de génération de texture"""
    print(f"\n🔍 Test génération avec {image_path}...")
    
    if not Path(image_path).exists():
        print(f"❌ Fichier non trouvé: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(
                f"{API_URL}/api/generate-face",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            # Sauvegarder le résultat
            output_path = "test_output.png"
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Texture générée avec succès!")
            print(f"   Sauvegardée: {output_path}")
            print(f"   Taille: {len(response.content)} bytes")
            
            # Afficher les headers
            if 'X-Template-Used' in response.headers:
                print(f"   Template: {response.headers['X-Template-Used']}")
            if 'X-Image-Size' in response.headers:
                print(f"   Dimensions: {response.headers['X-Image-Size']}")
            
            return True
        else:
            print(f"❌ Erreur {response.status_code}")
            print(f"   Message: {response.text}")
            return False
            
    except requests.Timeout:
        print("❌ Timeout (>30s)")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    print("=" * 50)
    print("  Test API PES Face UV")
    print("=" * 50)
    print()
    
    # Test 1: Health check
    if not test_health():
        sys.exit(1)
    
    # Test 2: Génération
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Chercher une image de test
        test_images = [
            "../test.jpg",
            "../test.png", 
            "../../test.jpg",
            "../../f1072581-4d44-48e2-b570-e886768f9f6e.jpg"
        ]
        
        image_path = None
        for path in test_images:
            if Path(path).exists():
                image_path = path
                break
        
        if not image_path:
            print("\n⚠️ Aucune image de test trouvée")
            print("   Usage: python test_api.py <chemin_image>")
            sys.exit(0)
    
    if test_generate(image_path):
        print("\n✅ Tous les tests passés!")
        sys.exit(0)
    else:
        print("\n❌ Tests échoués")
        sys.exit(1)

if __name__ == "__main__":
    main()
