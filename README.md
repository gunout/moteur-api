# 🔍 Méta-moteur data.gouv.fr

> Méta-moteur de recherche unifié pour interroger en parallèle les API publiques de [data.gouv.fr](https://www.data.gouv.fr).

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![DSFR](https://img.shields.io/badge/DSFR-1.11-000091?style=flat-square)](https://www.systeme-de-design.gouv.fr/)
[![Licence](https://img.shields.io/badge/Licence-etalab--2.0-blue?style=flat-square)](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)
[![Statut](https://img.shields.io/badge/Statut-actif-success?style=flat-square)]()

---

## 📖 Présentation

**Méta-moteur data.gouv.fr** est une application qui agrège en temps réel les résultats de **trois sources officielles** de la plateforme data.gouv.fr :

| Source | Rôle |
| :--- | :--- |
| **API Catalogue v1** | Catalogue historique des jeux de données |
| **API Catalogue v2** | Moteur du site actuel (métriques, qualité, filtres avancés) |
| **API Dataservices** | Recensement des API publiques publiées sur la plateforme |

Les résultats sont **dédoublonnés**, **normalisés** et **triés** selon plusieurs critères (pertinence, popularité, récence), puis exposés via une **interface web au design Marianne** (DSFR).

---

## 📸 Captures d'écran

### Interface de recherche

![Recherche "transport" triée par popularité](<img width="1644" height="6458" alt="Screenshot 2026-09-28 at 02-10-10 Méta-moteur data gouv fr" src="https://github.com/user-attachments/assets/c5ea1588-2198-4b83-908b-24dd8fdaf4ca" />
)

*Résultats de la recherche « transport » triés par popularité, avec le score calculé à partir des métriques v2.*

### Filtres par organisation et tags

![Filtres actifs dans la sidebar](<img width="1644" height="6458" alt="Screenshot 2026-09-28 at 02-02-15 Méta-moteur data gouv fr" src="https://github.com/user-attachments/assets/115f0671-84f6-4357-90b7-3f62b4ca5bd1" />
)

*Filtres client par organisation et par tag, avec chips actives retirables d'un clic.*

### Mode sombre

![Interface en mode sombre](<img width="1644" height="6458" alt="Screenshot 2026-09-28 at 02-10-10 Méta-moteur data gouv fr" src="https://github.com/user-attachments/assets/4a632c1d-03b6-4f23-acd8-d9aede9f7c03" />
)

*Basculement en mode sombre persistant, conforme au DSFR.*

### Export CSV

![Export CSV des résultats](<img width="1644" height="6458" alt="Screenshot 2026-09-28 at 02-12-39 Méta-moteur data gouv fr" src="https://github.com/user-attachments/assets/063fb24f-0ff1-4ab0-b10f-d4f6b1558a7b" />
)

*Export CSV en streaming des résultats agrégés sur plusieurs pages.*

---

## ✨ Fonctionnalités

- 🔎 **Recherche multi-sources** en parallèle (v1, v2, dataservices)
- 🧩 **Dédoublonnage intelligent** avec traçabilité des sources multiples
- 📊 **Score de popularité** calculé à partir des métriques (vues, téléchargements, réutilisations, abonnés)
- 🎛️ **Filtres** : type (`dataset`, `dataservice`), organisation, type d'accès, récence
- 🔀 **Tris** : pertinence, popularité, récence
- 📄 **Pagination** unifiée
- 📤 **Export CSV / JSON** en streaming
- 🗂️ **Profil tabulaire** d'un dataset via l'API Tabulaire
- 🎨 **Interface Marianne** (DSFR) avec mode sombre persistant
- 🏷️ **Filtres client** par organisation et tags avec chips actives
- ♿ **Accessibilité** conforme au DSFR (labels, `aria-live`, contrastes)

---

## 🏗️ Architecture

```
moteur-api/
├── main.py              # Backend FastAPI (méta-moteur)
├── index.html           # Frontend Marianne (DSFR)
├── requirements.txt     # Dépendances Python
├── LICENSE              # Licence etalab-2.0
├── README.md
└── docs/
    └── screenshots/     # Captures d'écran du README
```

### Flux de données

```
┌─────────────┐
│  Frontend   │  (index.html · DSFR)
│  Navigateur │
└──────┬──────┘
       │ fetch /search?q=...
       ▼
┌─────────────┐
│  FastAPI    │  (main.py · port 8001)
│  Backend    │
└──────┬──────┘
       │ asyncio.gather (requêtes parallèles)
       ├──────────────► API Catalogue v1
       ├──────────────► API Catalogue v2
       └──────────────► API Dataservices
       │
       ▼
┌─────────────┐
│  Fusion     │  dédoublonnage + normalisation + tri
│  Résultats  │
└─────────────┘
```

---

## 🚀 Installation

### Prérequis

- **Python 3.12+**
- **pip** et **venv**

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/gunout/moteur-api.git
cd moteur-api

# 2. Créer et activer un environnement virtuel
python3 -m venv Mapi
source Mapi/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le serveur
uvicorn main:app --reload --port 8001
```

Le serveur démarre sur **`http://127.0.0.1:8001`**.

> 💡 Si le port 8001 est occupé, utilisez `--port 8002` et adaptez la constante `API` dans `index.html`.

---

## 🖥️ Utilisation

### Interface web

Ouvrez dans votre navigateur :

```
http://127.0.0.1:8001/ui/index.html
```

Ou, si le montage `StaticFiles` n'est pas activé, ouvrez directement `index.html` (CORS est déjà configuré).

### API REST

| Méthode | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Documentation des endpoints |
| `GET` | `/search` | Recherche multi-sources |
| `GET` | `/export` | Export CSV ou JSON |
| `GET` | `/tabular/{dataset_id}` | Profil tabulaire d'un dataset |

### Exemples

```bash
# Recherche simple
curl "http://127.0.0.1:8001/search?q=transport"

# Recherche d'API uniquement, triée par popularité
curl "http://127.0.0.1:8001/search?q=finance&type=dataservice&sort=popularity"

# Recherche récente, filtrée par organisation
curl "http://127.0.0.1:8001/search?q=logement&organization=insee&last_update=last_12_months"

# Export CSV (téléchargement direct)
curl -o resultats.csv "http://127.0.0.1:8001/export?q=transport&format=csv&max_pages=3"

# Profil tabulaire d'un dataset
curl "http://127.0.0.1:8001/tabular/53699d0ea3a729239d205b2e"
```

---

## 📚 Paramètres de l'API

### `/search`

| Paramètre | Type | Valeurs | Défaut | Description |
| :--- | :--- | :--- | :--- | :--- |
| `q` | string | — | *requis* | Mot-clé de recherche |
| `page` | int | ≥ 1 | `1` | Numéro de page |
| `page_size` | int | 1–50 | `10` | Résultats par page |
| `type` | enum | `dataset`, `dataservice`, `all` | `all` | Type de résultat |
| `sort` | enum | `relevance`, `popularity`, `recent` | `relevance` | Tri |
| `organization` | string | — | — | Slug de l'organisation |
| `access_type` | enum | `open`, `restricted` | — | Type d'accès |
| `last_update` | enum | `last_30_days`, `last_12_months`, `last_3_years` | — | Récence |

### `/export`

| Paramètre | Type | Valeurs | Défaut | Description |
| :--- | :--- | :--- | :--- | :--- |
| `q` | string | — | *requis* | Mot-clé |
| `format` | enum | `csv`, `json` | `csv` | Format de sortie |
| `max_pages` | int | 1–10 | `3` | Pages agrégées |

---

## 🧪 Réponse type

```json
{
  "query": "transport",
  "type": "all",
  "sort": "popularity",
  "page": 1,
  "page_size": 10,
  "count": 10,
  "results": [
    {
      "id": "55e4129788ee386899a46ec1",
      "titre": "Transports",
      "description": "Ce jeu de données provient de la Banque de Données Macro-économiques…",
      "organisation": "Institut national de la statistique et des études économiques (Insee)",
      "url": "https://www.data.gouv.fr/datasets/transports",
      "source": "v2",
      "type": "dataset",
      "tags": ["automobiles", "carburant", "transports"],
      "last_update": "2026-07-10T05:07:36.139000+00:00",
      "popularity": 210000
    }
  ],
  "errors": null
}
```

---

## 🛠️ Stack technique

| Composant | Technologie |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, httpx (async), asyncio |
| **Frontend** | HTML5, CSS3, JavaScript vanilla, DSFR 1.11 |
| **API sources** | data.gouv.fr (v1, v2, dataservices, tabulaire) |
| **Design** | Système de Design de l'État (Marianne) |

---

## 📁 Structure du projet

```
.
├── main.py                     # Application FastAPI complète
├── index.html                  # Interface web (design Marianne)
├── requirements.txt            # Dépendances Python
├── LICENSE                     # Licence etalab-2.0
├── README.md                   # Ce fichier
├── docs/
│   └── screenshots/            # Captures d'écran
│       ├── 01-recherche.png
│       ├── 02-filtres.png
│       ├── 03-mode-sombre.png
│       └── 04-export-csv.png
└── Mapi/                       # Environnement virtuel (non versionné)
```

---

## 🤝 Contribution

Les contributions sont bienvenues. Pour proposer une amélioration :

1. Forkez le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Committez vos changements (`git commit -m 'Ajout de…'`)
4. Poussez la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

---

## 📜 Licence

Ce projet est distribué sous licence **etalab-2.0**, conformément à la politique d'ouverture des données publiques françaises.

Les données interrogées restent la propriété de leurs producteurs respectifs.

---

## 🔗 Ressources

- [data.gouv.fr](https://www.data.gouv.fr)
- [API data.gouv.fr — documentation](https://doc.data.gouv.fr/api/intro/)
- [Système de Design de l'État (DSFR)](https://www.systeme-de-design.gouv.fr/)
- [Licence etalab-2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)

---

<p align="center">
  <strong>République Française</strong><br>
  <em>Liberté · Égalité · Fraternité</em>
</p>
