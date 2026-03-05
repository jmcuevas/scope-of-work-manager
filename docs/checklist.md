# Development Checklist

Track progress phase by phase. Check items off as completed.

---

## Phase 1: Foundation + Data Models (Week 1)
**Goal**: Auth works, all models migrated, admin seeded, CI passes, factories create valid test data.

### Project Setup
- [x] Django 5.2 project scaffolded (`scope_manager/`) *(2026-03-03)*
- [x] All 7 apps created: `core`, `projects`, `exhibits`, `notes`, `reviews`, `ai_services`, `exports` *(2026-03-03)*
- [x] Settings configured: PostgreSQL, django-allauth, WhiteNoise, Tailwind CDN, AI feature flag *(2026-03-03)*
- [x] `.env.example` created *(2026-03-03)*
- [x] `develop` branch created; branch strategy established *(2026-03-03)*

### Data Models
- [x] `core`: Company, User (email-based, role field), ProjectType, CSITrade *(2026-03-03)*
- [x] `projects`: Project, Trade (status workflow, unique constraint) *(2026-03-03)*
- [x] `exhibits`: ScopeExhibit, ExhibitSection, ScopeItem (hierarchical: parent FK + level + order) *(2026-03-03)*
- [x] `notes`: Note (cross-trade M2M, resolution workflow) *(2026-03-03)*
- [x] `reviews`: ChecklistItem, FinalReview, FinalReviewItem *(2026-03-03)*
- [x] All migrations generated and applied cleanly *(2026-03-03)*

### Django Admin
- [x] `core` admin: Company, User, ProjectType, CSITrade registered *(2026-03-03)*
- [x] `projects` admin: Project, Trade registered *(2026-03-03)*
- [x] `exhibits` admin: ScopeExhibit, ExhibitSection, ScopeItem registered *(2026-03-03)*
- [x] `notes` admin: Note registered *(2026-03-03)*
- [x] `reviews` admin: ChecklistItem, FinalReview, FinalReviewItem registered *(2026-03-03)*

### Seed Data
- [x] Management command: seed CSI trades (priority trades: Mechanical, Electrical, Plumbing, Fire Sprinkler, Drywall, Doors + full list) *(2026-03-03)*
- [x] Management command: seed project types (Office TI, Lab TI, Core & Shell, Seismic Retrofit, Mixed-Use, Other) *(2026-03-03)*

### Testing Infrastructure
- [x] `pytest.ini` configured (Django settings, test DB) *(2026-03-04)*
- [x] `conftest.py` with shared fixtures *(2026-03-04)*
- [x] Factory Boy factories for every model *(2026-03-04)*
- [x] Model constraint tests (unique trade per project, email uniqueness, etc.) *(2026-03-04)*

### Base Template
- [x] `templates/base.html`: top navbar, left sidebar, main content, right panel block, flash messages *(2026-03-04)*
- [x] Tailwind CSS + Flowbite wired via CDN, blue accent, HTMX CSRF configured *(2026-03-04)*

---

## Phase 2: Project Dashboard + Trade Setup (Week 2)
**Goal**: PM can create a project, paste 15+ trades from a spreadsheet, see a clean buyout dashboard, and update statuses — all without full page reloads.

### Project List
- [x] Project list view: company-scoped queryset (users only see their company's projects) *(2026-03-04)*
- [x] Project list template: table/cards showing name, number, project type, trade count, link to dashboard *(2026-03-04)*
- [x] Empty state when no projects exist ("Create your first project") *(2026-03-04)*
- [x] "New Project" button *(2026-03-04)*

### Project Create & Edit
- [x] `ProjectForm` (ModelForm): name, number, project_type, description, address *(2026-03-04)*
- [x] Project create view + template *(2026-03-04)*
- [x] Project edit view + template *(2026-03-04)*
- [x] Form validation and inline error display *(2026-03-04)*
- [x] Success redirect to buyout dashboard after create; back to dashboard after edit *(2026-03-04)*

### Buyout Dashboard
- [x] Dashboard view: loads project + all trades, company-scoped *(2026-03-04)*
- [x] Stats bar: total trades + count per status (Not Started, In Progress, Out to Bid, etc.) *(2026-03-04)*
- [x] Trades table: CSI code, trade name, budget, status badge, assigned PE, link to scope editor (placeholder) *(2026-03-04)*
- [x] Empty state when no trades yet *(2026-03-04)*
- [x] "Import Trades" and "Add Trade" buttons visible on dashboard *(2026-03-04)*

### Trade Import (paste-based)
- [ ] ~~Deferred to post-MVP~~ — manual add is sufficient for pilot. Fuzzy match + confirm flow to be designed carefully before implementation.

### Manual Single-Trade Add
- [x] Trade add form: CSI trade dropdown + budget field *(2026-03-04)*
- [x] Redirect to dashboard after trade created *(2026-03-04)*
- [x] Validation: prevent duplicate CSI trade on same project *(2026-03-04)*

### HTMX Interactions
- [x] Trade status update: status dropdown → hx-post → updates Trade.status → returns updated row *(2026-03-04)*
- [x] Trade PE assignment: PE dropdown → hx-post → updates Trade.assigned_to → returns updated row *(2026-03-04)*

### URL & Navigation
- [x] `projects/urls.py` wired: list, create, edit, dashboard, trade add/update *(2026-03-04)*
- [x] Left sidebar updates when inside a project: show project name + back to project list link *(2026-03-04)*
- [x] Redirect root URL `/` to project list *(2026-03-04)*

### Tests
- [x] Company isolation: user cannot access another company's project (returns 404) *(2026-03-04)*
- [ ] ~~`parse_trade_import()` tests~~ — deferred with trade import feature (post-MVP)
- [x] Duplicate CSI trade on same project rejected *(2026-03-04)*
- [x] Trade status update persists correctly *(2026-03-04)*
- [x] Dashboard trade count matches actual Trade records *(2026-03-04)*

---

## Phase 3: Scope Exhibit Editor (Weeks 3–4)
**Goal**: Full editor workflow — pick template → clone → edit sections/items → reorder → indent/outdent. Hierarchical numbering correct after every operation.

### Week 3 — Template picker + clone + basic editor
- [ ] Template/past exhibit picker (filtered by CSI trade, sorted by project type match)
- [ ] Clone service (deep copy with parent FK remapping)
- [ ] Create-blank-exhibit service (5 default sections)
- [ ] Editor page layout: two-column (content left, sidebar right)
- [ ] Section CRUD: add, rename, delete, reorder (HTMX)
- [ ] Item CRUD: add, click-to-edit, delete (with descendants)

### Week 4 — Hierarchy + polish
- [ ] Item reordering: up/down with subtree integrity
- [ ] Item indent/outdent with cascade to descendants
- [ ] Hierarchical numbering (server-side: 1, 1.1, 1.1.1)
- [ ] Scope description textarea (saved to DB)
- [ ] Save-as-template flow
- [ ] Exhibit status transitions (DRAFT → READY_FOR_REVIEW → READY_FOR_BID → FINALIZED) with Trade status sync
- [ ] Editor integration tests

---

## Phase 4: PDF Export (Week 5, first half)
**Goal**: Clicking "Export PDF" downloads a clean, professional Exhibit A. Tested at multiple sizes.

- [ ] PDF HTML template: header, sections, hierarchical items, page numbers
- [ ] Print CSS: `@page` rules, margins, typography
- [ ] WeasyPrint service: `generate_exhibit_pdf()` → returns bytes
- [ ] Download view with correct `Content-Disposition` header
- [ ] "Export PDF" button in editor footer
- [ ] Tested: 1-page, 5-page, 10-page exhibits

---

## Phase 5: Notes & Cross-Trade Tracking (Week 5–6)
**Goal**: Notes appear in all relevant trade contexts. Open question count accurate. Dashboard shows open question count.

- [ ] Note creation form (primary trade + related trades + type + source)
- [ ] Notes sidebar in scope editor (HTMX)
- [ ] Cross-trade visibility (note tagged to multiple trades appears in each)
- [ ] Note resolution flow
- [ ] Project-level open questions view
- [ ] Open questions badge on buyout dashboard
- [ ] Tests: cross-trade visibility, company isolation, resolution persistence

---

## Phase 6: AI Scope Assistant (Week 6–7)
**Goal**: Both AI functions work end-to-end. Failures degrade gracefully. PM can complete any exhibit with or without AI.

- [ ] `generate_scope_from_description()` — description → exhibit sections + items
- [ ] `generate_scope_item()` — natural language → single inclusion/exclusion
- [ ] System prompts with exhibit language conventions + JSON output schema
- [ ] Response parsing with fallback on malformed JSON
- [ ] Error handling: 30s timeout, 1 retry on 5xx, graceful failure message
- [ ] `AIRequestLog` model for metrics (tokens, latency, success/failure — no prompt text)
- [ ] Editor integration: "Generate Scope" button + per-section NL input → preview → accept/edit/reject
- [ ] Tests with mocked API (no real API calls in tests)
- [ ] Feature flag: all workflows function with `AI_ENABLED=False`

---

## Phase 7: Final Review + Hardening + Launch (Weeks 7–8)

### Week 7: Final Review
- [ ] Review generation service: open notes check, cross-trade notes check, checklist items check
- [ ] Review UI: checklist display with summary scorecard, PM response fields
- [ ] "Run Final Review" button in editor
- [ ] Tests for review generation logic

### Week 8: Hardening + Pilot Launch
- [ ] Sentry error tracking
- [ ] Query performance audit (N+1 queries, missing indexes)
- [ ] Security audit: every view checked for auth + company isolation + role enforcement
- [ ] Production deployment (Railway or Render): gunicorn, WhiteNoise, env vars, SSL
- [ ] Seed production data: company, users, real trade templates, checklist items
- [ ] Pilot launch: 2–3 PMs + PEs onboarded, onboarding guide written
