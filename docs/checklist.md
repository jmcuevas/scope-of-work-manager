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
- [ ] Project list view: company-scoped queryset (users only see their company's projects)
- [ ] Project list template: table/cards showing name, number, project type, trade count, link to dashboard
- [ ] Empty state when no projects exist ("Create your first project")
- [ ] "New Project" button

### Project Create & Edit
- [ ] `ProjectForm` (ModelForm): name, number, project_type, description, address
- [ ] Project create view + template
- [ ] Project edit view + template
- [ ] Form validation and inline error display
- [ ] Success redirect to buyout dashboard after create; back to dashboard after edit

### Buyout Dashboard
- [ ] Dashboard view: loads project + all trades, company-scoped
- [ ] Stats bar: total trades + count per status (Not Started, In Progress, Out to Bid, etc.)
- [ ] Trades table: CSI code, trade name, budget, status dropdown, assigned PE, link to scope editor (placeholder for now)
- [ ] Empty state when no trades yet
- [ ] "Import Trades" and "Add Trade" buttons visible on dashboard

### Trade Import (paste-based)
- [ ] `parse_trade_import(text)` service function in `projects/services.py`
- [ ] Parser handles: tab-separated and comma-separated input, dollar signs in budget, extra whitespace, blank lines, invalid rows (skip gracefully)
- [ ] Import form: textarea where PM pastes from spreadsheet + submit
- [ ] Import view: parse → show preview of parsed rows → confirm → bulk-create Trade records
- [ ] Duplicate CSI codes within the same project handled gracefully (skip or warn, don't crash)
- [ ] 8-10 unit tests for `parse_trade_import()` covering all edge cases

### Manual Single-Trade Add
- [ ] Inline add-trade form on dashboard: CSI trade dropdown + budget field
- [ ] HTMX POST → creates Trade → returns updated trades table (no page reload)
- [ ] Validation: prevent duplicate CSI trade on same project

### HTMX Interactions
- [ ] Trade status update: status dropdown change → `hx-patch` → updates Trade.status → returns updated row
- [ ] Trade PE assignment: PE dropdown change → `hx-patch` → updates Trade.assigned_to → returns updated row

### URL & Navigation
- [ ] `projects/urls.py` wired: list, create, edit, dashboard, import, trade add/update
- [ ] Left sidebar updates when inside a project: show project name + back to project list link
- [ ] Redirect root URL `/` to project list

### Tests
- [ ] Company isolation: user cannot access another company's project (returns 404)
- [ ] `parse_trade_import()`: 8-10 edge case unit tests
- [ ] Duplicate CSI trade on same project rejected
- [ ] Trade status update persists correctly
- [ ] Dashboard trade count matches actual Trade records

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
