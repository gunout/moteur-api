import asyncio
import csv
import io
import httpx
from typing import Optional, Literal
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Meta-moteur data.gouv.fr")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_V1 = "https://www.data.gouv.fr/api/1"
BASE_V2 = "https://www.data.gouv.fr/api/2"
BASE_TABULAR = "https://tabular-api.data.gouv.fr/api"
TIMEOUT = httpx.Timeout(10.0)
DATAGOUV_WEB = "https://www.data.gouv.fr"


# ---------------------------------------------------------------------------
# Cache en mémoire : slug d'organisation → ID technique
# ---------------------------------------------------------------------------
_ORG_ID_CACHE: dict[str, str] = {}


async def resolve_org_id(client: httpx.AsyncClient, slug_or_id: str) -> Optional[str]:
    """
    Convertit un slug d'organisation en ID technique (24 chars hex).
    Si la valeur est déjà un ID, la renvoie telle quelle.
    Résultat mis en cache pour éviter de refaire l'appel.
    """
    # Déjà un ID ?
    if len(slug_or_id) == 24 and all(c in "0123456789abcdef" for c in slug_or_id.lower()):
        return slug_or_id

    # Cache ?
    if slug_or_id in _ORG_ID_CACHE:
        return _ORG_ID_CACHE[slug_or_id]

    # Appel API v1 pour récupérer l'organisation par son slug
    try:
        r = await client.get(f"{BASE_V1}/organizations/{slug_or_id}/")
        if r.status_code == 200:
            data = r.json()
            org_id = data.get("id")
            if org_id:
                _ORG_ID_CACHE[slug_or_id] = org_id
                return org_id
    except Exception as e:
        print(f"[resolve_org_id] erreur sur {slug_or_id}: {e}")

    return None


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def compute_popularity(item: dict) -> int:
    m = item.get("metrics") or {}
    views = m.get("views", 0) or 0
    downloads = m.get("resources_downloads", 0) or 0
    reuses = m.get("reuses", 0) or 0
    followers = m.get("followers", 0) or 0
    return views + downloads * 2 + reuses * 5 + followers * 3


def normalize_url(item: dict) -> Optional[str]:
    if item.get("url"):
        return item["url"]
    id_ = item.get("id")
    if not id_:
        return None
    kind = "dataservices" if item.get("type") == "dataservice" else "datasets"
    return f"{DATAGOUV_WEB}/{kind}/{id_}"


def deduplicate(results: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    priority = {"v2": 0, "dataservices": 1, "v1": 2}
    for r in results:
        if "error" in r or not r.get("id"):
            continue
        existing = by_id.get(r["id"])
        if not existing:
            by_id[r["id"]] = r
        else:
            if priority[r["source"]] < priority[existing["source"]]:
                r.setdefault("also_in", []).append(existing["source"])
                by_id[r["id"]] = r
            else:
                existing.setdefault("also_in", []).append(r["source"])
    return list(by_id.values())


def sort_results(items: list[dict], sort: str) -> list[dict]:
    if sort == "popularity":
        items.sort(key=lambda x: x.get("popularity", 0), reverse=True)
    elif sort == "recent":
        items.sort(key=lambda x: x.get("last_update") or "", reverse=True)
    return items


def clean_item(item: dict) -> dict:
    item = dict(item)
    item["url"] = normalize_url(item)
    return item


# ---------------------------------------------------------------------------
# Connecteurs API data.gouv.fr
# ---------------------------------------------------------------------------

async def search_datasets_v1(client, q, page, page_size, organization=None):
    try:
        params = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        if organization:
            org_id = await resolve_org_id(client, organization)
            if org_id:
                params["organization"] = org_id
        r = await client.get(f"{BASE_V1}/datasets/", params=params)
        r.raise_for_status()
        data = r.json()
        return [
            {
                "id": d.get("id"),
                "titre": d.get("title"),
                "description": (d.get("description") or "")[:280],
                "organisation": (d.get("organization") or {}).get("name"),
                "url": d.get("page"),
                "source": "v1",
                "type": "dataset",
                "tags": d.get("tags", []),
                "last_update": d.get("last_update"),
                "popularity": 0,
                "metrics": None,
            }
            for d in data.get("data", [])
        ]
    except Exception as e:
        return [{"error": f"v1: {e}"}]


async def search_datasets_v2(client, q, page, page_size, organization, access_type, last_update):
    params = {"page": page, "page_size": page_size}
    if q:
        params["q"] = q
    # ⭐ CORRECTIF CLÉ : convertir le slug en ID
    if organization:
        org_id = await resolve_org_id(client, organization)
        if org_id:
            params["organization"] = org_id
    if access_type:
        params["access_type"] = access_type
    if last_update:
        params["last_update"] = last_update

    try:
        r = await client.get(f"{BASE_V2}/datasets/search/", params=params)
        r.raise_for_status()
        data = r.json()
        out = []
        for d in data.get("data", []):
            item = {
                "id": d.get("id"),
                "titre": d.get("title"),
                "description": (d.get("description") or "")[:280],
                "organisation": (d.get("organization") or {}).get("name"),
                "url": d.get("page"),
                "source": "v2",
                "type": "dataset",
                "tags": d.get("tags", []),
                "last_update": d.get("last_update"),
                "metrics": d.get("metrics"),
            }
            item["popularity"] = compute_popularity(item)
            out.append(item)
        return out
    except Exception as e:
        return [{"error": f"v2: {e}"}]


async def search_dataservices(client, q, page, page_size):
    try:
        params = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        r = await client.get(f"{BASE_V2}/dataservices/search/", params=params)
        r.raise_for_status()
        data = r.json()
        out = []
        for d in data.get("data", []):
            item = {
                "id": d.get("id"),
                "titre": d.get("title"),
                "description": (d.get("description") or "")[:280],
                "organisation": (d.get("organization") or {}).get("name"),
                "url": d.get("page"),
                "source": "dataservices",
                "type": "dataservice",
                "tags": d.get("tags", []),
                "last_update": d.get("last_update"),
                "metrics": d.get("metrics"),
            }
            item["popularity"] = compute_popularity(item)
            out.append(item)
        return out
    except Exception as e:
        return [{"error": f"dataservices: {e}"}]


# ---------------------------------------------------------------------------
# Cœur du méta-moteur
# ---------------------------------------------------------------------------

async def run_search(
    q: str,
    page: int,
    page_size: int,
    type_: str,
    organization: Optional[str],
    access_type: Optional[str],
    last_update: Optional[str],
    sort: str,
):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        tasks, labels = [], []

        # Si un filtre organization est fourni, seule la v2 le gère correctement.
        if organization:
            tasks.append(search_datasets_v2(
                client, q, page, page_size, organization, access_type, last_update
            ))
            labels.append("v2")
        else:
            if type_ in ("dataset", "all"):
                tasks.append(search_datasets_v1(client, q, page, page_size))
                labels.append("v1")
                tasks.append(search_datasets_v2(
                    client, q, page, page_size, organization, access_type, last_update
                ))
                labels.append("v2")
            if type_ in ("dataservice", "all"):
                tasks.append(search_dataservices(client, q, page, page_size))
                labels.append("dataservices")

        responses = await asyncio.gather(*tasks)

    buckets = dict(zip(labels, responses))
    v1 = buckets.get("v1", [])
    v2 = buckets.get("v2", [])
    ds = buckets.get("dataservices", [])

    errors = [x["error"] for x in (v1 + v2 + ds) if isinstance(x, dict) and "error" in x]
    merged = deduplicate(v1 + v2 + ds)
    merged = sort_results(merged, sort)
    merged = [clean_item(x) for x in merged]
    return merged, errors


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/search")
async def search(
    q: str = Query("", description="Mot-clé (peut être vide si un filtre est appliqué)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    organization: Optional[str] = None,
    access_type: Optional[str] = Query(None, pattern="^(open|restricted)$"),
    last_update: Optional[str] = Query(
        None, pattern="^(last_30_days|last_12_months|last_3_years)$"
    ),
    type: Optional[Literal["dataset", "dataservice", "all"]] = Query("all"),
    sort: Optional[Literal["relevance", "popularity", "recent"]] = Query("relevance"),
):
    items, errors = await run_search(
        q, page, page_size, type, organization, access_type, last_update, sort
    )

    return JSONResponse(
        {
            "query": q,
            "type": type,
            "sort": sort,
            "page": page,
            "page_size": page_size,
            "count": len(items),
            "results": items,
            "errors": errors or None,
        }
    )


@app.get("/export")
async def export(
    q: str = Query("", description="Mot-clé (peut être vide si un filtre est appliqué)"),
    format: Literal["csv", "json"] = Query("csv"),
    max_pages: int = Query(3, ge=1, le=10),
    page_size: int = Query(50, ge=1, le=100),
    type: Optional[Literal["dataset", "dataservice", "all"]] = Query("all"),
    sort: Optional[Literal["relevance", "popularity", "recent"]] = Query("popularity"),
    organization: Optional[str] = None,
    access_type: Optional[str] = Query(None, pattern="^(open|restricted)$"),
    last_update: Optional[str] = Query(
        None, pattern="^(last_30_days|last_12_months|last_3_years)$"
    ),
):
    all_items: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []

    for p in range(1, max_pages + 1):
        items, errs = await run_search(
            q, p, page_size, type, organization, access_type, last_update, sort
        )
        errors.extend(errs)
        new_items = [it for it in items if it["id"] not in seen]
        for it in new_items:
            seen.add(it["id"])
        all_items.extend(new_items)
        if len(items) < page_size:
            break

    export_items = []
    for it in all_items:
        export_items.append({
            "id": it.get("id"),
            "titre": it.get("titre"),
            "type": it.get("type"),
            "source": it.get("source"),
            "organisation": it.get("organisation"),
            "url": it.get("url"),
            "tags": ", ".join(it.get("tags") or []),
            "last_update": it.get("last_update"),
            "popularity": it.get("popularity"),
            "description": it.get("description"),
        })

    if format == "json":
        return JSONResponse(
            {
                "query": q,
                "total": len(export_items),
                "errors": errors or None,
                "results": export_items,
            }
        )

    def generate_csv():
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "id", "titre", "type", "source", "organisation",
                "url", "tags", "last_update", "popularity", "description",
            ],
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for it in export_items:
            writer.writerow(it)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    filename = f"datagouv_{(q or 'export').replace(' ', '_')[:40]}.csv"
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/tabular/{dataset_id}")
async def tabular_profile(dataset_id: str):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(f"{BASE_TABULAR}/datasets/{dataset_id}/profile/")
            r.raise_for_status()
            return JSONResponse(r.json())
        except httpx.HTTPStatusError as e:
            return JSONResponse(
                {"error": f"HTTP {e.response.status_code}", "detail": e.response.text[:300]},
                status_code=e.response.status_code,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/resolve-org/{slug}")
async def resolve_org(slug: str):
    """Endpoint utilitaire pour tester la résolution slug → ID."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        org_id = await resolve_org_id(client, slug)
    return {"slug": slug, "id": org_id, "cached": slug in _ORG_ID_CACHE}


@app.get("/")
async def root():
    return {
        "message": "Meta-moteur data.gouv.fr",
        "endpoints": {
            "search": "/search?q=transport&page=1&page_size=10&type=all&sort=popularity",
            "search_by_org": "/search?q=&organization=ministere-de-linterieur",
            "resolve_org": "/resolve-org/ministere-de-linterieur",
            "export_csv": "/export?q=transport&format=csv&max_pages=3",
            "export_json": "/export?q=transport&format=json&max_pages=3",
            "tabular": "/tabular/{dataset_id}",
        },
        "filters": {
            "type": ["dataset", "dataservice", "all"],
            "sort": ["relevance", "popularity", "recent"],
            "access_type": ["open", "restricted"],
            "last_update": ["last_30_days", "last_12_months", "last_3_years"],
        },
    }