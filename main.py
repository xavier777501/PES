"""
PES Face UV Generator - FastAPI Backend
Utilise le code Python exact qui marche déjà (main.py)
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import cv2
import numpy as np
import os
import tempfile
import shutil
from pathlib import Path

from face_generator import generate_pes_face

app = FastAPI(
    title="PES Face UV API",
    description="API Python pour générer des textures UV PES avec précision maximale",
    version="1.0.0"
)

# CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod: mettre l'URL du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dossier pour les fichiers temporaires
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

# Dossier des templates
TEMPLATES_DIR = Path("templates")
TEMPLATES = []

# Charger les templates au démarrage
@app.on_event("startup")
async def load_templates():
    global TEMPLATES
    if TEMPLATES_DIR.exists():
        TEMPLATES = [
            str(p) for p in TEMPLATES_DIR.glob("*.png")
        ] + [
            str(p) for p in TEMPLATES_DIR.glob("*.jpg")
        ]
        print(f"✅ {len(TEMPLATES)} templates chargés")
    else:
        print("⚠️ Dossier templates/ non trouvé")


@app.get("/")
async def root():
    """Point d'entrée de l'API"""
    return {
        "service": "PES Face UV Generator",
        "version": "1.0.0",
        "status": "running",
        "templates_loaded": len(TEMPLATES),
        "endpoints": {
            "generate": "/api/generate-face",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check pour monitoring"""
    return {
        "status": "healthy",
        "templates": len(TEMPLATES)
    }


@app.post("/api/generate-face")
async def generate_face(
    image: UploadFile = File(..., description="Photo du visage (JPG/PNG)"),
    template_id: int = 0
):
    """
    Génère une texture UV PES depuis une photo.
    
    - **image**: Photo du visage (JPG ou PNG)
    - **template_id**: Index du template à utiliser (0-8, défaut: auto)
    
    Retourne: JSON avec image base64 + métadonnées
    """
    
    # Validation du fichier
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, "Le fichier doit être une image")
    
    # Créer un nom de fichier unique
    import uuid
    import base64
    unique_id = str(uuid.uuid4())
    
    # Sauvegarder l'image uploadée temporairement
    input_path = TEMP_DIR / f"{unique_id}_input.jpg"
    output_path = TEMP_DIR / f"{unique_id}_output.png"
    
    try:
        # Sauvegarder le fichier uploadé
        with input_path.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        
        # Vérifier que c'est une image valide
        img = cv2.imread(str(input_path))
        if img is None:
            raise HTTPException(400, "Image invalide ou corrompue")
        
        source_height, source_width = img.shape[:2]
        
        # Appeler le générateur (TON CODE PYTHON EXACT)
        templates = TEMPLATES if TEMPLATES else [str(input_path)]
        
        result = generate_pes_face(
            str(input_path),
            templates,
            str(output_path)
        )
        
        if not result or not isinstance(result, tuple):
            raise HTTPException(500, "Erreur lors de la génération")
        
        success, generated_path = result
        
        if not success:
            # Mode fallback : pas de visage détecté
            # TODO: Implémenter le fallback mode si nécessaire
            raise HTTPException(
                400, 
                "Aucun visage détecté. Essayez avec une photo plus claire ou frontale."
            )
        
        # Lire l'image générée et la convertir en base64
        with open(generated_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Retourner JSON avec l'image en base64
        return JSONResponse({
            "success": True,
            "image": f"data:image/png;base64,{image_base64}",
            "mode": "landmarked",
            "source_width": source_width,
            "source_height": source_height,
            "fidelity": 0.85,  # TODO: Calculer la vraie fidélité
            "error": 5.0,  # TODO: Calculer la vraie erreur RMSD
            "template_index": 0,  # TODO: Retourner le vrai template utilisé
            "blend_alpha": 0.0
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_message": str(e)
            }
        )
    finally:
        # Nettoyer les fichiers temporaires
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()


@app.post("/api/render-sketch")
async def render_sketch(request: dict):
    """
    Génère une texture UV depuis un croquis dessiné.
    
    Body JSON:
    {
        "strokes": [
            {
                "color": "#000000",
                "width": 6,
                "erase": false,
                "points": [x1, y1, x2, y2, ...]
            }
        ]
    }
    
    Retourne: JSON avec image base64
    """
    import base64
    import uuid
    
    try:
        strokes = request.get("strokes", [])
        if not strokes:
            raise HTTPException(400, "Aucun trait dessiné")
        
        # Créer une image 512×512 blanche
        canvas = np.ones((512, 512, 3), dtype=np.uint8) * 248  # Gris très clair
        
        # Dessiner chaque stroke
        for stroke in strokes:
            color_hex = stroke.get("color", "#000000")
            # Convertir hex en BGR pour OpenCV
            color_hex = color_hex.lstrip('#')
            r, g, b = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
            color_bgr = (b, g, r)
            
            width = int(stroke.get("width", 6))
            erase = stroke.get("erase", False)
            points = stroke.get("points", [])
            
            if len(points) < 4:
                continue
            
            # Convertir les points en liste de tuples (x, y)
            pts = [(int(points[i]), int(points[i+1])) for i in range(0, len(points)-1, 2)]
            
            # Dessiner le trait
            for i in range(len(pts) - 1):
                if erase:
                    cv2.line(canvas, pts[i], pts[i+1], (248, 248, 248), width, cv2.LINE_AA)
                else:
                    cv2.line(canvas, pts[i], pts[i+1], color_bgr, width, cv2.LINE_AA)
        
        # Sauvegarder temporairement
        unique_id = str(uuid.uuid4())
        output_path = TEMP_DIR / f"{unique_id}_sketch.png"
        cv2.imwrite(str(output_path), canvas)
        
        # Convertir en base64
        with open(output_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Nettoyer
        output_path.unlink()
        
        return JSONResponse({
            "success": True,
            "image": f"data:image/png;base64,{image_base64}",
            "mode": "sketch"
        })
        
    except Exception as e:
        print(f"❌ Erreur sketch: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_message": str(e)
            }
        )


@app.delete("/api/cleanup/{file_id}")
async def cleanup(file_id: str):
    """Nettoie les fichiers temporaires après téléchargement"""
    try:
        output_path = TEMP_DIR / f"{file_id}_output.png"
        if output_path.exists():
            output_path.unlink()
        return {"status": "cleaned"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
