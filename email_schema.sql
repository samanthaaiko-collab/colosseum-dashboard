-- Email/Ad Colosseum Domain Schema v1.0
-- Pre-test email subjects, copy, and ads against AI personas

CREATE TABLE IF NOT EXISTS beings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL, -- 'subject_line', 'email_copy', 'ad_creative', 'sequence'
    content TEXT NOT NULL,
    parent_id INTEGER,
    generation INTEGER DEFAULT 1,
    score REAL DEFAULT 5.0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (parent_id) REFERENCES beings(id)
);

CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- 'legal', 'medical'
    archetype TEXT NOT NULL, -- 'solo_pi_attorney', 'biglaw_associate', etc.
    description TEXT,
    behavior_traits JSON, -- {"skepticism": 0.8, "time_poor": 0.9, ...}
    scoring_weights JSON -- {"curiosity": 0.3, "relevance": 0.3, ...}
);

CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    being_a_id INTEGER NOT NULL,
    being_b_id INTEGER NOT NULL,
    winner_id INTEGER,
    persona_id INTEGER NOT NULL,
    battle_type TEXT NOT NULL,
    scores_a JSON, -- {"curiosity": 7, "relevance": 8, ...}
    scores_b JSON,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (being_a_id) REFERENCES beings(id),
    FOREIGN KEY (being_b_id) REFERENCES beings(id),
    FOREIGN KEY (winner_id) REFERENCES beings(id),
    FOREIGN KEY (persona_id) REFERENCES personas(id)
);

CREATE TABLE IF NOT EXISTS ab_test_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    being_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'testing', 'validated', 'rejected'
    simulated_score REAL,
    real_world_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    FOREIGN KEY (being_id) REFERENCES beings(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_beings_type ON beings(type);
CREATE INDEX IF NOT EXISTS idx_beings_score ON beings(score DESC);
CREATE INDEX IF NOT EXISTS idx_battles_winner ON battles(winner_id);
CREATE INDEX IF NOT EXISTS idx_personas_category ON personas(category);
