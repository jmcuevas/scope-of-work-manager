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
