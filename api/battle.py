#!/usr/bin/env python3
"""
LIVE BATTLE API - Real LLM battles with TTS
Beings battle with their actual prompts, speak with ElevenLabs voices.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import sqlite3
import httpx
import hashlib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load environment
ENV_PATH = '/Users/samantha/.openclaw/workspace-forge/.env'
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

# Voice IDs
VOICES = {
    'george': 'JBFqnCBsd6RMkjVDRZzb',
    'chris': 'iP95p4xoKVk53GoZ742B',
    'charlie': 'IKne3meq5aSn9XLyUdCD',
    'eric': 'cjVigY5qzO86Huf0OWal',
    'jessica': 'cgSgspJ2msm6clMCkdW9',
    'sarah': 'EXAVITQu4vr4xnSDxMaL',
    'river': 'SAz9YHcvj6GT2YYXdXww',
    'athena': 'custom_athena_id',  # Replace with actual
    'callie': 'custom_callie_id',  # Replace with actual
}

# DB paths
MAIN_DB = '/Users/samantha/Projects/colosseum/colosseum.db'
DOMAIN_DB_TEMPLATE = '/Users/samantha/Projects/colosseum/domains/{domain}/colosseum.db'


def get_being_prompt(being_id, domain=None):
    """Fetch being's actual prompt from database."""
    if domain:
        db_path = DOMAIN_DB_TEMPLATE.format(domain=domain)
    else:
        db_path = MAIN_DB
    
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT prompt FROM beings WHERE being_id = ?", (being_id,))
    row = cur.fetchone()
    conn.close()
    
    return row[0] if row else None


def generate_battle_response(being_prompt, scenario, opponent_response=None):
    """Generate battle response using LLM with being's actual prompt."""
    system_prompt = f"""You are an ACT-I being competing in a live battle arena.

YOUR CORE PROMPT (your identity and capabilities):
{being_prompt}

You must respond to the battle scenario using your unique expertise and approach.
Be compelling, confident, and demonstrate mastery.
Keep your response to 2-3 powerful sentences.
Speak as if you're addressing a live audience - be engaging and memorable.
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if opponent_response:
        user_content = f"""BATTLE SCENARIO: {scenario}

Your opponent just said: "{opponent_response}"

Now deliver YOUR response. Counter their points and make your case stronger."""
    else:
        user_content = f"""BATTLE SCENARIO: {scenario}

You speak FIRST. Open strong and establish your position."""
    
    messages.append({"role": "user", "content": user_content})
    
    try:
        response = httpx.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'anthropic/claude-3.5-sonnet',
                'messages': messages,
                'max_tokens': 300,
                'temperature': 0.8
            },
            timeout=30
        )
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"[Battle response error: {e}]"


def judge_battle(fighter1_name, fighter1_response, fighter2_name, fighter2_response, scenario):
    """Judge evaluates both fighters and declares winner."""
    judge_prompt = """You are an elite judge in the ACT-I Colosseum - the arena where influence masters compete.

You evaluate based on the Unblinded Formula:
1. Integration of heart and strategy
2. Authentic influence over manipulation
3. Value creation over extraction
4. The 0.8% zone action - finding the highest leverage move
5. Mastery demonstration, not just knowledge

Score each fighter 1-10 (allow decimals like 8.73).
Be specific about WHY one wins.
"""

    messages = [
        {"role": "system", "content": judge_prompt},
        {"role": "user", "content": f"""BATTLE SCENARIO: {scenario}

FIGHTER 1 ({fighter1_name}):
"{fighter1_response}"

FIGHTER 2 ({fighter2_name}):
"{fighter2_response}"

Evaluate both fighters. Provide:
1. Score for Fighter 1 (X.XX)
2. Score for Fighter 2 (X.XX)  
3. Winner declaration
4. 2-3 sentence explanation of why the winner excelled

Format your response as JSON:
{{"score1": X.XX, "score2": X.XX, "winner": "Fighter 1" or "Fighter 2", "explanation": "..."}}
"""}
    ]
    
    try:
        response = httpx.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'anthropic/claude-3.5-sonnet',
                'messages': messages,
                'max_tokens': 500,
                'temperature': 0.3
            },
            timeout=30
        )
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"error": "Could not parse judge response"}
    except Exception as e:
        return {"error": str(e)}


def generate_tts(text, voice_id):
    """Generate TTS audio using ElevenLabs."""
    if not ELEVENLABS_API_KEY:
        return None
    
    actual_voice_id = VOICES.get(voice_id, VOICES['george'])
    
    try:
        response = httpx.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{actual_voice_id}',
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2',
                'voice_settings': {
                    'stability': 0.5,
                    'similarity_boost': 0.75
                }
            },
            timeout=30
        )
        if response.status_code == 200:
            # Return base64 encoded audio
            import base64
            return base64.b64encode(response.content).decode()
        return None
    except Exception as e:
        print(f"TTS error: {e}")
        return None


@app.route('/api/battle/start', methods=['POST'])
def start_battle():
    """Start a live battle between two beings."""
    data = request.json
    
    fighter1 = data.get('fighter1', {})
    fighter2 = data.get('fighter2', {})
    scenario = data.get('scenario', 'Demonstrate your mastery in 60 seconds.')
    voice1 = data.get('voice1', 'george')
    voice2 = data.get('voice2', 'callie')
    
    # Get actual prompts
    prompt1 = fighter1.get('prompt') or get_being_prompt(fighter1.get('id'), fighter1.get('domain'))
    prompt2 = fighter2.get('prompt') or get_being_prompt(fighter2.get('id'), fighter2.get('domain'))
    
    if not prompt1:
        prompt1 = f"You are {fighter1.get('name', 'Fighter 1')}, a master of {fighter1.get('domain', 'influence')}."
    if not prompt2:
        prompt2 = f"You are {fighter2.get('name', 'Fighter 2')}, a master of {fighter2.get('domain', 'influence')}."
    
    # Fighter 1 opens
    response1 = generate_battle_response(prompt1, scenario)
    audio1 = generate_tts(response1, voice1) if data.get('withAudio') else None
    
    # Fighter 2 counters
    response2 = generate_battle_response(prompt2, scenario, response1)
    audio2 = generate_tts(response2, voice2) if data.get('withAudio') else None
    
    # Judge evaluates
    verdict = judge_battle(
        fighter1.get('name', 'Fighter 1'), response1,
        fighter2.get('name', 'Fighter 2'), response2,
        scenario
    )
    
    # Log battle to database
    battle_id = hashlib.md5(f"{datetime.now().isoformat()}{response1}{response2}".encode()).hexdigest()[:16]
    try:
        conn = sqlite3.connect(MAIN_DB)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO battles (battle_id, being_a_id, being_b_id, winner_id, score_a, score_b, scenario_prompt, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            battle_id,
            fighter1.get('id', 'custom'),
            fighter2.get('id', 'custom'),
            fighter1.get('id') if verdict.get('winner') == 'Fighter 1' else fighter2.get('id'),
            verdict.get('score1', 0),
            verdict.get('score2', 0),
            scenario,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB logging error: {e}")
    
    return jsonify({
        'battle_id': battle_id,
        'fighter1': {
            'name': fighter1.get('name'),
            'response': response1,
            'audio': audio1,
            'score': verdict.get('score1')
        },
        'fighter2': {
            'name': fighter2.get('name'),
            'response': response2,
            'audio': audio2,
            'score': verdict.get('score2')
        },
        'verdict': verdict,
        'scenario': scenario
    })


@app.route('/api/battle/tts', methods=['POST'])
def get_tts():
    """Generate TTS for a single piece of text."""
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'george')
    
    audio = generate_tts(text, voice)
    
    return jsonify({
        'audio': audio,
        'voice': voice
    })


@app.route('/api/champions', methods=['GET'])
def get_champions():
    """Get all champions from all domains."""
    champions = []
    
    # Main colosseum champion
    try:
        conn = sqlite3.connect(MAIN_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT being_id, name, prompt, generation, avg_score 
            FROM beings 
            ORDER BY avg_score DESC 
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            champions.append({
                'id': row[0],
                'name': row[1] or 'Helios',
                'domain': 'Influence',
                'prompt': row[2],
                'generation': row[3],
                'score': row[4] or 8.5
            })
        conn.close()
    except Exception as e:
        print(f"Main DB error: {e}")
    
    # Domain champions
    domains = ['strategy', 'marketing', 'sales', 'tech', 'operations', 
               'customer_success', 'finance', 'hr', 'legal', 'product']
    
    for domain in domains:
        db_path = DOMAIN_DB_TEMPLATE.format(domain=domain)
        if not os.path.exists(db_path):
            continue
        
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT being_id, name, prompt, generation, avg_score 
                FROM beings 
                ORDER BY avg_score DESC 
                LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                champions.append({
                    'id': row[0],
                    'name': row[1] or f'{domain.title()} Champion',
                    'domain': domain.replace('_', ' ').title(),
                    'prompt': row[2],
                    'generation': row[3],
                    'score': row[4] or 8.0
                })
            conn.close()
        except Exception as e:
            print(f"Domain {domain} error: {e}")
    
    return jsonify(champions)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'battle-arena'})


if __name__ == '__main__':
    app.run(port=3346, debug=True)
