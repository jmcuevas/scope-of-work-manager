# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered scope of work manager for construction general contractors. PMs use it to create Exhibit A scope documents for subcontractor bidding. Replaces the Word-template-hunting workflow.

Full product specification: `docs/specs.md`. This is the authoritative reference for all feature decisions, data models, workflows, and MVP scope. **Only read the relevant section when needed — do not read the full file.**

| Topic | specs.md Section |
|-------|-----------------|
| Workflows & user stories | `## Detailed Workflow / User Stories` |
| Data models (full detail) | `## Technical Architecture / System Design` |
| AI service functions | `### AI Service Layer` |
| HTMX interaction patterns | `### HTMX Interaction Patterns` |
| MVP scope boundaries | `### MVP Workflow Summary` |
| Post-MVP deferred features | `### Post-MVP Architecture Notes` |

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
| `ai_services` | Claude API integration — two functions: scope description → exhibit language, natural language → inclusion/exclusion item |
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
Two functions in `ai_services/` (not yet implemented):
1. `generate_scope_from_description()` — project/trade description → structured exhibit sections + items
2. `generate_scope_item()` — natural language input → single standardized inclusion/exclusion

AI is behind the `AI_ENABLED` setting. Every exhibit workflow must work without AI. Generated items are stored as regular `ScopeItem` records with `is_ai_generated=True`. No prompt text is stored — only token/cost/error metrics in `AIRequestLog`.

## Development Progress

Track completed and pending work in `docs/checklist.md`. Check this at the start of each session to know where we left off.

### Branch Strategy
- `main` — stable, deployable
- `develop` — active development; merge to `main` at end of each phase

### MVP Phases
1. Foundation + data models ✅
2. Project dashboard + trade import
3. Scope exhibit editor (Weeks 3–4, ~40% of total effort)
4. PDF export (closes core value loop)
5. Notes & cross-trade tracking
6. AI scope assistant
7. Final review + hardening + pilot launch
