#!/usr/bin/env python3
"""
Email/Ad Colosseum Battle Engine v1.0
Pre-tests email subjects, copy, and ads against AI personas
"""

import sqlite3
import json
import os
import random
from openai import OpenAI
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'email_ad.db')

# Load API key from .env
def load_env():
    env_path = '/Users/samantha/.openclaw/workspace-forge/.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v

load_env()
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

SCORING_DIMENSIONS = ['curiosity', 'relevance', 'credibility', 'urgency', 'clarity']

def get_db():
    return sqlite3.connect(DB_PATH)

def get_random_persona(category=None):
    """Get a random persona, optionally filtered by category"""
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM personas WHERE category = ? ORDER BY RANDOM() LIMIT 1", (category,))
    else:
        cursor.execute("SELECT * FROM personas ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0], 'name': row[1], 'category': row[2], 'archetype': row[3],
            'description': row[4], 'behavior_traits': json.loads(row[5]), 
            'scoring_weights': json.loads(row[6])
        }
    return None

def get_being(being_id):
    """Get a being by ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM beings WHERE id = ?", (being_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0], 'type': row[1], 'content': row[2], 'parent_id': row[3],
            'generation': row[4], 'score': row[5], 'wins': row[6], 'losses': row[7]
        }
    return None

def run_battle(being_a_id, being_b_id, persona_id=None, battle_type='subject_line'):
    """Run a head-to-head battle between two beings"""
    being_a = get_being(being_a_id)
    being_b = get_being(being_b_id)
    
    if not being_a or not being_b:
        raise ValueError("Both beings must exist")
    
    # Get persona (random if not specified)
    if persona_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM personas WHERE id = ?", (persona_id,))
        row = cursor.fetchone()
        conn.close()
        persona = {
            'id': row[0], 'name': row[1], 'category': row[2], 'archetype': row[3],
            'description': row[4], 'behavior_traits': json.loads(row[5]),
            'scoring_weights': json.loads(row[6])
        }
    else:
        persona = get_random_persona()
    
    # Build the judge prompt
    prompt = build_judge_prompt(being_a, being_b, persona, battle_type)
    
    # Get judgment from LLM
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    result = parse_judgment(response.choices[0].message.content)
    
    # Determine winner
    score_a = calculate_weighted_score(result['scores_a'], persona['scoring_weights'])
    score_b = calculate_weighted_score(result['scores_b'], persona['scoring_weights'])
    
    winner_id = being_a_id if score_a > score_b else being_b_id
    
    # Record battle
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO battles (being_a_id, being_b_id, winner_id, persona_id, battle_type, scores_a, scores_b, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (being_a_id, being_b_id, winner_id, persona['id'], battle_type,
          json.dumps(result['scores_a']), json.dumps(result['scores_b']), result['reasoning']))
    
    # Update being stats
    cursor.execute("UPDATE beings SET wins = wins + 1, score = score + 0.1 WHERE id = ?", (winner_id,))
    loser_id = being_b_id if winner_id == being_a_id else being_a_id
    cursor.execute("UPDATE beings SET losses = losses + 1, score = score - 0.05 WHERE id = ?", (loser_id,))
    
    conn.commit()
    conn.close()
    
    return {
        'winner_id': winner_id,
        'score_a': score_a,
        'score_b': score_b,
        'persona': persona['name'],
        'reasoning': result['reasoning']
    }

def build_judge_prompt(being_a, being_b, persona, battle_type):
    """Build the LLM prompt for judging"""
    traits = ', '.join([f"{k}: {v}" for k, v in persona['behavior_traits'].items()])
    
    type_context = {
        'subject_line': 'email subject line (deciding whether to open)',
        'email_copy': 'full email (deciding whether to read and click the CTA)',
        'ad_creative': 'ad (deciding whether to stop scrolling and click)'
    }
    
    return f"""You are {persona['name']}, a {persona['description']}.

Your behavioral traits: {traits}

You just received two {type_context.get(battle_type, 'marketing messages')} in your inbox. 
Score each one on these dimensions (1-10):
- Curiosity: Does it make me want to know more?
- Relevance: Does this feel like it's for ME specifically?
- Credibility: Do I trust the sender?
- Urgency: Do I feel I need to act now?
- Clarity: Do I understand the value in 3 seconds?

OPTION A:
{being_a['content']}

OPTION B:
{being_b['content']}

Respond in this exact JSON format:
{{
  "scores_a": {{"curiosity": X, "relevance": X, "credibility": X, "urgency": X, "clarity": X}},
  "scores_b": {{"curiosity": X, "relevance": X, "credibility": X, "urgency": X, "clarity": X}},
  "reasoning": "As {persona['name']}, I would [open/read/click] [A/B] because..."
}}
"""

def parse_judgment(response_text):
    """Parse the LLM's JSON response"""
    import re
    # Find JSON in response
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    # Fallback
    return {
        'scores_a': {d: 5 for d in SCORING_DIMENSIONS},
        'scores_b': {d: 5 for d in SCORING_DIMENSIONS},
        'reasoning': 'Unable to parse judgment'
    }

def calculate_weighted_score(scores, weights):
    """Calculate weighted score based on persona weights"""
    total = 0
    for dim in SCORING_DIMENSIONS:
        total += scores.get(dim, 5) * weights.get(dim, 0.2)
    return total

def add_being(content, being_type='subject_line', parent_id=None, metadata=None):
    """Add a new being to the arena"""
    conn = get_db()
    cursor = conn.cursor()
    
    generation = 1
    if parent_id:
        cursor.execute("SELECT generation FROM beings WHERE id = ?", (parent_id,))
        row = cursor.fetchone()
        if row:
            generation = row[0] + 1
    
    cursor.execute("""
        INSERT INTO beings (type, content, parent_id, generation, metadata)
        VALUES (?, ?, ?, ?, ?)
    """, (being_type, content, parent_id, generation, json.dumps(metadata) if metadata else None))
    
    being_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return being_id

def get_top_performers(being_type=None, limit=10):
    """Get top performing beings"""
    conn = get_db()
    cursor = conn.cursor()
    if being_type:
        cursor.execute("""
            SELECT id, type, content, score, wins, losses 
            FROM beings WHERE type = ? 
            ORDER BY score DESC LIMIT ?
        """, (being_type, limit))
    else:
        cursor.execute("""
            SELECT id, type, content, score, wins, losses 
            FROM beings ORDER BY score DESC LIMIT ?
        """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'type': r[1], 'content': r[2], 'score': r[3], 'wins': r[4], 'losses': r[5]} for r in rows]

def queue_for_ab_test(being_id):
    """Add a top performer to the A/B test queue"""
    being = get_being(being_id)
    if not being:
        return None
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ab_test_queue (being_id, simulated_score)
        VALUES (?, ?)
    """, (being_id, being['score']))
    queue_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return queue_id

if __name__ == '__main__':
    # Quick test
    print("Email/Ad Colosseum Battle Engine v1.0")
    print(f"Database: {DB_PATH}")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM personas")
    print(f"Personas loaded: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM beings")
    print(f"Beings in arena: {cursor.fetchone()[0]}")
    conn.close()
