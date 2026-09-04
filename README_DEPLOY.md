# 🚀 Déploiement sur Render.com

## ✅ Fichiers configurés

- `requirements.txt` → Dépendances Python optimisées pour le cloud
- `render.yaml` → Configuration automatique Render
- `.gitignore` → Ignore les fichiers inutiles

## 📋 Étapes de déploiement

### 1️⃣ Créer un compte GitHub (si pas déjà fait)

1. Va sur : https://github.com/
2. Sign up (gratuit)
3. Vérifie ton email

### 2️⃣ Upload le backend sur GitHub

**Option A : GitHub Desktop (Recommandé - Plus facile)**

1. Télécharge : https://desktop.github.com/
2. Installe et connecte-toi avec ton compte GitHub
3. File > Add Local Repository
4. Choisis le dossier : `d:\pes\pes-pwa\backend`
5. Clic "Publish repository"
   - Nom : `pes-face-backend`
   - Description : "Backend Python pour PES Face UV"
   - ☑️ Keep this code private
6. Clic "Publish repository"

**Option B : Git en ligne de commande**

```bash
cd d:\pes\pes-pwa\backend

# Initialiser Git
git init

# Ajouter tous les fichiers
git add .

# Premier commit
git commit -m "Backend PES Face UV ready for Render"

# Créer un repo sur GitHub.com puis connecter :
git remote add origin https://github.com/TON_USERNAME/pes-face-backend.git
git branch -M main
git push -u origin main
```

### 3️⃣ Déployer sur Render.com

1. **Créer un compte Render**
   - Va sur : https://render.com/
   - Clic "Get Started"
   - Sign up avec GitHub (recommandé)

2. **Créer un nouveau Web Service**
   - Dashboard > "New +" > "Web Service"
   - Clic "Connect" à côté de ton repo `pes-face-backend`
   - Si tu ne le vois pas, clic "Configure account" et autorise Render

3. **Configuration automatique**
   - Render détecte `render.yaml` automatiquement
   - Vérifie les settings :
     - **Name** : `pes-face-backend`
     - **Environment** : `Python 3`
     - **Build Command** : `pip install -r requirements.txt`
     - **Start Command** : `uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Plan** : `Free`

4. **Créer le service**
   - Clic "Create Web Service"
   - ⏱️ Attends 5-10 minutes (première fois)

5. **Récupérer l'URL**
   - Une fois déployé (status "Live"), copie l'URL
   - Format : `https://pes-face-backend.onrender.com`

### 4️⃣ Configurer l'app mobile

**Dans le frontend** :

```bash
cd d:\pes\pes-pwa\frontend

# Modifier .env.local
notepad .env.local
```

**Remplace par ton URL Render** :
```
NEXT_PUBLIC_API_URL=https://pes-face-backend.onrender.com
```

**Rebuild l'APK** :
```bash
npm run build
cd android
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-21.0.5.11-hotspot"
$env:GRADLE_USER_HOME = "C:\Users\GENESYS\.gradle"
.\gradlew assembleDebug
```

**Installe le nouvel APK** sur ton téléphone.

### 5️⃣ Tester

1. Ouvre l'app sur ton téléphone
2. Clique "Choisir une photo"
3. ✅ Ça marche avec 4G/5G/WiFi !

## ⚠️ Important : Limitations du plan gratuit Render

- ⏱️ **Cold start** : Si pas utilisé pendant 15 minutes, le service se met en veille
  - Premier appel après veille = 30-60 secondes
  - Appels suivants = rapides
- 📊 **750 heures/mois** gratuites (suffisant pour usage personnel)
- 💾 **Stockage temporaire** : Les fichiers uploadés sont supprimés au redémarrage

## 🔧 Dépannage

### Service ne démarre pas
- Vérifie les logs dans Render Dashboard
- Vérifie que `requirements.txt` est correct
- Vérifie que les templates sont présents

### "Failed to fetch" dans l'app
- Vérifie que l'URL dans `.env.local` est correcte
- Vérifie que le service Render est "Live" (pas "Deploying")
- Teste l'URL dans navigateur : `https://ton-url.onrender.com/health`

### Génération lente
- Normal la première fois (cold start)
- Ensuite plus rapide

## 🎯 Résultat final

✅ Backend Python sur le cloud  
✅ Accessible partout (4G/5G/WiFi)  
✅ Pas besoin du PC allumé  
✅ URL fixe (pas de rebuild APK)  
✅ Gratuit  

---

**Prochaine étape** : Upload sur GitHub puis déploie sur Render !
