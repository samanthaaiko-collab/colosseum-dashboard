#!/bin/bash
# Update both main colosseum and email colosseum dashboards
set -e

cd /Users/samantha/.openclaw/workspace/colosseum-dashboard

# 1. Export main colosseum data
echo "Exporting main colosseum..."
curl -s http://localhost:5050/api/export | python3 -c "
import json, sys
data = json.load(sys.stdin)
stats = data.get('stats', {})
domains = stats.get('domains', [])
trimmed = {
    'stats': {
        'total_beings': sum(d.get('beings_count', 0) for d in domains),
        'total_battles': sum(d.get('battle_count', 0) for d in domains),
        'total_domains': stats.get('active_domains', 11),
        'max_generation': max((d.get('generation_depth', 0) for d in domains), default=0),
        'generated_at': data.get('generated_at', '')
    },
    'domains': [{
        'name': d['name'],
        'beings_count': d.get('beings_count', 0),
        'generation_depth': d.get('generation_depth', 0),
        'avg_score': d.get('avg_score', 0),
        'battle_count': d.get('battle_count', 0),
        'champion_name': d.get('champion', {}).get('name', 'Unknown'),
        'champion_score': d.get('champion', {}).get('score', 0),
    } for d in domains]
}
json.dump(trimmed, open('data/main_trimmed.json', 'w'), indent=2)
print(f'Main: {trimmed[\"stats\"][\"total_beings\"]} beings, {trimmed[\"stats\"][\"total_battles\"]} battles')
" || echo "Main export failed"

# 2. Export email colosseum data
echo "Exporting email colosseum..."
curl -s http://localhost:3347/api/leaderboard > data/email_leaderboard.json
curl -s http://localhost:3347/api/stats > data/email_stats.json

# 3. Update email-colosseum.html with live data
bash update-dashboard.sh 2>/dev/null

echo "All exports complete. Deploying..."

# 4. Git commit and deploy
git add -A
git commit -m "Auto-update all dashboards: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || true
git push origin main 2>/dev/null || true
vercel --prod --token $VERCEL_TOKEN 2>/dev/null | tail -3

echo "Done!"
