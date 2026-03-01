# Dashboard Optimizations (Aiko Feedback - Feb 27, 2026 ~2AM)

## Priority Enhancements

### 1. 🌳 Family Tree in Being Profiles (HIGH)
**Current:** Domain-level family tree shows all beings
**Requested:** Each being's profile modal should show THEIR specific lineage chain
- Show parent → grandparent → great-grandparent chain
- Visual mini-tree in the being modal
- Click through lineage to explore ancestors

### 2. 🎭 Role Playing Scenarios Display (HIGH)
**Current:** Only shows system prompts
**Requested:** Show the actual scenarios/challenges beings are evaluated on
- Display the test prompts/scenarios
- Show what judges are looking for
- Make scoring criteria visible

### 3. 🤖 Model Performance Tracking (MEDIUM)
**Current:** Model column shows "unknown" or null
**Requested:** Track which LLMs perform best for the Unblinded Formula
- Populate model field in database
- Add model filter/breakdown in dashboard
- Show model performance comparison chart

### 4. ⚔️ Interactive Battle Trails (MEDIUM)
**Current:** Battle history table is static/empty
**Requested:** Make battles clickable and explorable
- Click battle → see full transcript
- Replay battle dialogue
- Filter by winner/loser
- Sort by score differential

## Implementation Notes
- Use compound development: enhance existing code, don't rebuild
- Each feature builds on the current foundation
- Backend (server.py) needs battle logging enabled in daemon
- Model tracking requires daemon to log which LLM was used

## Data Requirements
- `model` field needs populated in beings table
- Battle history table needs actual battle records
- Scenario/challenge prompts need storage

---
*Feedback captured 2:00 AM EST - ready for Codex implementation*
