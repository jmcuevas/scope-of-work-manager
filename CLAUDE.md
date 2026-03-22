# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered scope of work manager for construction general contractors. PMs use it to create Exhibit A scope documents for subcontractor bidding. Replaces the Word-template-hunting workflow.

Full product specification: `docs/specs.md`. This is the authoritative reference for all feature decisions, data models, workflows, and MVP scope. **Only read the relevant section when needed — do not read the full file.**

| Topic | specs.md Section |
|-------|-----------------|
| Workflows & user stories | `## Detailed Workflow / User Stories` |
| Data models (full detail) | `## Technical Architecture / System Design` |
| AI service functions & chat infrastructure | `### AI Service Layer` |
| AI UX entry points | `### AI Assistant UX` |
| HTMX interaction patterns | `### HTMX Interaction Patterns` |
| MVP scope boundaries | `### MVP Workflow Summary` |
| Post-MVP deferred features | `### Post-MVP Architecture Notes` |
| All pending work (deployment, AI, app features) | `## Pending Implementation` |

## Commands

All commands use the local virtual environment. Either activate it first (`source .venv/bin/activate`) or prefix with `.venv/bin/python`.

```bash
# Run development server (requires DB env vars)
DB_USER=$(whoami) DB_PASSWORD="" .venv/bin/python manage.py runserver

# Migrations
.venv/bin/python manage.py makemigrations
DB_USER=$(whoami) DB_PASSWORD="" .venv/bin/python manage.py migrate

# Django system check
.venv/bin/python manage.py check

# Run all tests
DB_USER=$(whoami) DB_PASSWORD="" .venv/bin/pytest

# Run a single test file
DB_USER=$(whoami) DB_PASSWORD="" .venv/bin/pytest core/tests.py

# Run a single test
DB_USER=$(whoami) DB_PASSWORD="" .venv/bin/pytest core/tests.py::TestClassName::test_method_name

# Create superuser
DB_USER=$(whoami) DB_PASSWORD="" .venv/bin/python manage.py createsuperuser
```

**Note**: No `.env` file is set up locally. DB credentials are passed inline as shown above (`DB_USER=$(whoami) DB_PASSWORD=""`). For production, use a `.env` file following `.env.example`.

## Architecture

### Tech Stack
- **Django 5.2** + **PostgreSQL** — server-rendered monolith, no separate frontend
- **HTMX** — dynamic UI (toggles, AI responses, form submissions) without a JS framework
- **Tailwind CSS** — utility-first styling via CDN in MVP
- **Claude API (Sonnet)** — AI scope language generation (`ai_services/`)
- **WeasyPrint** — HTML Django templates → PDF export (`exports/`)
- **django-allauth** — email-based auth; self-registration is disabled, admin creates accounts

### App Structure

| App | Responsibility |
|-----|---------------|
| `core` | Company, User (custom, email-based), ProjectType, CSITrade lookup tables |
| `projects` | Project and Trade models; buyout dashboard |
| `exhibits` | ScopeExhibit, ExhibitSection, ScopeItem; the scope editor |
| `notes` | Cross-trade note tracking with resolution workflow |
| `reviews` | ChecklistItem, FinalReview, FinalReviewItem; final review checklist |
| `ai_services` | Claude API integration — scope generation, item rewrite/expand, section AI, note-to-scope conversion, completeness check, conversational chat with tool use |
| `exports` | WeasyPrint PDF generation |

### Key Data Relationships

```
Company → User (role: PM | PE | SUPERINTENDENT | ADMIN)
Company → Project → Trade (FK: CSITrade, status workflow)
Company → ScopeExhibit (is_template=True for library; project=null for global templates)
Project → ScopeExhibit (via csi_trade; one per project+trade pair)
ScopeExhibit → ExhibitSection (ordered) → ScopeItem (hierarchical: parent FK + level + order)
Project → Note (primary_trade FK + related_trades M2M for cross-trade visibility)
ScopeExhibit → FinalReview → FinalReviewItem (informational only in MVP, does not block export)
```

### Multi-Tenancy
Every view and queryset must be scoped to `request.user.company`. Cross-company data exposure is a P0 bug. Apply company filters at the queryset/service layer by default.

### Scope Editor Complexity
The `ScopeItem` model uses `parent` (self-FK), `level`, and `order` fields for hierarchical numbering (1, 1.1, 1.1.1). The trickiest logic in the app:
- **Clone service**: deep-copies a ScopeExhibit with correct parent FK remapping
- **Reorder/indent/outdent**: moves subtrees as a unit; cascades level changes to all descendants
- Centralize all reorder logic in a service layer with transactional updates

### AI Service Layer
All AI functions live in `ai_services/services.py`, gated by the `AI_ENABLED` setting. Every workflow must work without AI.

**Service functions:**
1. `generate_scope_from_description(exhibit)` — project/trade description → structured exhibit sections + items (gap-fill mode when ≥5 items exist)
2. `generate_scope_item(input_text, exhibit, section)` — natural language → single polished scope item
3. `rewrite_scope_item(item, exhibit, instruction)` — rewrite a single item with optional instruction
4. `expand_scope_item(item, exhibit)` — expand one item into sub-items
5. `section_ai_action(section, exhibit, instruction)` — unified section-level AI: uses tool-based API (add/edit/delete tools) to decide actions from a free-form instruction
6. `rewrite_section_items(section, exhibit, instruction)` — bulk rewrite all items in a section
7. `convert_note_to_scope(note, exhibit, instruction)` — convert a note to scope item with overlap detection
8. `check_exhibit_completeness(exhibit)` — identify gaps in scope coverage
9. `chat_with_exhibit(exhibit, messages)` — conversational AI with Claude tool use (add/edit/delete/convert_note tools)

**Architecture pattern — "one AI brain, multiple entry points":**
- Chat overlay is the full-flexibility interface with all tools available
- AI icons throughout the UI (sections, items, notes) are pre-scoped shortcuts into the same service layer
- Each icon opens a popover/inline form with a text input for quick instructions
- All AI-generated items use `is_pending_review=True` for accept/reject workflow
- Token/cost/error metrics logged to `AIRequestLog` (no prompt text stored)

**Chat infrastructure:**
- Server-side history: `ChatSession` + `ChatMessage` models (persist across page reloads)
- Structured context: `_build_structured_chat_context()` → JSON with item PKs, refs, hierarchy, notes
- Claude tool use API: `_call_claude_with_tools()` with `CHAT_TOOLS` (add/edit/delete/convert_note)
- `_apply_proposed_changes()` in views handles all tool-generated changes uniformly

## Development Progress

Track completed and pending work in `docs/checklist.md`. Check this at the start of each session to know where we left off.

### Branch Strategy
- `main` — stable, deployable
- `develop` — active development; merge to `main` at end of each phase

### Versioning
Follows [Semantic Versioning](https://semver.org/) (`vMAJOR.MINOR.PATCH`):
- **MAJOR** — breaking changes or major rewrites
- **MINOR** — new features or enhancements
- **PATCH** — bug fixes

Tag `main` after each merge: `git tag -a vX.Y.Z -m "description"`. Push tags with `git push --tags`.

| Tag | Milestone |
|-----|-----------|
| `v1.0.0` | MVP complete (pre-deployment) |
| `v1.1.0` | Railway deployment config + production settings |

### Deployment
- **Platform:** Railway (Docker-based)
- **URL:** https://buyouthd.up.railway.app
- **Auto-deploy:** push to `main` triggers build + migrate + restart
- **Config files:** `Dockerfile`, `railway.toml`, `.dockerignore`
- **Env vars:** managed in Railway dashboard (Variables tab)

### Development Phases
1. Foundation + data models ✅
2. Project dashboard + trade import ✅
3. Scope exhibit editor ✅
4. PDF export ✅
5. Notes & cross-trade tracking ✅
6. AI scope assistant ✅
7. Final review + hardening ✅
8. AI assistant redesign — pending review workflow, per-item rewrite/expand, chat overlay with tool use ✅
9. AI architecture upgrade — server-side chat history, structured context, section letter numbering, Claude tool use API ✅
   - Step 5: New AI capabilities — unified section AI action, note-to-scope conversion with overlap detection, chat batch note conversion ✅

**Remaining:** seed production data, pilot launch onboarding (deployment only)
