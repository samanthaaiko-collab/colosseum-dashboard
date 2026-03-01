#!/usr/bin/env python3
"""ACT-I Colosseum dashboard API server.

Provides domain-level and being-level endpoints backed by SQLite databases.
Supports exporting a static JSON snapshot for static deployments.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request, send_from_directory

try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover
    CORS = None


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MAIN_DB = "/Users/samantha/Projects/colosseum/colosseum.db"
DEFAULT_DOMAINS_ROOT = "/Users/samantha/Projects/colosseum/domains"
DEFAULT_EMAIL_DB = str(BASE_DIR / "email_ad.db")
DEFAULT_RECOVERY_JSON = str(BASE_DIR / "data" / "recovery_lawyers_colosseum.json")
DEFAULT_DOMAINS = [
    "strategy",
    "marketing",
    "sales",
    "tech",
    "ops",
    "cs",
    "finance",
    "hr",
    "legal",
    "product",
]
BEING_COLUMNS = [
    "id",
    "name",
    "generation",
    "score",
    "wins",
    "losses",
    "system_prompt",
    "model",
    "parent_id",
    "created_at",
    "updated_at",
]

BATTLE_TABLE_CANDIDATES = [
    "battles",
    "battle_history",
    "matches",
    "fight_results",
    "duels",
    "arena_battles",
]

BATTLE_FIELD_ALIASES = {
    "battle_id": ["id", "battle_id", "match_id"],
    "being_a_id": ["being_a_id", "agent_a_id", "a_id", "being1_id", "challenger_id"],
    "being_b_id": ["being_b_id", "agent_b_id", "b_id", "being2_id", "defender_id"],
    "being_a_name": ["being_a_name", "name_a", "challenger_name", "agent_a_name"],
    "being_b_name": ["being_b_name", "name_b", "defender_name", "agent_b_name"],
    "score_a": ["score_a", "being_a_score", "challenger_score", "agent_a_score"],
    "score_b": ["score_b", "being_b_score", "defender_score", "agent_b_score"],
    "winner_id": ["winner_id", "winner", "winning_being_id"],
    "winner_name": ["winner_name", "winner", "winning_name"],
    "transcript": ["transcript", "battle_log", "log", "conversation", "result_text", "details"],
    "created_at": ["created_at", "timestamp", "started_at", "finished_at", "updated_at"],
}

RECOVERY_SCRIPT_VARIANTS = [
    {
        "name": "Longhorn Closer",
        "creature": "Longhorn Lion",
        "rapport": "Hey {first_name} in {city}, this is Recovery. I know your time is limited, so I will keep this short.",
        "pain": "Most firms we see have value stuck between signed case and collected case because recovery follow-up is fragmented.",
        "agreement": "You already win cases. The opportunity is cleaner recovery conversion, not more intake volume.",
        "zone_action": "Would a 15-minute recovery map call this week be useful?",
    },
    {
        "name": "Metro Docket Tactician",
        "creature": "Metro Falcon",
        "rapport": "Hey {first_name} in {city}, this is Recovery outreach. Quick call, clear intent.",
        "pain": "Teams in your lane often lose speed where files transition across staff with no single recovery owner.",
        "agreement": "You do not need new lead flow first. You need tighter middle-pipeline execution.",
        "zone_action": "Open to a short call where we pressure-test your current recovery chain?",
    },
    {
        "name": "Bayou Momentum Architect",
        "creature": "Bayou Jaguar",
        "rapport": "Hey {first_name} in {city}, I will be direct so this is useful.",
        "pain": "High-volume firms get hit by small delays that compound and quietly reduce realized case value.",
        "agreement": "Demand is not the blocker. Process rhythm after intake is the blocker.",
        "zone_action": "Can we schedule a focused call to identify one stalled lane?",
    },
    {
        "name": "Borderline Precision Closer",
        "creature": "Border Hawk",
        "rapport": "Hey {first_name} in {city}, appreciate the quick minute. This is a focused recovery follow-up.",
        "pain": "Stale files typically come from communication lag around medical timelines and negotiation checkpoints.",
        "agreement": "Your legal work is strong; the gain is protecting momentum before case value decays.",
        "zone_action": "Can we run three active files through a short recovery filter call?",
    },
    {
        "name": "Docket Velocity Ranger",
        "creature": "North Star Wolf",
        "rapport": "Hey {first_name} in {city}, quick one from Recovery and then I am out of your way.",
        "pain": "When updates stay manual, case transitions become slow and recoverable dollars remain stranded.",
        "agreement": "You have enough opportunities already in motion; the win is better handoff clarity.",
        "zone_action": "Would a 12-minute zone-action call help isolate your highest leverage fix?",
    },
    {
        "name": "Agreement Engine",
        "creature": "River Phoenix",
        "rapport": "Hey {first_name} in {city}, reconnecting with a practical next step.",
        "pain": "Even qualified firms leak value when ownership is unclear between negotiation and collection.",
        "agreement": "You are close to better outcomes; this is an execution refinement.",
        "zone_action": "Should we lock a short implementation call and define one sprint owner?",
    },
    {
        "name": "Conversion Smith",
        "creature": "Iron Coyote",
        "rapport": "Hey {first_name} in {city}, this is Recovery. Specific purpose, under 30 seconds.",
        "pain": "Many firms win trust early and then stall near settlement because recovery choreography is inconsistent.",
        "agreement": "You already do the hard legal work. Process consistency unlocks the rest.",
        "zone_action": "Open to a short call to design one cleaner settlement-to-collection path?",
    },
    {
        "name": "Booking Sentinel",
        "creature": "Silver Lynx",
        "rapport": "Hey {first_name} in {city}, sharing a quick pre-brief so your next step is clear.",
        "pain": "Booked firms still show hidden delay when file progression and post-demand communication are not synced.",
        "agreement": "You already took action by engaging. Now we accelerate measurable recovery.",
        "zone_action": "On a short call, we can set one lane, one owner, and one timeline.",
    },
    {
        "name": "Resolution Driver",
        "creature": "Dust Stallion",
        "rapport": "Hey {first_name} in {city}, I will keep this practical.",
        "pain": "Smaller market teams feel pressure fastest when unresolved files consume attention but do not move revenue.",
        "agreement": "Headcount is not step one. Prioritized recovery decisions on current files are step one.",
        "zone_action": "Would a quick call to rank your next three files by leverage help?",
    },
    {
        "name": "Agreement Captain",
        "creature": "Tide Serpent",
        "rapport": "Hey {first_name} in {city}, thanks for the minute. Calling with one concrete idea.",
        "pain": "Recovery friction often hides at case transitions and drags out time-to-cash.",
        "agreement": "Your active matters already contain upside. Transition control unlocks it faster.",
        "zone_action": "Would Thursday or Friday work for a short zone-action recovery call?",
    },
]


class ColosseumData:
    def __init__(self) -> None:
        self.main_db = os.getenv("COLOSSEUM_MAIN_DB", DEFAULT_MAIN_DB)
        self.domains_root = os.getenv("COLOSSEUM_DOMAINS_ROOT", DEFAULT_DOMAINS_ROOT)
        self.email_db = os.getenv("COLOSSEUM_EMAIL_DB", DEFAULT_EMAIL_DB)
        self.recovery_json = os.getenv("COLOSSEUM_RECOVERY_JSON", DEFAULT_RECOVERY_JSON)
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.recovery_supabase_table = os.getenv("RECOVERY_SUPABASE_TABLE", "recovery_lawyers")
        configured = os.getenv("COLOSSEUM_DOMAIN_LIST", ",".join(DEFAULT_DOMAINS))
        self.domains = [d.strip() for d in configured.split(",") if d.strip()]
        self._battle_table_cache: Dict[str, Optional[Tuple[str, Dict[str, str]]]] = {}

    def domain_paths(self) -> Dict[str, str]:
        paths = {"main": self.main_db}
        for domain in self.domains:
            paths[domain] = str(Path(self.domains_root) / domain / "colosseum.db")
        return paths

    def _connect(self, db_path: str) -> sqlite3.Connection:
        if not Path(db_path).exists():
            raise FileNotFoundError(db_path)
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> List[str]:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [r["name"] for r in rows]

    def _table_exists(self, conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table,),
        ).fetchone()
        return row is not None

    def _coerce_timestamp(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
            except (OverflowError, ValueError):
                return str(value)
        return str(value)

    def _pick_alias(self, columns: List[str], aliases: List[str]) -> Optional[str]:
        colset = {c.lower(): c for c in columns}
        for alias in aliases:
            key = alias.lower()
            if key in colset:
                return colset[key]
        return None

    def _timestamp_sort_value(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return 0.0
        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                return datetime.fromisoformat(candidate).timestamp()
            except ValueError:
                continue
        return 0.0

    def _safe_json(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def _detect_battle_table(self, db_path: str) -> Optional[Tuple[str, Dict[str, str]]]:
        if db_path in self._battle_table_cache:
            return self._battle_table_cache[db_path]

        try:
            with self._connect(db_path) as conn:
                tables = {
                    r["name"]: r["name"]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }

                selected = None
                for candidate in BATTLE_TABLE_CANDIDATES:
                    if candidate in tables:
                        selected = candidate
                        break

                if selected is None:
                    for name in tables:
                        lowered = name.lower()
                        if "battle" in lowered or "match" in lowered or "fight" in lowered:
                            selected = name
                            break

                if selected is None:
                    self._battle_table_cache[db_path] = None
                    return None

                columns = self._table_columns(conn, selected)
                mapping: Dict[str, str] = {}
                for field, aliases in BATTLE_FIELD_ALIASES.items():
                    picked = self._pick_alias(columns, aliases)
                    if picked:
                        mapping[field] = picked

                self._battle_table_cache[db_path] = (selected, mapping)
                return self._battle_table_cache[db_path]
        except Exception:
            self._battle_table_cache[db_path] = None
            return None

    def domain_status(self) -> List[Dict[str, Any]]:
        statuses: List[Dict[str, Any]] = []
        for name, db_path in self.domain_paths().items():
            exists = Path(db_path).exists()
            statuses.append({"name": name, "db_path": db_path, "online": exists})
        return statuses

    def load_beings(self, domain: str) -> List[Dict[str, Any]]:
        db_path = self.domain_paths().get(domain)
        if not db_path:
            raise KeyError(domain)

        with self._connect(db_path) as conn:
            if not self._table_exists(conn, "beings"):
                return []

            columns = self._table_columns(conn, "beings")
            selectors = []
            for col in BEING_COLUMNS:
                if col in columns:
                    selectors.append(f"{col} AS {col}")
                else:
                    selectors.append(f"NULL AS {col}")

            sql = (
                f"SELECT {', '.join(selectors)} FROM beings "
                "ORDER BY COALESCE(score, 0) DESC, COALESCE(generation, 0) DESC"
            )
            rows = conn.execute(sql).fetchall()

        beings = [dict(r) for r in rows]
        for b in beings:
            b["score"] = float(b["score"] or 0.0)
            b["generation"] = int(b["generation"] or 0)
            b["wins"] = int(b["wins"] or 0)
            b["losses"] = int(b["losses"] or 0)
            b["domain"] = domain
            b["created_at"] = self._coerce_timestamp(b.get("created_at"))
            b["updated_at"] = self._coerce_timestamp(b.get("updated_at"))
        return beings

    def load_domain_battles(self, domain: str, limit: int = 120) -> List[Dict[str, Any]]:
        db_path = self.domain_paths().get(domain)
        if not db_path:
            raise KeyError(domain)

        battle_meta = self._detect_battle_table(db_path)
        if not battle_meta:
            return []

        table, mapping = battle_meta
        with self._connect(db_path) as conn:
            selectors = []
            for field in BATTLE_FIELD_ALIASES:
                col = mapping.get(field)
                selectors.append(f"{col} AS {field}" if col else f"NULL AS {field}")

            order_col = mapping.get("created_at") or mapping.get("battle_id")
            sql = f"SELECT {', '.join(selectors)} FROM {table}"
            if order_col:
                sql += f" ORDER BY {order_col} DESC"
            sql += " LIMIT ?"

            rows = conn.execute(sql, (limit,)).fetchall()

        battles = [dict(r) for r in rows]
        for row in battles:
            row["domain"] = domain
            row["score_a"] = float(row["score_a"] or 0.0)
            row["score_b"] = float(row["score_b"] or 0.0)
            row["created_at"] = self._coerce_timestamp(row.get("created_at"))
            if not row.get("winner_name") and row.get("winner_id"):
                if row.get("winner_id") == row.get("being_a_id"):
                    row["winner_name"] = row.get("being_a_name")
                elif row.get("winner_id") == row.get("being_b_id"):
                    row["winner_name"] = row.get("being_b_name")
            if not row.get("winner_name"):
                if row["score_a"] > row["score_b"]:
                    row["winner_name"] = row.get("being_a_name")
                elif row["score_b"] > row["score_a"]:
                    row["winner_name"] = row.get("being_b_name")
                else:
                    row["winner_name"] = "Draw"
        return battles

    def domain_summary(self, domain: str) -> Dict[str, Any]:
        beings = self.load_beings(domain)
        champions = sorted(beings, key=lambda b: (b["score"], b["wins"]), reverse=True)[:10]
        battles = self.load_domain_battles(domain, limit=500)
        generation_depth = max((b["generation"] for b in beings), default=0)
        avg_score = round(sum(b["score"] for b in beings) / len(beings), 3) if beings else 0.0

        return {
            "name": domain,
            "db_path": self.domain_paths()[domain],
            "online": True,
            "beings_count": len(beings),
            "battle_count": len(battles),
            "generation_depth": generation_depth,
            "avg_score": avg_score,
            "champion": champions[0] if champions else None,
        }

    def find_being(self, being_id: str) -> Optional[Dict[str, Any]]:
        for domain in self.domain_paths():
            try:
                beings = self.load_beings(domain)
            except FileNotFoundError:
                continue
            for being in beings:
                if being["id"] == being_id:
                    return being
        return None

    def lineage(self, being_id: str) -> Optional[Dict[str, Any]]:
        being = self.find_being(being_id)
        if not being:
            return None

        domain = being["domain"]
        beings = {b["id"]: b for b in self.load_beings(domain)}

        chain: List[Dict[str, Any]] = []
        seen = set()
        current = beings.get(being_id)
        while current and current["id"] not in seen:
            seen.add(current["id"])
            chain.append(current)
            parent_id = current.get("parent_id")
            current = beings.get(parent_id) if parent_id else None

        chain.reverse()
        return {
            "domain": domain,
            "being_id": being_id,
            "root_id": chain[0]["id"] if chain else None,
            "depth": len(chain) - 1,
            "chain": chain,
        }

    def battles_for_being(self, being_id: str, limit: int = 80) -> List[Dict[str, Any]]:
        being = self.find_being(being_id)
        if not being:
            return []

        domain = being["domain"]
        battles = self.load_domain_battles(domain, limit=300)
        filtered = [
            b
            for b in battles
            if b.get("being_a_id") == being_id or b.get("being_b_id") == being_id
        ]
        return filtered[:limit]

    def activity_feed(self, limit: int = 40) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        for domain, db_path in self.domain_paths().items():
            try:
                beings = self.load_beings(domain)
                battles = self.load_domain_battles(domain, limit=20)
            except FileNotFoundError:
                continue

            recent_beings = sorted(
                beings,
                key=lambda b: self._timestamp_sort_value(b.get("updated_at") or b.get("created_at")),
                reverse=True,
            )[:20]

            for being in recent_beings:
                ts = being.get("updated_at") or being.get("created_at")
                items.append(
                    {
                        "type": "evolution",
                        "domain": domain,
                        "timestamp": ts,
                        "title": f"{being['name'] or being['id']} evolved",
                        "details": f"Gen {being['generation']} | score {being['score']:.2f}",
                        "being_id": being["id"],
                    }
                )

            for battle in battles:
                ts = battle.get("created_at")
                a = battle.get("being_a_name") or battle.get("being_a_id") or "Unknown A"
                b = battle.get("being_b_name") or battle.get("being_b_id") or "Unknown B"
                winner = battle.get("winner_name") or "Unknown"
                items.append(
                    {
                        "type": "battle",
                        "domain": domain,
                        "timestamp": ts,
                        "title": f"Battle: {a} vs {b}",
                        "details": f"Winner: {winner}",
                        "battle_id": battle.get("battle_id"),
                    }
                )

        def sort_key(row: Dict[str, Any]) -> float:
            return self._timestamp_sort_value(row.get("timestamp"))

        items.sort(key=sort_key, reverse=True)
        return items[:limit]

    def aggregate_stats(self) -> Dict[str, Any]:
        total_beings = 0
        total_battles = 0
        max_generation = 0
        domain_summaries: List[Dict[str, Any]] = []
        leaderboard: List[Dict[str, Any]] = []

        for status in self.domain_status():
            domain = status["name"]
            if not status["online"]:
                domain_summaries.append(
                    {
                        "name": domain,
                        "db_path": status["db_path"],
                        "online": False,
                        "beings_count": 0,
                        "battle_count": 0,
                        "generation_depth": 0,
                        "avg_score": 0.0,
                        "champion": None,
                    }
                )
                continue

            try:
                summary = self.domain_summary(domain)
                domain_summaries.append(summary)
                total_beings += summary["beings_count"]
                total_battles += summary["battle_count"]
                max_generation = max(max_generation, summary["generation_depth"])
                if summary["champion"]:
                    leaderboard.append(summary["champion"])
            except Exception:
                domain_summaries.append(
                    {
                        "name": domain,
                        "db_path": status["db_path"],
                        "online": False,
                        "beings_count": 0,
                        "battle_count": 0,
                        "generation_depth": 0,
                        "avg_score": 0.0,
                        "champion": None,
                    }
                )

        leaderboard = sorted(leaderboard, key=lambda b: (b["score"], b["wins"]), reverse=True)[:10]
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_domains": len(domain_summaries),
            "active_domains": sum(1 for d in domain_summaries if d["online"]),
            "total_beings": total_beings,
            "total_battles": total_battles,
            "max_generation": max_generation,
            "leaderboard": leaderboard,
            "domains": domain_summaries,
        }

    def export_snapshot(self, battle_limit: int = 120) -> Dict[str, Any]:
        stats = self.aggregate_stats()
        domain_data: Dict[str, Any] = {}

        for status in self.domain_status():
            domain = status["name"]
            if not status["online"]:
                domain_data[domain] = {
                    "online": False,
                    "beings": [],
                    "champions": [],
                    "battles": [],
                }
                continue

            try:
                beings = self.load_beings(domain)
                domain_data[domain] = {
                    "online": True,
                    "beings": beings,
                    "champions": sorted(beings, key=lambda b: (b["score"], b["wins"]), reverse=True)[:10],
                    "battles": self.load_domain_battles(domain, limit=battle_limit),
                }
            except Exception:
                domain_data[domain] = {
                    "online": False,
                    "beings": [],
                    "champions": [],
                    "battles": [],
                }

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "domains": stats["domains"],
            "domain_data": domain_data,
            "activity": self.activity_feed(limit=120),
        }

    def load_email_leaderboard(
        self, limit: int = 25, being_type: Optional[str] = "subject_line"
    ) -> List[Dict[str, Any]]:
        with self._connect(self.email_db) as conn:
            if not self._table_exists(conn, "beings"):
                return []
            if being_type:
                rows = conn.execute(
                    """
                    SELECT id, type, content, score, wins, losses, generation, created_at, metadata
                    FROM beings
                    WHERE type = ?
                    ORDER BY COALESCE(score, 0) DESC, COALESCE(wins, 0) DESC, COALESCE(losses, 0) ASC, id ASC
                    LIMIT ?
                    """,
                    (being_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, type, content, score, wins, losses, generation, created_at, metadata
                    FROM beings
                    ORDER BY COALESCE(score, 0) DESC, COALESCE(wins, 0) DESC, COALESCE(losses, 0) ASC, id ASC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        leaderboard = [dict(r) for r in rows]
        for row in leaderboard:
            row["score"] = float(row["score"] or 0.0)
            row["wins"] = int(row["wins"] or 0)
            row["losses"] = int(row["losses"] or 0)
            row["generation"] = int(row["generation"] or 0)
            row["created_at"] = self._coerce_timestamp(row.get("created_at"))
            row["metadata"] = self._safe_json(row.get("metadata"))
            total = row["wins"] + row["losses"]
            row["win_rate"] = round(row["wins"] / total, 4) if total else 0.0
        return leaderboard

    def load_email_battles(
        self, limit: int = 60, battle_type: Optional[str] = "subject_line"
    ) -> List[Dict[str, Any]]:
        with self._connect(self.email_db) as conn:
            if not self._table_exists(conn, "battles"):
                return []

            where_sql = "WHERE b.battle_type = ?" if battle_type else ""
            params: Tuple[Any, ...] = (battle_type, limit) if battle_type else (limit,)
            rows = conn.execute(
                f"""
                SELECT
                    b.id AS battle_id,
                    b.being_a_id,
                    b.being_b_id,
                    b.winner_id,
                    b.persona_id,
                    b.battle_type,
                    b.scores_a,
                    b.scores_b,
                    b.reasoning,
                    b.created_at,
                    a.content AS being_a_content,
                    c.content AS being_b_content,
                    w.content AS winner_content,
                    p.name AS persona_name,
                    p.category AS persona_category,
                    p.archetype AS persona_archetype
                FROM battles b
                LEFT JOIN beings a ON a.id = b.being_a_id
                LEFT JOIN beings c ON c.id = b.being_b_id
                LEFT JOIN beings w ON w.id = b.winner_id
                LEFT JOIN personas p ON p.id = b.persona_id
                {where_sql}
                ORDER BY b.created_at DESC, b.id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        battles = [dict(r) for r in rows]
        for row in battles:
            row["created_at"] = self._coerce_timestamp(row.get("created_at"))
            row["scores_a"] = self._safe_json(row.get("scores_a")) or {}
            row["scores_b"] = self._safe_json(row.get("scores_b")) or {}
            row["reasoning"] = str(row.get("reasoning") or "").strip()
            if row.get("winner_id") == row.get("being_a_id"):
                row["winner_side"] = "A"
            elif row.get("winner_id") == row.get("being_b_id"):
                row["winner_side"] = "B"
            else:
                row["winner_side"] = "?"
        return battles

    def load_email_personas(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect(self.email_db) as conn:
            if not self._table_exists(conn, "personas"):
                return []
            rows = conn.execute(
                """
                SELECT id, name, category, archetype, description, behavior_traits, scoring_weights
                FROM personas
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        personas = [dict(r) for r in rows]
        for row in personas:
            row["behavior_traits"] = self._safe_json(row.get("behavior_traits")) or {}
            row["scoring_weights"] = self._safe_json(row.get("scoring_weights")) or {}
        return personas

    def load_email_sequence_rankings(self, limit: int = 10) -> Dict[str, Any]:
        with self._connect(self.email_db) as conn:
            if not self._table_exists(conn, "beings"):
                return {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "type": "sequence",
                    "limit": limit,
                    "count": 0,
                    "summary": {
                        "total_sequences": 0,
                        "with_battles": 0,
                        "without_battles": 0,
                        "avg_win_rate": 0.0,
                    },
                    "top": [],
                    "bottom": [],
                    "rankings": [],
                }

            rows = conn.execute(
                """
                SELECT
                    id,
                    type,
                    content,
                    score,
                    wins,
                    losses,
                    generation,
                    created_at,
                    metadata,
                    (COALESCE(wins, 0) + COALESCE(losses, 0)) AS battles,
                    CASE
                        WHEN (COALESCE(wins, 0) + COALESCE(losses, 0)) > 0
                        THEN (1.0 * COALESCE(wins, 0)) / (COALESCE(wins, 0) + COALESCE(losses, 0))
                        ELSE 0.0
                    END AS win_rate
                FROM beings
                WHERE type = 'sequence'
                """
            ).fetchall()

        rankings = [dict(r) for r in rows]
        for row in rankings:
            row["score"] = float(row["score"] or 0.0)
            row["wins"] = int(row["wins"] or 0)
            row["losses"] = int(row["losses"] or 0)
            row["generation"] = int(row["generation"] or 0)
            row["battles"] = int(row["battles"] or 0)
            row["created_at"] = self._coerce_timestamp(row.get("created_at"))
            row["metadata"] = self._safe_json(row.get("metadata"))
            row["win_rate"] = round(float(row.get("win_rate") or 0.0), 6)
            row["win_rate_pct"] = round(row["win_rate"] * 100.0, 2)

        rankings_sorted = sorted(
            rankings,
            key=lambda row: (
                row.get("win_rate", 0.0),
                row.get("battles", 0),
                row.get("wins", 0),
                row.get("score", 0.0),
            ),
            reverse=True,
        )

        top = rankings_sorted[:limit]
        bottom = sorted(
            rankings,
            key=lambda row: (
                row.get("win_rate", 0.0),
                -(row.get("battles", 0)),
                row.get("losses", 0),
                row.get("score", 0.0),
            ),
        )[:limit]

        with_battles = [row for row in rankings if row.get("battles", 0) > 0]
        avg_win_rate = (
            round(sum(row["win_rate"] for row in with_battles) / len(with_battles), 6)
            if with_battles
            else 0.0
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "type": "sequence",
            "limit": limit,
            "count": len(rankings),
            "summary": {
                "total_sequences": len(rankings),
                "with_battles": len(with_battles),
                "without_battles": len(rankings) - len(with_battles),
                "avg_win_rate": avg_win_rate,
            },
            "top": top,
            "bottom": bottom,
            "rankings": rankings_sorted,
        }

    def export_email_snapshot(
        self,
        leaderboard_limit: int = 100,
        battles_limit: int = 300,
        battle_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        summary = {
            "beings": 0,
            "battles": 0,
            "personas": 0,
            "ab_test_queue": 0,
        }
        with self._connect(self.email_db) as conn:
            for table_name in summary:
                if not self._table_exists(conn, table_name):
                    continue
                row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
                summary[table_name] = int(row["count"] if row else 0)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "db_path": self.email_db,
            "online": True,
            "summary": summary,
            "leaderboard": self.load_email_leaderboard(
                limit=leaderboard_limit,
                being_type="subject_line",
            ),
            "battles": self.load_email_battles(limit=battles_limit, battle_type=battle_type),
            "personas": self.load_email_personas(limit=500),
            "sequences": self.load_email_sequence_rankings(limit=10),
        }

    def _recovery_sample_payload(self) -> Dict[str, Any]:
        path = Path(self.recovery_json)
        if not path.exists():
            raise FileNotFoundError(str(path))
        return json.loads(path.read_text(encoding="utf-8"))

    def _recovery_supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key and self.recovery_supabase_table)

    def _normalize_recovery_lead(self, row: Dict[str, Any], idx: int) -> Dict[str, Any]:
        try:
            close_confidence = float(row.get("close_confidence") or 0.0)
        except (TypeError, ValueError):
            close_confidence = 0.0
        close_confidence = max(0.0, min(close_confidence, 1.0))

        return {
            "id": str(row.get("id") or f"TX-LIVE-{idx + 1:03d}"),
            "phone": str(row.get("phone") or ""),
            "first_name": str(row.get("first_name") or "Counsel"),
            "location_city": str(row.get("location_city") or "Texas"),
            "location_state": str(row.get("location_state") or "TX"),
            "pipeline_stage": str(row.get("pipeline_stage") or "new"),
            "call_outcome": str(row.get("call_outcome") or "not_attempted"),
            "close_confidence": round(close_confidence, 2),
            "source_campaign": str(row.get("source_campaign") or "TX_Pilot_Recovery_Q1"),
        }

    def load_recovery_supabase_leads(self, limit: int = 250) -> List[Dict[str, Any]]:
        if not self._recovery_supabase_configured():
            raise RuntimeError(
                "Supabase env missing. Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and RECOVERY_SUPABASE_TABLE."
            )

        fields = ",".join(
            [
                "id",
                "phone",
                "first_name",
                "location_city",
                "location_state",
                "pipeline_stage",
                "call_outcome",
                "close_confidence",
                "source_campaign",
            ]
        )
        query = (
            f"select={fields}&location_state=eq.TX"
            f"&order=id.asc&limit={min(max(limit, 1), 1000)}"
        )
        url = f"{self.supabase_url}/rest/v1/{self.recovery_supabase_table}?{query}"
        request_headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Accept": "application/json",
        }
        req = Request(url, headers=request_headers, method="GET")

        try:
            with urlopen(req, timeout=12) as response:
                body = response.read().decode("utf-8")
        except URLError as exc:
            raise RuntimeError(f"Supabase request failed: {exc}") from exc

        try:
            rows = json.loads(body or "[]")
        except json.JSONDecodeError as exc:
            raise RuntimeError("Supabase response was not valid JSON") from exc

        if not isinstance(rows, list):
            raise RuntimeError("Supabase response shape was unexpected")

        leads = [self._normalize_recovery_lead(row, idx) for idx, row in enumerate(rows)]
        if not leads:
            raise RuntimeError("Supabase returned zero TX leads")
        return leads

    def _build_recovery_beings(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prioritized = [
            lead
            for lead in leads
            if (lead.get("first_name") or "").strip() and (lead.get("location_city") or "").strip()
        ]
        selected = prioritized[:10]

        beings: List[Dict[str, Any]] = []
        for idx, lead in enumerate(selected):
            template = RECOVERY_SCRIPT_VARIANTS[idx % len(RECOVERY_SCRIPT_VARIANTS)]
            first_name = lead.get("first_name") or "Counsel"
            city = lead.get("location_city") or "Texas"
            pipeline_stage = str(lead.get("pipeline_stage") or "new")

            rapport = template["rapport"].format(first_name=first_name, city=city)
            pain = template["pain"]
            agreement = template["agreement"]
            zone_action = template["zone_action"]
            full_script = " ".join([rapport, pain, agreement, zone_action]).strip()
            sms_script = (
                f"Hey {first_name} in {city}, quick note: we help PI teams reduce recovery stalls. "
                f"Open to a short call this week?"
            )

            self_mastery = round(8.3 + (idx % 4) * 0.2 + (0.1 if pipeline_stage != "new" else 0.0), 2)
            influence_mastery = round(8.6 + (idx % 5) * 0.2 + (0.15 if idx in {1, 7} else 0.0), 2)
            process_mastery = round(8.8 + (idx % 3) * 0.25 + (0.2 if pipeline_stage in {"qualified", "meeting_booked"} else 0.0), 2)
            creature_scale = round(8.4 + (idx % 4) * 0.2, 2)
            net_formula = round(
                (self_mastery * 0.32) + (influence_mastery * 0.36) + (process_mastery * 0.32),
                2,
            )

            beings.append(
                {
                    "id": f"RL-LIVE-{idx + 1:02d}",
                    "lead_id": lead.get("id"),
                    "name": template["name"],
                    "creature": template["creature"],
                    "first_name": first_name,
                    "city": city,
                    "pipeline_stage": pipeline_stage,
                    "call_script": {
                        "rapport": rapport,
                        "pain": pain,
                        "agreement": agreement,
                        "zone_action": zone_action,
                        "full": full_script,
                    },
                    "sms_script": sms_script,
                    "judge_scores": {
                        "self_mastery": self_mastery,
                        "influence_mastery": influence_mastery,
                        "process_mastery": process_mastery,
                        "creature_scale": creature_scale,
                        "net_formula": net_formula,
                    },
                }
            )
        return beings

    def _build_recovery_battles(self, beings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(beings) < 2:
            return []

        pair_indices = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (0, 7)]
        rounds = ["Qualifier A", "Qualifier B", "Qualifier C", "Qualifier D", "Semifinal", "Final"]
        judges = [
            "Athena Council",
            "Helios Board",
            "Forge Tribunal",
            "Atlas Panel",
            "Net Formula Core",
            "Grand Judge Synthesis",
        ]

        now = datetime.now(timezone.utc)
        battles: List[Dict[str, Any]] = []
        for idx, pair in enumerate(pair_indices):
            a_idx, b_idx = pair
            if a_idx >= len(beings) or b_idx >= len(beings):
                continue
            being_a = beings[a_idx]
            being_b = beings[b_idx]
            score_a = float(being_a["judge_scores"]["net_formula"])
            score_b = float(being_b["judge_scores"]["net_formula"])
            winner_id = being_a["id"] if score_a >= score_b else being_b["id"]
            created_at = (now.replace(microsecond=0)).isoformat()
            now = now.replace(second=min(59, now.second + 2))

            battles.append(
                {
                    "id": f"RB-LIVE-{idx + 1:03d}",
                    "round": rounds[idx % len(rounds)],
                    "being_a_id": being_a["id"],
                    "being_b_id": being_b["id"],
                    "winner_id": winner_id,
                    "judge": judges[idx % len(judges)],
                    "judge_notes": "Winner had stronger agreement and zone action precision.",
                    "scores": {
                        "a": being_a["judge_scores"],
                        "b": being_b["judge_scores"],
                    },
                    "created_at": created_at,
                }
            )
        return battles

    def _build_recovery_mock_calls(self, beings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []
        for idx, being in enumerate(beings[:3]):
            first_name = being.get("first_name") or "Counsel"
            city = being.get("city") or "Texas"
            calls.append(
                {
                    "id": f"MC-LIVE-{idx + 1:03d}",
                    "being_id": being["id"],
                    "title": f"{first_name} in {city} - mock call",
                    "lines": [
                        f"Agent: Hey {first_name} in {city}, this is Recovery. Quick check-in.",
                        "Lawyer: Yes, what are you seeing in firms like mine?",
                        "Agent: The pattern is stalled value after intake when recovery ownership is split.",
                        "Lawyer: That sounds familiar. What is your recommendation?",
                        "Agent: Short strategy call. We identify one lane, one owner, one timeline.",
                    ],
                }
            )
        return calls

    def _build_recovery_payload(self, leads: List[Dict[str, Any]], source: str) -> Dict[str, Any]:
        state_filtered = [lead for lead in leads if str(lead.get("location_state") or "").upper() == "TX"]
        city_distribution: Dict[str, int] = {}
        for lead in state_filtered:
            city = str(lead.get("location_city") or "Unknown")
            city_distribution[city] = city_distribution.get(city, 0) + 1

        city_distribution = dict(
            sorted(city_distribution.items(), key=lambda item: item[1], reverse=True)
        )
        untouched_new = sum(1 for lead in state_filtered if str(lead.get("pipeline_stage") or "").lower() == "new")

        beings = self._build_recovery_beings(state_filtered)
        battles = self._build_recovery_battles(beings)
        mock_calls = self._build_recovery_mock_calls(beings)
        top_scripts = sorted(
            beings,
            key=lambda being: float(being.get("judge_scores", {}).get("net_formula", 0.0)),
            reverse=True,
        )[:5]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "pilot_data": {
                "state": "TX",
                "total_lawyers": len(state_filtered),
                "untouched_new": untouched_new,
                "city_distribution": city_distribution,
                "schema": [
                    "phone",
                    "first_name",
                    "location_city",
                    "location_state",
                    "pipeline_stage",
                    "call_outcome",
                    "close_confidence",
                    "source_campaign",
                ],
            },
            "leads": state_filtered,
            "beings": beings,
            "top_scripts": top_scripts,
            "battles": battles,
            "mock_calls": mock_calls,
        }

    def export_recovery_snapshot(self, source: str = "sample") -> Dict[str, Any]:
        requested = source.strip().lower()
        if requested in {"supabase", "live"}:
            try:
                leads = self.load_recovery_supabase_leads(limit=500)
                payload = self._build_recovery_payload(leads, source="supabase")
                payload["supabase_stub"] = {
                    "configured": self._recovery_supabase_configured(),
                    "used": True,
                    "table": self.recovery_supabase_table,
                }
                return payload
            except Exception as exc:
                payload = self._recovery_sample_payload()
                payload["generated_at"] = datetime.now(timezone.utc).isoformat()
                payload["source"] = "sample"
                payload["supabase_stub"] = {
                    "configured": self._recovery_supabase_configured(),
                    "used": False,
                    "table": self.recovery_supabase_table,
                    "error": str(exc),
                }
                return payload

        payload = self._recovery_sample_payload()
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        payload["source"] = payload.get("source") or "sample"
        payload["supabase_stub"] = {
            "configured": self._recovery_supabase_configured(),
            "used": False,
            "table": self.recovery_supabase_table,
        }
        return payload


data = ColosseumData()
app = Flask(__name__)
if CORS is not None:
    CORS(app)


@app.get("/api/health")
def health() -> Any:
    return jsonify({"ok": True, "timestamp": datetime.now(timezone.utc).isoformat()})


@app.get("/api/stats")
def api_stats() -> Any:
    return jsonify(data.aggregate_stats())


@app.get("/api/domains")
def api_domains() -> Any:
    domains = []
    for status in data.domain_status():
        if not status["online"]:
            domains.append(
                {
                    "name": status["name"],
                    "db_path": status["db_path"],
                    "online": False,
                    "beings_count": 0,
                    "battle_count": 0,
                    "generation_depth": 0,
                    "avg_score": 0.0,
                    "champion": None,
                }
            )
            continue
        try:
            domains.append(data.domain_summary(status["name"]))
        except Exception:
            domains.append(
                {
                    "name": status["name"],
                    "db_path": status["db_path"],
                    "online": False,
                    "beings_count": 0,
                    "battle_count": 0,
                    "generation_depth": 0,
                    "avg_score": 0.0,
                    "champion": None,
                }
            )

    return jsonify({"domains": domains, "count": len(domains)})


@app.get("/api/domain/<name>/beings")
def api_domain_beings(name: str) -> Any:
    if name not in data.domain_paths():
        return jsonify({"error": f"Unknown domain '{name}'"}), 404
    try:
        beings = data.load_beings(name)
    except FileNotFoundError:
        return jsonify({"error": "Domain DB not available", "domain": name}), 503
    return jsonify({"domain": name, "count": len(beings), "beings": beings})


@app.get("/api/domain/<name>/champions")
def api_domain_champions(name: str) -> Any:
    limit = min(max(int(request.args.get("limit", 10)), 1), 100)
    if name not in data.domain_paths():
        return jsonify({"error": f"Unknown domain '{name}'"}), 404
    try:
        beings = data.load_beings(name)
    except FileNotFoundError:
        return jsonify({"error": "Domain DB not available", "domain": name}), 503
    champions = sorted(beings, key=lambda b: (b["score"], b["wins"]), reverse=True)[:limit]
    return jsonify({"domain": name, "count": len(champions), "champions": champions})


@app.get("/api/domain/<name>/battles")
def api_domain_battles(name: str) -> Any:
    limit = min(max(int(request.args.get("limit", 120)), 1), 500)
    if name not in data.domain_paths():
        return jsonify({"error": f"Unknown domain '{name}'"}), 404
    try:
        battles = data.load_domain_battles(name, limit=limit)
    except FileNotFoundError:
        return jsonify({"error": "Domain DB not available", "domain": name}), 503
    return jsonify({"domain": name, "count": len(battles), "battles": battles})


@app.get("/api/being/<being_id>")
def api_being(being_id: str) -> Any:
    being = data.find_being(being_id)
    if not being:
        return jsonify({"error": f"Being '{being_id}' not found"}), 404
    return jsonify(being)


@app.get("/api/being/<being_id>/lineage")
def api_being_lineage(being_id: str) -> Any:
    lineage = data.lineage(being_id)
    if lineage is None:
        return jsonify({"error": f"Being '{being_id}' not found"}), 404
    return jsonify(lineage)


@app.get("/api/being/<being_id>/battles")
def api_being_battles(being_id: str) -> Any:
    battles = data.battles_for_being(being_id)
    return jsonify({"being_id": being_id, "count": len(battles), "battles": battles})


@app.get("/api/activity")
def api_activity() -> Any:
    limit = min(max(int(request.args.get("limit", 40)), 1), 200)
    items = data.activity_feed(limit=limit)
    return jsonify({"items": items, "count": len(items)})


@app.get("/api/export")
def api_export() -> Any:
    battle_limit = min(max(int(request.args.get("battle_limit", 120)), 1), 1000)
    return jsonify(data.export_snapshot(battle_limit=battle_limit))


@app.get("/api/email/leaderboard")
def api_email_leaderboard() -> Any:
    limit = min(max(int(request.args.get("limit", 25)), 1), 500)
    requested_type = (request.args.get("type", "subject_line") or "").strip()
    being_type = None if requested_type.lower() == "all" else requested_type or "subject_line"
    try:
        leaderboard = data.load_email_leaderboard(limit=limit, being_type=being_type)
    except FileNotFoundError:
        return jsonify({"error": "Email arena DB not available", "db_path": data.email_db}), 503
    return jsonify(
        {
            "count": len(leaderboard),
            "type": being_type or "all",
            "leaderboard": leaderboard,
        }
    )


@app.get("/api/email/battles")
def api_email_battles() -> Any:
    limit = min(max(int(request.args.get("limit", 60)), 1), 500)
    requested_type = (request.args.get("type", "subject_line") or "").strip()
    battle_type = None if requested_type.lower() == "all" else requested_type or "subject_line"
    try:
        battles = data.load_email_battles(limit=limit, battle_type=battle_type)
    except FileNotFoundError:
        return jsonify({"error": "Email arena DB not available", "db_path": data.email_db}), 503
    return jsonify(
        {
            "count": len(battles),
            "type": battle_type or "all",
            "battles": battles,
        }
    )


@app.get("/api/email/personas")
def api_email_personas() -> Any:
    limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    try:
        personas = data.load_email_personas(limit=limit)
    except FileNotFoundError:
        return jsonify({"error": "Email arena DB not available", "db_path": data.email_db}), 503
    return jsonify({"count": len(personas), "personas": personas})


@app.get("/api/email/export")
def api_email_export() -> Any:
    leaderboard_limit = min(max(int(request.args.get("leaderboard_limit", 100)), 1), 1000)
    battles_limit = min(max(int(request.args.get("battles_limit", 300)), 1), 2000)
    requested_type = (request.args.get("type", "all") or "").strip()
    battle_type = None if requested_type.lower() == "all" else requested_type
    try:
        payload = data.export_email_snapshot(
            leaderboard_limit=leaderboard_limit,
            battles_limit=battles_limit,
            battle_type=battle_type,
        )
    except FileNotFoundError:
        return jsonify({"error": "Email arena DB not available", "db_path": data.email_db}), 503
    return jsonify(payload)


@app.get("/api/recovery-lawyers/export")
def api_recovery_lawyers_export() -> Any:
    requested_source = (request.args.get("source", "sample") or "sample").strip().lower()
    payload = data.export_recovery_snapshot(source=requested_source)
    return jsonify(payload)


@app.get("/api/sequences")
def api_sequences() -> Any:
    limit = min(max(int(request.args.get("limit", 10)), 1), 200)
    try:
        payload = data.load_email_sequence_rankings(limit=limit)
    except FileNotFoundError:
        return jsonify({"error": "Email arena DB not available", "db_path": data.email_db}), 503
    return jsonify(payload)


@app.get("/")
def serve_index() -> Any:
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return send_from_directory(BASE_DIR, "index.html")
    return jsonify({"message": "Colosseum API online"})


@app.get("/<path:path>")
def serve_static(path: str) -> Any:
    if path.startswith("api/"):
        return jsonify({"error": "API route not found"}), 404
    requested = BASE_DIR / path
    if requested.exists() and requested.is_file():
        return send_from_directory(BASE_DIR, path)
    return send_from_directory(BASE_DIR, "index.html")


def export_to_file(output_path: str, battle_limit: int) -> None:
    payload = data.export_snapshot(battle_limit=battle_limit)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACT-I Colosseum dashboard API")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", default=int(os.getenv("PORT", "5050")), type=int)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--export",
        dest="export_path",
        help="Write a static snapshot JSON file and exit.",
    )
    parser.add_argument(
        "--battle-limit",
        default=120,
        type=int,
        help="Battle rows per domain for export mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.export_path:
        export_to_file(args.export_path, battle_limit=args.battle_limit)
        print(f"Snapshot exported to {args.export_path}")
        return

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
