# Forge Streaming — N-Backlog Wave

**Lane:** `forge-streaming` · **Scope:** `static/forge/*`, forge docs  
**Read first:** [STATE.md](../STATE.md), [WAVES.md](../../WAVES.md), [FORGE_HYGIENE.md](FORGE_HYGIENE.md)  
**Prereqs:** N5 SSE streaming shipped (CM-W1), swarm-viz.js canvas renderer live on `/colony`

This backlog captures the next concrete improvements to the forge streaming
experience — real-time session visualization, spend guardrails, and multi-agent
coordination UX. Each item is sized for a single PR / wave.

---

## Items

### B-N1: Live session transcript panel (real-time SSE viz)

**Priority:** P0  
**Effort:** 3–4 days (full-stack)

**Description:**

The current forge console renders streamed `text_delta` text into a single
`#stream` div, but it has no live session *telemetry* panel — the user cannot
see what the agent is doing between turns (tool calls, file writes, errors,
token burn) without scrolling back through transcript history. This is a gap
vs Cursor / Claude Code which show a live activity feed.

Implement a collapsible "Session Pulse" panel anchored beside (or overlaid on)
the composer. It subscribes to the same SSE event stream that drives the chat
and surfaces structured event cards in real time:

- `tool_call` → show tool name + target path (collapsible args on click)
- `tool_result` → stdout preview (truncated to 600 chars, expandable)
- `error` → red card with retry hint
- `compaction` → teal digest card ("context compacted, N turns folded")
- `cost` → inline `$0.03` tick per assistant turn

Panel is client-only: it piggybacks on the existing SSE event bus in
`app.js` (`_onSseEvent`). No new API endpoints. State is ephemeral (resets on
session switch). Pulse panel persists collapsed state in
`localStorage["cm_pulse_collapsed"]`.

Add a `pulse.css` file under `static/forge/` and load it from `index.html`
after `jungle-theme.css`.

**Acceptance:**

- Panel renders live tool-call/error/compaction cards during an active session
- Panel collapses to a 28px tab; expand/collapse state survives reload
- No regression in existing streaming chat render path
- `pytest` green; spot-check at `/` with `STREAM_ENABLED=1`

---

### B-N2: Spend alerts & per-session budget caps

**Priority:** P0  
**Effort:** 2–3 days (server + small UI)

**Description:**

The cost dashboard (`modal-cost`) is a passive historical view. Once a session
is burning through an expensive model, the user has no guardrail until they
open the dashboard manually. Add proactive spend alerts and a per-session
budget guard.

**Server side** (`server.py`):

- Add `max_session_budget_usd` field to the session record (default `null`,
  meaning uncapped). Settable via `POST /api/sessions/{sid}/budget` (owner or
  session owner only).
- During streaming, after each model call, accumulate `session_cost_usd`.
  When `session_cost_usd >= 0.50 * max_session_budget_usd`, emit a
  `budget_warning` SSE event at `0.5` and `0.9` thresholds.
- When `session_cost_usd >= max_session_budget_usd`, emit `budget_exceeded`
  and hard-stop the session (same path as `/stop` — emit `done` event with
  `reason: "budget_exceeded"`).

**Client side** (`app.js`):

- On `budget_warning`: toast banner (amber) with "Session at 50% of budget —
  $0.42 of $1.00 used. [Open dashboard →]"
- On `budget_exceeded`: red banner + auto-stop; show "Budget exceeded" in
  `#hdr-status`.
- Composer shows a small budget dial when a cap is set:
  `💲 $0.42 / $1.00` with a mini progress bar (gold → amber → red).

**Settings modal:** Add a "Session budget" input under the Advanced tab
(owner-only by default; per-user when per-user isolation is live).

**Acceptance:**

- `POST /api/sessions/{sid}/budget` persists cap; null cap = uncapped
- SSE `budget_warning` events fire at 50% and 90% of cap
- SSE `budget_exceeded` event + hard-stop at 100%
- Client toast renders without blocking chat input
- Tests: `tests/test_session_budget.py` (≥ 6 tests covering cap persistence,
  threshold events, hard-stop, non-owner rejection)

---

### B-N3: Multi-agent coordination tree view (live sub-agent DAG)

**Priority:** P1  
**Effort:** 4–5 days (canvas + server events)

**Description:**

When the orchestrator spawns sub-agents (Claude Code-style fan-out), the user
currently has no way to see the tree of who is doing what. The `swarm-viz.js`
canvas already supports a hierarchical *tree layout* mode (`setTreeState`), but
no server endpoint feeds it parent-child relationships.

**Server side** (`server.py`):

- Track `parent_sid` on session creation when a session is spawned by another
  session (new optional `?parent_sid=...` query param on
  `POST /api/sessions`).
- Add `GET /api/sessions/{sid}/children` → returns direct child sessions with
  their status, label, model, and progress.
- Add `GET /api/sessions/{sid}/tree` → returns the full DAG from the target
  session down to leaf agents (max depth 8 to prevent abuse).

**Client side** (`swarm_viz.html`):

- Replace the static `window.__swarmState` poll with a new poll of
  `GET /api/sessions/{activeSid}/tree` every 2 s.
- Feed the response into `setTreeState(tree)` to render the parent-child DAG
  with bezier edges, tier badges, and hover tooltips (already implemented in
  `swarm-viz.js`).
- Add a "Focus session" input at the top: type a session ID (or pick from a
  dropdown of recent sessions) to root the tree at that node.
- Add a "Ring / Tree" toggle button (already supported via `setLayoutMode`).

**Acceptance:**

- `GET /api/sessions/{sid}/tree` returns nested children with status + model
- `swarm_viz.html` renders the DAG with animated edges and hover tooltips
- Tree re-polls every 2 s; smooth lerp between layouts (already in
  `swarm-viz.js`)
- Depth limit enforced server-side (≤ 8)
- Tests: `tests/test_session_tree.py` (≥ 5 tests for parent-child binding,
  tree endpoint, depth limit, non-owner rejection)

---

### B-N4: Streaming presence indicator in sidebar session list

**Priority:** P1  
**Effort:** 1 day (client-only)

**Description:**

The sidebar session list (`#session-list`) shows session titles and a status
dot, but the dot is static (idle/running) and does not reflect *streaming*
state — whether the agent is actively emitting tokens right now. Users have no
glanceable way to know "which session is talking" when multiple tabs are open.

Enhance the session list rendering in `app.js`:

- When an SSE `text_delta` event arrives for a session, add a
  `.streaming-now` class to that session's sidebar row for the duration of
  the stream.
- `.streaming-now` adds a subtle animated gold border pulse + a small
  "streaming…" label next to the title.
- When the stream ends (`done` event), remove the class.
- If a background session (not the active tab) is streaming, add a tiny
  notification badge (count of unread deltas) on its row — click to switch
  tab and jump to live tail.

This is purely client-side state derived from the existing SSE event bus. No
server changes.

**Acceptance:**

- Active streaming session shows animated gold pulse in sidebar
- Background streaming session shows unread-delta badge
- Clicking a background streaming session switches to it and scrolls to tail
- No regression in non-streaming mode
- `pytest` green (no server changes); spot-check at `/`

---

### B-N5: Agent handoff timeline (swarm-viz banana arcs → structured log)

**Priority:** P2  
**Effort:** 2 days (client-only)

**Description:**

The `swarm-viz.js` canvas already animates "banana arc" projectiles when an
agent transitions to `DONE` (handoff back to orchestrator) or `RUNNING`
(receiving work). These are delightful but ephemeral — once the animation
fades, there is no record of *when* handoffs happened or *which* agents
coordinated.

Add a persistent "Handoff Log" panel below the canvas on `swarm_viz.html`:

- Each handoff event (banana arc spawn) appends a timestamped row:
  `14:32:07  agent-3 → orchestrator  done  +$0.04`
  `14:32:09  orchestrator → agent-7  running  gpt-4o`
- Log is capped at 50 rows (FIFO). Scrollable, monospace, dark panel.
- Color-code by transition type: green (done), blue (running), red (error).
- Add a "Clear log" button and a "Pause/resume" toggle for the canvas
  animation (so users can freeze the viz without stopping the log).

This reuses the existing `_detectHandoffs` hook in `swarm-viz.js` — we add a
callback that the page subscribes to.

**Acceptance:**

- Handoff log captures every banana arc event with timestamp + agents + cost
- Log persists for the page lifetime (resets on reload)
- Pause/resume toggle stops animation but log continues
- No regression in canvas rendering
- `pytest` green (no server changes); spot-check at `/colony`

---

## Sequencing recommendation

```
B-N1 (Pulse panel)  ──▶  B-N2 (Spend alerts)  ──▶  B-N3 (Coordination tree)
                              │
                              ▼
                      B-N4 (Sidebar presence)  ──▶  B-N5 (Handoff log)
```

B-N1 and B-N2 are independent and can run in parallel. B-N3 depends on
B-N2's session-budget schema (shared `parent_sid` field). B-N4 and B-N5 are
polish items that slot in after the core telemetry is live.

---

## Out of scope (future waves)

- WebSocket upgrade for sub-100ms event latency (current SSE is fine for forge)
- Mobile-native push for spend alerts (PWA push exists but is owner-gated)
- Multi-user real-time cursors (requires CRDT layer — S6 Layer 3+)
- Voice narration of agent output (separate accessibility track)
