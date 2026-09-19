# Forge UI — Maintainer Hygiene Checklist

**Lane:** `forge-streaming` · **Scope:** `static/forge/*` and forge-related docs.  
**Read first:** [STATE.md](../STATE.md), [README.md](../README.md), [WAVES.md](../../WAVES.md), [OFFICE_HOURS.md](../../OFFICE_HOURS.md).

Use this before editing the Forge console, landing a UI wave, or reviewing an
automation PR that touches streaming or frontend assets.

---

## 0. Architecture overview (`static/forge/`)

Vanilla JS + vendored Tailwind (`tailwind.css` built from `tailwind.input.css` via
`npx tailwindcss`). No bundler, no runtime CDN. CSP `script-src 'self'`. Each
route is a standalone `.html` file sharing the `static/forge/` asset pool.

| Route | Entry HTML | Key JS | Role |
|-------|-----------|--------|------|
| `/` | `index.html` | `app.js`, `index-shell.js`, `workbench.js` | Main console / chat shell |
| `/swarm` | `swarm.html` | `swarm.js` | Full-page canvas swarm visualizer |
| `/colony` | `swarm_viz.html` | `swarm-viz.js` | Colony visualizer (ring + tree modes, ES module) |
| `/terminal` | `terminal.js` | `terminal.js` | Claude Code-style REPL (gated OFF) |
| `/audit` | `audit.html` | `audit.js` | Tamper-evident audit log viewer (owner-only) |

### JS load order (per page)

- `index.html` → `agents-hub.js` → `omni-search.js` → `fleet-store.js` →
  `workbench.js` → `cursor-desk.js` → `gremlins.js` → `push.js` →
  `three-card-triage.js` → `egress-consent.js` → `app.js` → `field-report.js` →
  `feedback.js` → `pwa.js` → `index-shell.js`
- `swarm.html` → `swarm.js`
- `terminal.html` → `egress-consent.js` → `terminal.js` → `feedback.js`
- `audit.html` → `audit.js`

### Cross-module contracts

- `window.api` — exposed by `app.js`; wraps fetch with JSON + Bearer auth + M-4
  egress consent gate. Other modules (`agents-hub.js`, `workbench.js`) call it
  instead of re-implementing auth.
- `window.EgressConsent` — exposed by `egress-consent.js`. `api()` and
  `terminal.api()` both call `EgressConsent.ensure()` before model calls.
- `window.AgentsHub` — Cursor-style session + automation modal (Dynamically
  injected into the DOM by `_ensureModal()`).
- `window.Workbench` — Injects toolbar, fleet panel, embedded terminal into
  `index.html`'s main column.
- `window.__swarmState` — Global written by `swarm_viz.html`; polled at 500 ms
  by `swarm-viz.js`.

### Accessibility / meta

All five UI pages (`index.html`, `swarm.html`, `terminal.html`, `swarm_viz.html`,
`audit.html`) now carry `<meta name="description">`. `<title>` is set per page.
`terminal.html` input has `aria-label`. `audit.html` table headers are `<th scope>`.
`index.html` uses `role="tablist"` on the dynamic tab bar. Steady Ground crisis
modal is present on every page (offline-safe, no JS bundle dependency).

### Documentation quality

| File | Top-level docblock | Inline / function docs | Verdict |
|------|-------------------|------------------------|---------|
| `app.js` | 1 line | Inline comments on M-4, N5 streaming, proxy shim | adequate — dense file; consider JSDoc on public funcs |
| `swarm.js` | 2 lines | none | minimal |
| `terminal.js` | 3-line block | Inline on each event type | good |
| `swarm-viz.js` | Full module docblock + GDD refs | JSDoc on every exported function | best in dir |
| `audit.js` | 2-line block + S-3 ref | Inline on hash-chain verify | good |
| `agents-hub.js` | 1 line | none on methods | minimal — large file |
| `workbench.js` | 1 line | none on methods | minimal |
| `index-shell.js` | TBD | TBD | verify |

No `TODO` / `FIXME` / `HACK` markers found in `static/forge/`.

### Dead-code / shim notes

- `index.html` lines ~1154–1191: ~30 hidden proxy elements (`display:none`,
  `aria-hidden="true"`) used by `app.js` to avoid null-ref errors after the
  Settings sidebar was migrated into `modal-settings`. Documented inline. Not
  dead — kept intentionally. Do not remove without auditing `app.js`
  `getElementById` call sites.

---

## 1. Path map (`static/forge/`)

| Path | Role |
|------|------|
| `index.html` | Main console shell; links vendored `tailwind.css` |
| `app.js`, `workbench.js` | Session UI, composer, event polling |
| `agents-hub.js` | Agents hub (sessions, automations, personas, rules) |
| `terminal.html`, `terminal.js` | Web terminal (gated OFF by default) |
| `swarm.html`, `swarm.js` | Live swarm view |
| `swarm_viz.html`, `swarm-viz.js` | Colony standalone visualizer (canvas, ring + tree modes) |
| `feedback.js`, `field-report.js`, `three-card-triage.*` | Field Report / triage |
| `push.js`, `pwa.js`, `sw.js`, `manifest.webmanifest` | PWA + push |
| `tailwind.input.css` | Tailwind source directives |
| `tailwind.css` | **Built output** (image build or local `npx`; not hand-edited) |
| `jungle-theme.css` | Theme tokens (CSS variables) |

**Coordination:** Automation waves may touch `server.py` (compaction, catalog, streaming).
UI track stays in `static/forge/*` unless explicitly merged. If an open
`automation/wave-*` PR exists, finish or pause before overlapping server changes.

---

## 2. Vendored Tailwind build

Phase 2 is live: runtime CDN is gone; `index.html` links `/static/forge/tailwind.css`.
The dev host has **no Node** — CI and the Docker image are the verification path.

**Config:** `tailwind.config.js` scans `./static/forge/*.html` and `*.js`.

**Local build (when Node is available):**

```bash
npx --yes tailwindcss@3.4.17 \
  -i static/forge/tailwind.input.css \
  -o static/forge/tailwind.css --minify
```

**CI (`css` job):** same command to `/tmp/tailwind.css`; asserts non-trivial output
and spot-checks `.flex` + `gold` arbitrary-value classes.

**Dockerfile:** runs the identical build at image time into `static/forge/tailwind.css`.

**After CSS changes:** run the build (or rely on CI `css` job). Eyeball Forge at `/`
after deploy — owner confirmed prod render; regressions are owner-visible.

---

## 3. Streaming flags (N5 / CM-W1)

| Env | Default | Effect |
|-----|---------|--------|
| `STREAM_ENABLED` | off (`""`) | When `1` / `true` / `yes`, SSE emits `text_delta` events; forge + terminal render live partial text |

- Default-off preserves pre-N5 behaviour (byte-identical non-stream path).
- Server redacts streamed chunks; errors fall back to non-streaming.
- **Do not flip in production** without owner intent — set via Fly env / secrets policy.

Forge polls session events; no separate frontend flag — behaviour follows server env.

---

## 4. Verify commands

**Full suite (matches CI / office hours):**

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt pytest
mkdir -p data
DATA_DIR=./data ./.venv/bin/python -c "import server"
DATA_DIR=./data ./.venv/bin/pytest tests/ -q
```

**Focused:**

```bash
DATA_DIR=./data ./.venv/bin/pytest tests/test_streaming.py -q
DATA_DIR=./data ./.venv/bin/pytest tests/test_vendored_tailwind.py -q   # when present
```

**UI spot-check:** Forge at `/` (or `/forge` per [OFFICE_HOURS.md](../../OFFICE_HOURS.md)) — login, composer,
streaming text deltas when `STREAM_ENABLED=1`, mobile drawer ≤767px if touched.

**Import smoke:** `DATA_DIR=./data python -c "import server"` (CI runs this before pytest).

---

## 5. Branch + claim discipline

- Branch per task: `work/<topic>` or `cursor/<topic>-<date>`; never `git add -A`.
- Before multi-file forge edits: `work-check.sh start --area forge-streaming`.
- Claim: `REPO=CodeMonkeys AREA=forge-streaming WHO=<name> BRANCH=<branch> work-claim.sh claim`.
- Deploy is **owner-gated** (`fly deploy`); automation PRs do not deploy.

---

## 6. N-backlog / automation queue status

**As of 2026-07-13:** Safe automation backlog is **exhausted**. [WAVES.md](../../WAVES.md) Active queue
is empty — **do not start blocked automation waves.**

| Category | Status | Next action |
|----------|--------|-------------|
| CM-W1–W7 (N5 streaming, N8 compaction, N12 catalog, lint, triage, session ownership) | ✅ merged | — |
| CM-UI-W1–W3 (Forge parity track) | ✅ done on `work/frontend-polish` | Owner deploy when ready |
| **S5 notify-on-done** | ✅ merged via PR #45; inert until `NOTIFY_WEBHOOK_URL` is set | Owner enables webhook secret when ready |
| OAuth app registration, webhook secrets | **owner-gated** | Owner registers apps + sets Fly secrets |
| Terminal activation (`TERMINAL_ENABLED` + `TERMINAL_EXEC_ENABLED`) | **owner-gated** | Both default OFF → 404 |
| `fly deploy` / prod config | **owner-gated** | Not automation |
| [SECURITY.md](../../SECURITY.md) substantive edits | **owner-gated** | Manual merge |
| S6 Layers 2–4 (workspace jail, per-user secrets, shell sandbox) | **owner-gated** | Owner decision |

**Executor rule:** If Active queue is `_(none)_`, document status (this section or
[WAVES.md](../../WAVES.md)) and stop — do not fabricate waves or merge owner-gated work.

See [WAVES.md](../../WAVES.md) § Blocked / owner-gated for the canonical list.
