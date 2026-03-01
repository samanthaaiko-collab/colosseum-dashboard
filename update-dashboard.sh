#!/bin/bash
# Regenerate email-colosseum.html with live data from API
API="http://localhost:3347"
DATA=$(curl -s "$API/api/leaderboard")
STATS=$(curl -s "$API/api/stats")

if [ -z "$DATA" ] || [ "$DATA" = "" ]; then
    echo "API not responding, skipping update"
    exit 1
fi

BATTLES=$(echo "$STATS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_battles'])")
BEINGS=$(echo "$STATS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_beings'])")

# Update the stats in the HTML
python3 -c "
import json, re, sys

with open('email-colosseum.html', 'r') as f:
    html = f.read()

data = json.loads('''$DATA''')
stats = json.loads('''$STATS''')

# Update stat numbers
html = re.sub(r'(<div class=\"number\" id=\"totalBattles\">)\d+', r'\g<1>' + str(stats['total_battles']), html)
html = re.sub(r'(<div class=\"number\" id=\"totalBeings\">)\d+', r'\g<1>' + str(stats['total_beings']), html)

# Update champion cards with live data
top5 = data[:5]
ranks = ['gold', 'silver', 'bronze', '', '']
emojis = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']

# Build new champion cards
cards = ''
for i, d in enumerate(top5):
    cls = f' {ranks[i]}' if ranks[i] else ''
    wr = round(d['wins'] * 100 / max(d['wins'] + d['losses'], 1), 1)
    fill_cls = 'high' if wr >= 75 else 'mid' if wr >= 60 else 'low'
    cards += f'''
        <div class=\"champion-card{cls}\">
            <div class=\"rank\">{emojis[i]}</div>
            <div class=\"card-content\">
                <div class=\"subject-line\">\"{d['content']}\"</div>
                <div class=\"metrics\">
                    <div class=\"metric\"><span class=\"val\">{d['wins']}W-{d['losses']}L</span> <span class=\"lbl\">Record</span></div>
                    <div class=\"metric\"><span class=\"val\">{d['score']:.2f}</span> <span class=\"lbl\">Score</span></div>
                    <div class=\"metric\"><span class=\"val\">{wr}%</span> <span class=\"lbl\">Win Rate</span></div>
                </div>
                <div class=\"win-bar\"><div class=\"fill {fill_cls}\" style=\"width: {wr}%\"></div></div>
            </div>
        </div>
'''

# Replace champion section
html = re.sub(
    r'(<div class=\"champions\">.*?<h2>🏆 Current Champions</h2>)(.*?)(</div>\s*<div class=\"methodology\">)',
    r'\1' + cards + r'\3',
    html, flags=re.DOTALL
)

with open('email-colosseum.html', 'w') as f:
    f.write(html)
print(f'Updated: {stats[\"total_battles\"]} battles, {stats[\"total_beings\"]} beings')
"

# Push to git and deploy
cd /Users/samantha/.openclaw/workspace/colosseum-dashboard
git add email-colosseum.html
git commit -m "Auto-update Email Colosseum stats: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null
git push origin main 2>/dev/null
vercel --prod --token $VERCEL_TOKEN 2>/dev/null | tail -3
