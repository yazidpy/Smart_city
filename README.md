# Smart City Traffic Dashboard

Un système complet d’analyse de trafic urbain en temps réel basé sur l’IA (YOLOv8), avec un backend FastAPI et un frontend Next.js modernes.

---

## Table des matières

1. [Vue d’ensemble](#vue-densemble)
2. [Entraînement YOLOv8](#entraînement-yolov8)
3. [Architecture du projet](#architecture-du-projet)
4. [Installation](#installation)
5. [Utilisation](#utilisation)
6. [Déploiement](#déploiement)
7. [Performance et optimisations](#performance-et-optimisations)
8. [API](#api)
9. [Contributions](#contributions)

---

## Vue d’ensemble

Le projet permet de :
- Détecter et suivre des objets (personnes, voitures, bus, camions, motos, vélos) dans des flux vidéo
- Afficher des métriques en temps réel (nombre d’objets par classe, état du trafic)
- Gérer plusieurs caméras (IP locales ou URLs distantes)
- Visualiser les flux vidéo MJPEG optimisés pour CPU bas de gamme

---

## Entraînement YOLOv8

### Dataset

- **Source** : images de trafic urbain annotées
- **Classes** : 6 catégories
  - `0: Person`
  - `1: Bicycle`
  - `2: Car`
  - `3: Motorcycle`
  - `4: Bus`
  - `5: Truck`

### Configuration

- **Modèle** : YOLOv8 nano (`yolov8n.pt`)
- **Résolution** : 640×640
- **Batch size** : 16
- **Époques** : 100
- **Optimiseur** : SGD
- **Learning rate** : 0.01
- **Augmentations** : flip, scale, hue, saturation

### Résultats

Après 100 époques sur `Train/detect/train3/` :

```
mAP50: 0.78
mAP50-95: 0.52
Précision moyenne : 81%
Rappel moyen : 76%

```

Le modèle atteint une bonne détection sur les scènes de trafic urbain, même avec des objets partiellement occultés.

---

## Architecture du projet

```
Smart_City/
├── backend/                 # FastAPI + OpenCV + YOLO
│   ├── main.py             # Serveur API + endpoints
│   ├── pipeline.py         # Pipeline vidéo + inférence YOLO
│   ├── models.py           # SQLite + CRUD caméras
│   ├── video_test/         # Vidéos de test (.mp4)
│   └── requirements.txt
├── frontend/               # Next.js + Tailwind + shadcn/ui
│   ├── src/app/(app)/
│   │   ├── dashboard/      # Tableau de bord
│   │   ├── streaming/      # Flux vidéo + sélection
│   │   ├── cameras/        # CRUD caméras
│   │   └── layout.tsx      # Sidebar + dark mode
│   ├── src/components/
│   │   ├── ui/             # Composants réutilisables
│   │   └── theme-provider.tsx
│   ├── package.json
│   └── tailwind.config.ts
├── Train/                  # Résultats entraînement YOLO
│   └── detect/train3/weights/best.pt
├── DEPLOY.md               # Guide déploiement
├── docker-compose.yml
└── README.md
```

---

## Installation

### Prérequis

- Python 3.10+
- Node.js 18+
- Docker (optionnel, pour déploiement)

### Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
---

## Utilisation

### 1. Lancement

- Backend : http://localhost:8000
- Frontend : http://localhost:3000
- Documentation API : http://localhost:8000/docs

### 2. Pages

- **Dashboard** (`/dashboard`) : KPIs, graphiques, état du trafic
- **Streaming** (`/streaming`) : flux vidéo MJPEG, sélection caméra/vidéo
- **Caméras** (`/cameras`) : CRUD caméras, zones (ROI)

### 3. Ajouter une caméra

1. Aller dans `/cameras`
2. Remplir :
   - Nom
   - URL source (RTSP, HTTP, ou chemin local)
   - Nom de la zone (optionnel)
3. Cliquer **Ajouter**


---


## API

### Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/cameras` | Lister les caméras |
| POST | `/api/cameras` | Créer une caméra |
| GET | `/api/cameras/{id}` | Détails caméra |
| DELETE | `/api/cameras/{id}` | Supprimer caméra |
| POST | `/api/cameras/{id}/select` | Sélectionner caméra active |
| GET | `/api/videos` | Lister vidéos de test |
| POST | `/api/videos/select` | Choisir une vidéo |
| GET | `/video_feed` | Flux MJPEG |
| WebSocket | `/ws` | Métriques temps réel |