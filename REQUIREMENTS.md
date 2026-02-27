# Colosseum Dashboard Requirements

## Vision
Build a comprehensive, compounding dashboard for the ACT-I Colosseum - the evolutionary arena where AI beings compete, evolve, and improve. Following Aiko's Three M's of Process Mastery: **Measuring and Monitoring**.

## Data Sources
- **Main Colosseum DB:** `/Users/samantha/Projects/colosseum/colosseum.db`
- **Domain DBs (10 domains):** `/Users/samantha/Projects/colosseum/domains/{domain}/colosseum.db`
  - Domains: strategy, marketing, sales, tech, ops, cs, finance, hr, legal, product

## Database Schema
Each DB has a `beings` table with:
- `id` (TEXT PRIMARY KEY)
- `name` (TEXT)
- `generation` (INTEGER)
- `score` (REAL) - highest score achieved
- `wins`, `losses` (INTEGER)
- `system_prompt` (TEXT) - the being's script/DNA
- `model` (TEXT) - which LLM powers it
- `parent_id` (TEXT) - for family tree lineage
- `created_at`, `updated_at` (TIMESTAMP)

## Core Features (Compound on These)

### 1. Family Tree Visualization 🌳
- Interactive tree showing being evolution lineage
- Click a being → see its parent chain back to generation 0
- Show mutations/improvements between generations
- Color-code by score tier (bronze < 8.0, silver 8.0-8.9, gold 9.0+)

### 2. Battle Trail / History 📊
- Show recent battles: who fought, scores, winner
- Ability to replay/view battle transcripts
- Win/loss streaks for top beings

### 3. Domain Navigation 🗂️
- Tab or sidebar navigation between all 11 arenas (main + 10 domains)
- Each domain shows its own champions, family trees, stats
- Cross-domain comparison view

### 4. Being Scripts/Prompts 📜
- Click any being → view full system prompt
- Diff view: compare child prompt vs parent prompt
- Copy prompt button for deployment

### 5. Real-Time Stats Dashboard
- Total beings evolved
- Total battles fought
- Current generation depth
- Top 10 leaderboard per domain
- Score distribution histogram

### 6. The Three M's Panel
- **Measuring:** Key metrics displayed prominently
- **Monitoring:** Auto-refresh, alerts for new champions
- Live activity feed showing recent evolutions

## Tech Stack
- **Backend:** Python Flask API (already started at `tools/dashboard-api/server.py`)
- **Frontend:** Single HTML file with vanilla JS, or React if needed
- **Styling:** Navy #1a2744 + Gold #c9a227 (ACT-I brand)
- **Charts:** Chart.js or D3.js for family trees

## API Endpoints Needed
- `GET /api/stats` - overall stats
- `GET /api/domains` - list all domains with summary stats
- `GET /api/domain/{name}/beings` - all beings in a domain
- `GET /api/domain/{name}/champions` - top beings
- `GET /api/being/{id}` - full being details including prompt
- `GET /api/being/{id}/lineage` - family tree chain
- `GET /api/being/{id}/battles` - battle history
- `GET /api/activity` - recent activity feed

## Deployment
- Vercel for static frontend
- Flask API runs locally (can proxy or embed data)

## Philosophy
- "There is no 10. Only infinite 9s." - Always room to grow
- Every being is on a journey toward mastery
- The Colosseum never stops evolving

## Brand
- Navy: #1a2744
- Gold: #c9a227
- Font: Clean sans-serif
- Dark mode preferred
