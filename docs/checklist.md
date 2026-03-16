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

#### URL & Routing
- [x] Create `exhibits/urls.py` with `app_name = 'exhibits'` — entry flow URLs (open/pick/start) + editor URL + all HTMX section/item endpoints *(2026-03-05)*
- [x] Wire `exhibits/` into `scope_manager/urls.py` *(2026-03-05)*

#### Services (`exhibits/services.py`)
- [x] `create_blank_exhibit(trade, user)` — creates exhibit + 5 default sections: General Conditions, Scope of Work, Specific Inclusions, Specific Exclusions, Clarifications & Assumptions *(2026-03-05)*
- [x] `clone_exhibit(source_exhibit, trade, user)` — deep-copies all sections and items; two-pass approach: create items with `parent=None` first, then remap parent FKs using old→new pk map *(2026-03-05)*

#### Entry Flow Views
- [x] `trade_scope_open` — checks if exhibit already exists for the trade's `(project, csi_trade)` pair; redirects to editor if found, picker if not *(2026-03-05)*
- [x] `template_picker` — lists templates (`is_template=True`) + finalized past exhibits for the same CSI trade, sorted by project type match then date *(2026-03-05)*
- [x] `exhibit_start` (POST) — calls clone or create-blank service based on `source` param; sets `trade.status = SCOPE_IN_PROGRESS`; redirects to editor *(2026-03-05)*

#### Template Picker Page
- [x] `templates/exhibits/picker.html` — "Start from Blank" button + company template cards + past exhibit cards; each card has a form that POSTs to `exhibit_start` with `source=<pk>` or `source=blank` *(2026-03-05)*

#### Editor Page
- [x] `exhibit_editor` view — fetches exhibit (company-scoped), prefetches sections with items *(2026-03-05)*
- [x] `templates/exhibits/editor.html` — two-column layout: section list (left, ~70%) + placeholder sidebar (right, ~30%); scope description textarea with manual Save button *(2026-03-05)*

#### Section CRUD (HTMX — all return `partials/section_list.html`)
- [x] `partials/section_list.html` + `partials/section.html` — section list is the HTMX swap target (`id="section-list"`); each section shows name, rename/delete/move-up/move-down controls, its item list, and an "Add Item" button *(2026-03-05)*
- [x] `section_add` view — appends new section at end; returns section list *(2026-03-05)*
- [x] `section_rename` view — updates section name; returns section list *(2026-03-05)*
- [x] `section_delete` view — deletes section (cascade removes items); returns section list *(2026-03-05)*
- [x] `section_move` view — reads `direction` param (up/down), swaps `order` with adjacent section; returns section list *(2026-03-05)*

#### Item CRUD (HTMX — target is item list within a section, `id="items-<section_pk>"`)
- [x] `partials/item.html` + `partials/item_form.html` — display mode shows text + Edit/Delete buttons; edit mode shows textarea + Save/Cancel *(2026-03-05)*
- [x] `item_add` view — creates top-level item (`level=0`, `parent=None`) at end of section; returns section's item list *(2026-03-05)*
- [x] `item_edit` view — GET returns edit form partial; POST saves text and returns display partial (outerHTML swap on `#item-<pk>`) *(2026-03-05)*
- [x] `item_delete` view — recursively collects item + all descendants, deletes all; returns section's item list *(2026-03-05)*

#### Wiring
- [x] Update `trade_row.html` "Open Scope →" link to `{% url 'exhibits:trade_scope_open' trade.project.pk trade.pk %}` *(2026-03-05)*

### Week 4 — Hierarchy + polish

#### URL Additions
- [x] Add 5 new patterns to `exhibits/urls.py`: `item_move`, `item_indent`, `item_outdent`, `exhibit_save_as_template`, `exhibit_update_status` *(2026-03-05)*

#### Hierarchical Numbering
- [x] `compute_section_numbering(section)` in `services.py` — builds item tree in memory, recursively assigns number strings (`1`, `1.1`, `1.1.1`); returns `{item_pk: "1.2.3"}` dict *(2026-03-05)*
- [x] `exhibits/templatetags/exhibit_tags.py` — `get_item` filter so templates can do `{{ numbers|get_item:item.pk }}` *(2026-03-05)*
- [x] Update `_item_list_response` and `_section_list_response` in `views.py` to call `compute_section_numbering` and pass `numbers` dict to templates *(2026-03-05)*
- [x] Update `item.html` to display the hierarchical number prefix before item text *(2026-03-05)*

#### Item Reordering
- [x] `item_move` view — finds siblings (same `parent` + same `section`), swaps `order` with adjacent sibling in given direction; subtree follows for free since children are always rendered under their parent; returns item list *(2026-03-05)*
- [x] Add ↑ / ↓ buttons to `item.html` (visible on hover, alongside Edit/Delete) *(2026-03-05)*

#### Item Indent / Outdent
- [x] `indent_item(item)` in `services.py` — finds previous sibling; sets `item.parent = previous_sibling`, `item.level += 1`, appends to end of new parent's children; cascades `level += 1` to all descendants via `bulk_update` *(2026-03-05)*
- [x] `outdent_item(item)` in `services.py` — sets `item.parent = item.parent.parent` (may be `None`), `item.level -= 1`, appends to end of new sibling group; cascades `level -= 1` to all descendants via `bulk_update` *(2026-03-05)*
- [x] `item_indent` and `item_outdent` views — call the respective service functions; return item list for the section *(2026-03-05)*
- [x] Add → (indent) and ← (outdent) buttons to `item.html` (visible on hover) *(2026-03-05)*

#### Save-as-Template
- [x] `save_as_template(source_exhibit, user)` in `services.py` — reuses clone logic with `is_template=True`, `project=None` *(2026-03-05)*
- [x] `exhibit_save_as_template` view (POST) — calls service, redirects to original exhibit's editor with a success flash message *(2026-03-05)*
- [x] Add "Save as Template" button to editor header *(2026-03-05)*

#### Exhibit Status Transitions
- [x] `exhibit_update_status` view (POST) — validates status value; updates `exhibit.status`; syncs trade status: `READY_FOR_BID` → trade `OUT_TO_BID`, `FINALIZED` → trade `SUBCONTRACT_ISSUED` (never regresses trade status); trade looked up via `(exhibit.project, exhibit.csi_trade)` *(2026-03-05)*
- [x] Replace static status badge in `editor.html` header with a `<select>` form that auto-submits on change to `exhibit_update_status` *(2026-03-05)*

#### Integration Tests (`exhibits/tests.py`)
- [x] Service tests: `create_blank_exhibit` (5 sections), `clone_exhibit` (parent FK remapping), `save_as_template` (`is_template=True`, `project=None`) *(2026-03-05)*
- [x] Entry flow tests: `trade_scope_open` redirects correctly; `exhibit_start` sets trade to `SCOPE_IN_PROGRESS`; company isolation (404 for other company's exhibit) *(2026-03-05)*
- [x] Section CRUD tests: add, rename, delete (cascades items), move (order swaps correctly) *(2026-03-05)*
- [x] Item CRUD tests: add, edit, delete with descendants *(2026-03-05)*
- [x] Item reorder tests: up/down swaps correct siblings; first/last item no-ops *(2026-03-05)*
- [x] Indent/outdent tests: correct parent + level after indent; correct parent + level after outdent; descendants cascade level change *(2026-03-05)*
- [x] Numbering tests: `compute_section_numbering` returns correct strings for flat and nested structures *(2026-03-05)*
- [x] Status transition tests: trade status synced at `READY_FOR_BID` and `FINALIZED`; other transitions leave trade unchanged *(2026-03-05)*

---

## Phase 4: PDF Export (Week 5, first half)
**Goal**: Clicking "Export PDF" downloads a clean, professional Exhibit A. Tested at multiple sizes.

### Setup
- [x] Verify WeasyPrint is in venv and install pango system dependency via Homebrew *(2026-03-05)*
- [x] Create `exports/services.py` *(2026-03-05)*
- [x] Create `exports/urls.py` with `app_name = 'exports'` *(2026-03-05)*
- [x] Wire `exports/urls.py` into `scope_manager/urls.py` *(2026-03-05)*

### PDF Template (`templates/exports/exhibit_pdf.html`)
- [x] Document header block: "Exhibit A — Scope of Work" title, company name, project name + number, CSI trade name + code, export date *(2026-03-05)*
- [x] Scope description block: rendered only if non-empty *(2026-03-05)*
- [x] Section loop: section name header + all items in DFS order with hierarchical number prefix and level-based indentation *(2026-03-05)*
- [x] Page footer: page number via CSS `@bottom-center { content: counter(page) " of " counter(pages); }` *(2026-03-05)*

### Print CSS (inline `<style>` block in `exhibit_pdf.html`)
- [x] `@page` rule: letter size, 1in margins *(2026-03-05)*
- [x] Typography: Arial sans-serif; title 16pt bold, section header 11pt bold, item text 10pt *(2026-03-05)*
- [x] Section formatting: top/bottom borders, `page-break-inside: avoid` *(2026-03-05)*
- [x] No interactive styles — ink-safe black/dark-gray output *(2026-03-05)*

### WeasyPrint Service (`exports/services.py`)
- [x] `generate_exhibit_pdf(exhibit)`: fetches sections → DFS flatten + numbering per section → `render_to_string()` → `weasyprint.HTML(...).write_pdf()` → returns bytes *(2026-03-05)*
- [x] `safe_filename(exhibit)`: builds `ExhibitA_{csi_code}_{trade_name}_{project_name}.pdf` with special chars stripped *(2026-03-05)*

### Download View + URL
- [x] `exhibit_pdf_download(request, pk)` in `exports/views.py`: `@login_required`, company-scoped 404, calls service, sets `Content-Disposition: attachment` *(2026-03-05)*
- [x] URL `exports/exhibit/<int:pk>/pdf/` wired in `exports/urls.py` *(2026-03-05)*

### Editor Integration
- [x] "Export PDF" button added to `editor.html` header alongside "Save as Template" *(2026-03-05)*

### Tests (`exports/tests.py`) — 11 tests, all passing
- [x] `generate_exhibit_pdf()` returns non-empty bytes for flat, nested, and empty-item exhibits *(2026-03-05)*
- [x] `safe_filename()` contains trade info and has no special characters *(2026-03-05)*
- [x] Download view returns HTTP 200, `Content-Type: application/pdf`, `Content-Disposition: attachment` *(2026-03-05)*
- [x] Company isolation: another company's user gets 404 *(2026-03-05)*
- [x] Unauthenticated request redirects to login *(2026-03-05)*
- [x] Multi-section smoke test (5 sections × 4 items) *(2026-03-05)*

---

## Phase 5: Notes & Cross-Trade Tracking (Week 5–6)
**Goal**: Notes appear in all relevant trade contexts. Open question count accurate. Dashboard shows open question count.

> Note model already exists from Phase 1 — building UI only.

### URL & Routing
- [x] Create `notes/urls.py` with `app_name = 'notes'` — all note endpoints *(2026-03-06)*
- [x] Wire `notes/` into `scope_manager/urls.py` *(2026-03-06)*

### Note Creation (HTMX — from scope editor sidebar)
- [x] `NoteForm` (ModelForm): fields — `text`, `note_type`, `primary_trade`, `related_trades` (checkboxes), `source`; all trade fields filtered to project's trades *(2026-03-06)*
- [x] `note_add` view (POST): validates form, saves Note with `project` + `created_by`; returns refreshed `note_list` partial *(2026-03-06)*
- [x] `partials/note_form.html`: compact inline form; related trades in collapsible `<details>`; `hx-post` → `note_add` → swap `#notes-list` *(2026-03-06)*

### Notes Sidebar in Scope Editor
- [x] `note_list` view (GET): cross-trade queryset — `primary_trade = trade OR trade in related_trades`; ordered OPEN first *(2026-03-06)*
- [x] `partials/note_list.html`: wraps add form + note cards; `id="notes-list"` is HTMX swap target; empty state *(2026-03-06)*
- [x] `partials/note_card.html`: type badge color-coded (yellow/blue/gray/green); source, resolution block, inline resolve form in `<details>`, Edit button *(2026-03-06)*
- [x] Editor right panel updated: replaces Phase 5 placeholder; guards against template exhibits (no project) *(2026-03-06)*
- [x] `exhibit_editor` view: passes `notes` (cross-trade Q filter) and `form` (NoteForm) on initial load *(2026-03-06)*

### Note Resolution (HTMX)
- [x] `note_resolve` view (POST): sets `status`, `resolution`, `resolved_by`, `resolved_at`; returns `note_card.html` or empty response when `dismiss=1` (open questions page) *(2026-03-06)*

### Note Edit (HTMX)
- [x] `note_edit` view (GET/POST): GET returns edit form; `?cancel=1` returns card; POST saves and returns updated card *(2026-03-06)*
- [x] `partials/note_edit_form.html`: pre-populated form; related trades auto-checked; Cancel → restore card *(2026-03-06)*

### Project-Level Open Questions View
- [x] `open_questions` view (GET): filters `OPEN_QUESTION + OPEN` for the project; company-scoped 404 *(2026-03-06)*
- [x] `templates/notes/open_questions.html`: yellow-bordered cards with trade info, age, "Open scope →" link, inline resolve form; resolved items collapse out via `dismiss=1` *(2026-03-06)*

### Open Questions Badge on Buyout Dashboard
- [x] `project_dashboard` view: counts `OPEN_QUESTION + OPEN` notes, passes `open_question_count` to template *(2026-03-06)*
- [x] Dashboard header: yellow badge button with count linking to open questions page; hidden when count is zero *(2026-03-06)*

### Tests (`notes/tests.py`) — 20 tests, all passing
- [x] Note creation: M2M related_trades saved, project + created_by set correctly *(2026-03-06)*
- [x] Cross-trade visibility: primary and related trade notes appear; unrelated notes excluded *(2026-03-06)*
- [x] Company isolation: note_list, note_resolve, open_questions all return 404 for wrong company *(2026-03-06)*
- [x] Resolution: fields set correctly, optional text works, dismiss=1 returns empty response *(2026-03-06)*
- [x] Open questions view: filters by type + status correctly *(2026-03-06)*
- [x] Dashboard badge: shows/hides based on count, count matches DB *(2026-03-06)*
- [x] Auth guards: all endpoints redirect unauthenticated users *(2026-03-06)*

---

## Phase 6: AI Scope Assistant (Week 6–7)
**Goal**: Both AI functions work end-to-end. Failures degrade gracefully. PM can complete any exhibit with or without AI.

> `AI_ENABLED` flag and `ANTHROPIC_API_KEY` are already in settings. `ai_services/` app already exists — building the service layer and UI on top.

### AIRequestLog Model
- [x] Add `AIRequestLog` model to `ai_services/models.py` with fields: `request_type` (SCOPE_FROM_DESCRIPTION or SCOPE_ITEM), `exhibit` (FK → ScopeExhibit, nullable), `success` (boolean), `error_message` (text, blank), `tokens_used` (int, nullable), `latency_ms` (int, nullable), `created_at` *(2026-03-08)*
- [x] Register `AIRequestLog` in `ai_services/admin.py` *(2026-03-08)*
- [x] Generate and apply migration *(2026-03-08)*

### AI Service Layer (`ai_services/services.py`)
- [x] Install `anthropic` package (`pip install anthropic`) and verify it's importable *(2026-03-08)*
- [x] Write a shared `_call_claude(system_prompt, user_prompt)` helper: retries once on 5xx errors, returns the text response or raises a clear exception; logs every call to `AIRequestLog` (success/failure, tokens, latency) *(2026-03-08)*
- [x] Write `generate_scope_from_description(exhibit)`: builds user prompt with trade, project type, description, scope description, and existing sections; asks Claude to return structured JSON; returns the parsed dict *(2026-03-08)*
- [x] Write `generate_scope_item(input_text, exhibit, section)`: sends the PM's plain-language note plus trade/section context; asks Claude to rewrite as a single polished exhibit line; returns the standardized text string *(2026-03-08)*
- [x] Write `_parse_json_response(text)`: strips markdown fences, wraps `json.loads()` with try/except; returns `None` on failure *(2026-03-08)*
- [x] Both functions check `settings.AI_ENABLED` first and raise `AIDisabledError` if the flag is off *(2026-03-08)*

### Editor Integration 1 — "Generate Scope" (full exhibit from description)
- [x] Add a "Generate Scope" button to `editor.html` — visible only when `AI_ENABLED` is True and `exhibit.scope_description` is not empty *(2026-03-08)*
- [x] Write `exhibit_generate_scope` view: calls `generate_scope_from_description(exhibit)`; matches sections by name (case-insensitive); bulk-creates `ScopeItem` records with `is_ai_generated=True`; returns refreshed `section_list` partial *(2026-03-08)*
- [x] Show loading spinner on the button while HTMX request is in flight (`hx-indicator`) *(2026-03-08)*
- [x] On AI failure, return section list unchanged with a Django flash message *(2026-03-08)*
- [x] Add URL for this view in `exhibits/urls.py` *(2026-03-08)*

### Editor Integration 2 — Per-Section Item Generation
- [x] Add "Ask AI…" input to each section's footer in `section.html` — visible only when `AI_ENABLED` is True *(2026-03-08)*
- [x] Write `item_generate` view: calls `generate_scope_item()`, creates a `ScopeItem` with `is_ai_generated=True`; falls back to raw input text on AI failure *(2026-03-08)*
- [x] Add URL for this view in `exhibits/urls.py` *(2026-03-08)*

### Feature Flag Guard
- [x] All AI UI elements wrapped in `{% if ai_enabled %}` in `editor.html` and `section.html` *(2026-03-08)*
- [x] `ai_enabled` passed from `exhibit_editor` view context and `_section_list_response` helper *(2026-03-08)*

### Tests (`ai_services/tests.py`) — all with mocked API, no real calls
- [x] `generate_scope_from_description()` returns correctly structured dict when API returns valid JSON *(2026-03-08)*
- [x] `generate_scope_from_description()` returns `None` gracefully when API returns malformed JSON *(2026-03-08)*
- [x] `generate_scope_item()` returns a cleaned string when API responds correctly *(2026-03-08)*
- [x] `_call_claude()` retries once on a simulated 5xx error then succeeds *(2026-03-08)*
- [x] `_call_claude()` logs a failed `AIRequestLog` record when all retries fail *(2026-03-08)*
- [x] `exhibit_generate_scope` view creates `ScopeItem` records with `is_ai_generated=True` *(2026-03-08)*
- [x] `exhibit_generate_scope` view skips unmatched section names *(2026-03-08)*
- [x] `item_generate` view falls back to raw input on AI failure *(2026-03-08)*
- [x] All AI views return 404 for another company's exhibit (company isolation) *(2026-03-08)*
- [x] With `AI_ENABLED=False`, both service functions raise `AIDisabledError` *(2026-03-08)*

---

## Phase 7: Final Review + Hardening + Launch (Weeks 7–8)

### Week 7: Final Review
- [x] Review generation service (`reviews/services.py`): open notes check, cross-trade notes check, checklist items check; re-running replaces previous review atomically *(2026-03-08)*
- [x] Review UI: scorecard badges (✅/⚠️/❌ counts), items grouped by check type, PM response input per item, edit existing response *(2026-03-08)*
- [x] "Run Final Review" button in editor right panel (HTMX POST → review panel partial swap) *(2026-03-08)*
- [x] `review_item_respond` view: saves PM notes per item, GET edit mode *(2026-03-08)*
- [x] 18 tests: all three check types, company isolation, re-run replacement, view auth *(2026-03-08)*

### Week 8: Hardening + Pilot Launch
- [x] Sentry error tracking: `sentry-sdk` installed, configured in settings behind `SENTRY_DSN` env var (no-op if not set) *(2026-03-08)*
- [x] Query performance audit: all key views use `select_related`/`prefetch_related`; N+1 on `section.items` per section is acceptable for MVP (5-10 sections typical) *(2026-03-08)*
- [x] Security audit: all views require `@login_required`; all querysets scoped to `request.user.company`; cross-company 404 enforced and tested; `ProjectType`/`CSITrade` are global lookup tables (no isolation needed) *(2026-03-08)*
- [x] Production readiness: `gunicorn` installed, `Procfile` created (migrate + collectstatic on release), `requirements.txt` generated *(2026-03-08)*
- [ ] Seed production data: company, users, real trade templates, checklist items — do when deploying
- [ ] Pilot launch: 2–3 PMs + PEs onboarded, onboarding guide written — post-deployment

---

## Phase 8: AI Assistant Redesign (Post-MVP)
**Goal**: Upgrade the AI experience from a one-shot "Generate Scope" button to a fully interactive assistant with pending review workflow, contextual quick actions, and a conversational chat overlay.

### Data Model Changes
- [x] `ScopeItem.is_pending_review` (BooleanField, default=False) — migration `exhibits/0002_add_pending_review_to_scope_item.py` *(2026-03-13)*
- [x] `ScopeItem.pending_original_text` (TextField, blank=True) — same migration *(2026-03-13)*
- [x] `Note.scope_item` (FK → ScopeItem, nullable) — migration `notes/0002_add_scope_item_to_note.py` *(2026-03-13)*

### Step 1: Accept/Reject Service Functions
- [x] Write `accept_ai_item(item)` in `exhibits/services.py`: clears `is_pending_review`, clears `pending_original_text`, saves item *(2026-03-13)*
- [x] Write `reject_ai_item(item)` in `exhibits/services.py`: if `pending_original_text` non-empty → restore `text` from it, clear pending fields; if empty → delete item and all descendants *(2026-03-13)*
- [x] Write `accept_all_pending(exhibit)` in `exhibits/services.py`: bulk accept all items with `is_pending_review=True` *(2026-03-13)*
- [x] Write `reject_all_pending(exhibit)` in `exhibits/services.py`: bulk reject all pending items (restore edits, delete new items) *(2026-03-13)*
- [x] Tests for all four service functions in `exhibits/tests.py` — 7 tests, all passing *(2026-03-13)*

### Step 2: Pending Item UI (Editor Display)
- [x] Update `partials/item.html`: detect `is_pending_review` — edit proposals show amber left border + red strikethrough original + green proposed text; new items show green left border + ✨ prefix; both show Accept ✓ / Reject ✗ buttons *(2026-03-13)*
- [x] Write `item_accept_ai` view (POST) in `exhibits/views.py`: calls `accept_ai_item()`, returns item list partial with `HX-Trigger: pendingChanged` *(2026-03-13)*
- [x] Write `item_reject_ai` view (POST) in `exhibits/views.py`: calls `reject_ai_item()`, returns item list partial with `HX-Trigger: pendingChanged` *(2026-03-13)*
- [x] Add URL patterns for `item_accept_ai` and `item_reject_ai` in `exhibits/urls.py` *(2026-03-13)*
- [x] 7 view tests: accept/reject clears state or deletes, HX-Trigger header present, company isolation — all passing *(2026-03-13)*

### Step 3: Pending Banner
- [x] Create `partials/pending_banner.html`: shows "N AI suggestion(s) pending review" with Accept All / Reject All buttons; renders nothing when count is 0 *(2026-03-13)*
- [x] Write `pending_banner` view (GET): queries `is_pending_review=True` count, returns banner partial *(2026-03-13)*
- [x] Write `accept_all_pending_view` (POST): calls service, returns section list + `HX-Trigger: pendingChanged` *(2026-03-13)*
- [x] Write `reject_all_pending_view` (POST): calls service, returns section list + `HX-Trigger: pendingChanged` *(2026-03-13)*
- [x] Banner container in `editor.html` with `hx-trigger="load, pendingChanged from:body"` — self-fetches on load and refreshes after every accept/reject *(2026-03-13)*
- [x] URL patterns for all three views added *(2026-03-13)*
- [x] 7 tests: count correct, empty state, bulk actions, HX-Trigger header, company isolation — all passing *(2026-03-13)*

### Step 4: Update Existing AI to Use Pending Review
- [x] Update `exhibit_generate_scope` view: bulk-created items now have `is_pending_review=True`; response fires `HX-Trigger: pendingChanged`; success message updated to indicate review is needed *(2026-03-13)*
- [x] Update `item_generate` view: AI-generated items now have `is_pending_review=True` and `original_input` stored; fallback (raw input) items remain non-pending; `HX-Trigger: pendingChanged` only fired on AI success *(2026-03-13)*
- [ ] Update `generate_scope_from_description()` service: add completeness check — if exhibit has substantial content, include existing items in prompt context and ask Claude to check for gaps rather than regenerate everything

### Step 5: New AI Service Functions
- [x] Add `REWRITE_ITEM`, `EXPAND_ITEM`, `CHAT` choices to `AIRequestLog.RequestType`; migration `ai_services/0002_add_request_type_choices.py` *(2026-03-13)*
- [x] Add `REWRITE_ITEM_SYSTEM_PROMPT`, `EXPAND_ITEM_SYSTEM_PROMPT`, `CHAT_SYSTEM_PROMPT` to `ai_services/prompts.py` *(2026-03-13)*
- [x] Extended `_call_claude()` to accept `messages=` list for multi-turn chat (backward-compatible) *(2026-03-13)*
- [x] Write `rewrite_scope_item(item, exhibit, instruction='')`: returns proposed new text string or None *(2026-03-13)*
- [x] Write `expand_scope_item(item, exhibit)`: returns list of `{"text": "...", "level": N}` dicts or None *(2026-03-13)*
- [x] Write `chat_with_exhibit(exhibit, conversation_history)`: injects live exhibit context into system prompt; returns `{"message": "...", "proposed_changes": [...]}` or None *(2026-03-13)*
- [x] 16 tests across all three functions: success, malformed JSON, AI disabled, request type logged, instruction/history passed correctly — all passing *(2026-03-13)*

### Step 6: Rewrite & Expand Item Actions
- [x] Add ✨ icon to `item.html` hover controls (alongside ↑↓→← and trash) *(2026-03-13)*
- [x] Clicking ✨ icon opens a small inline popover: "Rewrite…" (instruction textarea + Submit) and "Expand into sub-items" *(2026-03-13)*
- [x] `toggleAIPanel` JS in `editor.html`: closes others, opens target, closes on outside click *(2026-03-13)*
- [x] Write `item_rewrite` view (POST) in `exhibits/views.py`: calls `rewrite_scope_item()`; sets pending fields; returns diff item partial + `HX-Trigger: pendingChanged` *(2026-03-13)*
- [x] Write `item_expand` view (POST) in `exhibits/views.py`: calls `expand_scope_item()`; creates child items with pending review; returns section item list + `HX-Trigger: pendingChanged` *(2026-03-13)*
- [x] URL patterns for `item_rewrite` and `item_expand` added *(2026-03-13)*
- [x] 10 view tests: pending fields correct, HX-Trigger header, no-op on AI failure, company isolation, POST-only — all passing *(2026-03-13)*

### Step 7: AI Right Pane Tab
- [x] Add "AI ✨" as third tab in `editor.html` right panel (alongside Notes and Final Review); only shown when `ai_enabled` *(2026-03-13)*
- [x] Create `partials/ai_panel.html` with three states: item context (`?item_pk`), completeness results, and default *(2026-03-13)*
  - Default: "Check Exhibit Completeness" button + open OPEN_QUESTION notes with section picker for conversion + per-section scroll links
  - Item context: rewrite form + expand button (both targeting editor elements via HTMX)
  - Completeness results: gap list with "Add to [section]" buttons; green "looks complete" state; error state
- [x] `ai_panel` view (GET) with optional `?item_pk` param; `_ai_panel_context()` helper *(2026-03-13)*
- [x] `exhibit_check_completeness` view (POST): calls `check_exhibit_completeness()` service; returns panel in suggestions state *(2026-03-13)*
- [x] `note_to_scope_item` view (POST): calls `generate_scope_item()`, creates pending ScopeItem, links note to item *(2026-03-13)*
- [x] `add_gap_item` view (POST): creates pending ScopeItem from suggestion text *(2026-03-13)*
- [x] `check_exhibit_completeness()` service function + `COMPLETENESS_SYSTEM_PROMPT`; `AIRequestLog.RequestType.COMPLETENESS_CHECK` *(2026-03-13)*
- [x] JS: `EXHIBIT_AI_PANEL_URL` global; `switchTab('ai')` triggers htmx.ajax to load panel; `updateAIPanel(itemPk)` called from ✨ button if AI tab is active *(2026-03-13)*
- [x] `id="section-ai-input-{{ section.pk }}"` on Ask AI input in `section.html` for scroll-to links *(2026-03-13)*
- [x] 28 new tests across service + 4 view classes: company isolation, AI failure handling, pending fields, note linking — all passing *(2026-03-13)*

### Step 8: Full-Screen Chat Overlay
- [x] "Chat with AI ✨" button in `editor.html` header (only when `ai_enabled`); opens overlay via `openChatOverlay()` *(2026-03-13)*
- [x] `ai_chat_overlay.html`: fixed full-screen overlay (z-50); greeting message; scrollable chat history; textarea input with Enter-to-send; loading spinner on Send button *(2026-03-13)*
- [x] `partials/ai_chat_messages.html`: two-bubble partial (user + assistant) returned by `ai_chat_send`; carries `data-history` attribute for JS to read updated history *(2026-03-13)*
- [x] `ai_chat` view (GET): returns overlay template *(2026-03-13)*
- [x] `ai_chat_send` view (POST): receives message + history JSON; builds full conversation; calls `chat_with_exhibit()`; applies proposed changes via `_apply_proposed_changes()`; returns message pair partial *(2026-03-13)*
- [x] `_apply_proposed_changes()` helper: handles `add` (pending ScopeItem), `edit` (pending diff), `delete` (immediate) *(2026-03-13)*
- [x] Conversation history managed client-side: `window.chatHistory` array; `htmx:configRequest` injects it before each POST; `htmx:afterSwap` reads updated history from `data-history` attribute *(2026-03-13)*
- [x] `section_list` GET view + URL (`<int:pk>/sections/`): refreshes section list after chat overlay closes *(2026-03-13)*
- [x] JS: `openChatOverlay()` (loads overlay once via HTMX, re-shows if already loaded); `closeChatOverlay()` (hides overlay, refreshes section list) *(2026-03-13)*
- [x] Split-screen chat panel: aside expands to 45vw; `openChatPanel()` / `closeChatPanel()`; `chat_side_panel.html` with quick-actions (collapsible, includes `ai_panel.html`) + chat messages + input; AI tab removed; `updateAIPanel()` removed *(2026-03-15)*
- [x] Context chip picker in chat input: `+` button opens picker with sections + open notes; chips render as dismissible pills (blue=section, amber=note); selected context injected as `[Context: ...]` prefix in `ai_chat_send`; Open Questions + Sections removed from `ai_panel.html`; 3 new tests *(2026-03-15)*
- [x] `HX-Trigger: pendingChanged` fired when changes are applied; section list refreshed on overlay close *(2026-03-13)*
- [x] 14 tests: overlay load, send with add/edit changes, history threading, AI failure, empty message, company isolation — all passing *(2026-03-13)*

### Step 9: Tests
- [x] Accept/reject item view tests (accept clears pending, reject restores/deletes, company isolation) — 7 tests *(2026-03-13)*
- [x] Bulk accept/reject tests (all pending items affected, banner count correct) — covered in pending banner suite *(2026-03-13)*
- [x] Pending banner view tests (count correct, clears after bulk actions, company isolation) — 7 tests *(2026-03-13)*
- [x] `item_rewrite` view tests (pending fields set correctly, mocked Claude, no-op on failure, company isolation) — 5 tests *(2026-03-13)*
- [x] `item_expand` view tests (child items created as pending, parent FK correct, mocked Claude) — 5 tests *(2026-03-13)*
- [x] `ai_chat_send` view tests (add/edit/delete changes, history threading, AI failure, company isolation) — 10 tests *(2026-03-13)*
