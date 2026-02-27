# ACT-I Colosseum Dashboard

Comprehensive dashboard for ACT-I's evolutionary AI arena with:
- Family tree lineage visualization
- Battle trail/history views
- Domain navigation across main + 10 domains
- Being detail modal with full system prompt + parent diff
- Real-time stats + activity feed

## Files
- `server.py`: Flask API and snapshot exporter
- `index.html`: Single-page dashboard frontend
- `data/snapshot.json`: Static-mode dataset scaffold
- `vercel.json`: Static SPA routing for Vercel

## Database Configuration
Defaults are wired to the paths in `REQUIREMENTS.md`:
- Main DB: `/Users/samantha/Projects/colosseum/colosseum.db`
- Domain DB root: `/Users/samantha/Projects/colosseum/domains`

Override with env vars:
- `COLOSSEUM_MAIN_DB`
- `COLOSSEUM_DOMAINS_ROOT`
- `COLOSSEUM_DOMAIN_LIST` (comma-separated domain names)

## Run API Locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py --host 0.0.0.0 --port 5050
```

API endpoints:
- `GET /api/stats`
- `GET /api/domains`
- `GET /api/domain/{name}/beings`
- `GET /api/domain/{name}/champions`
- `GET /api/domain/{name}/battles`
- `GET /api/being/{id}`
- `GET /api/being/{id}/lineage`
- `GET /api/being/{id}/battles`
- `GET /api/activity`
- `GET /api/export`

## Static Export Option (Vercel-ready)
Generate a static snapshot JSON from local SQLite DBs:
```bash
python server.py --export data/snapshot.json --battle-limit 120
```

Then deploy the repository to Vercel as a static site. The dashboard will automatically:
- use live API (`/api`) when available
- fall back to `data/snapshot.json` when API is unavailable

You can force static mode with:
- `?static=1`

You can point UI to another API base with:
- `?api=https://your-api.example.com/api`
