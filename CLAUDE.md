# Sheeper - Farm Management System for Sheep

## Project Overview
Django app for managing sheep farms — tracking sheep, milking, birth events (lamping), and calendar events. Multi-farm architecture with role-based access.

## Tech Stack
- **Backend:** Django + Django REST Framework
- **Database:** PostgreSQL
- **Frontend:** Bootstrap 5 + Tabulator (vanilla JS, no frameworks)
- **Theme:** Custom green CSS variables (`--green-50` through `--green-900`)
- **Future:** Chart.js for dashboards, D3.js for genealogy tree, html5-qrcode for ear tag scanning, PWA for offline/camera

## Architecture

### Multi-Farm
- Every data model has a `farm` FK (Sheep, CalendarEvent) or reaches farm through a FK (Milk → Sheep → Farm, BirthEvent → mother → Farm)
- `unique_together = ['farm', 'earing']` on Sheep — earing tags are unique per farm, not globally
- Active farm stored in `request.session['active_farm_id']`
- Users can belong to multiple farms (M2M: `Farm.members`)

### Roles (Global, not per-farm)
- **farmer** — CRUD on own farm's data only
- **analyst** — read-only milk analysis (future feature)
- **manager** — access to all farms, full CRUD
- **superuser** — manager + Django admin
- Enforced via `@role_required()` (page views) and `@api_role_required()` (DRF views) decorators in `accounts/helpers.py`

### Models (`sheepfold/models.py`)
- **Sheep** — `id` (BigAutoField PK), `farm` (FK), `earing` (CharField), `birthdate`, `gender` (M/F), `mother` (self FK, `related_name='children'`), `is_active`
- **BirthEvent** — `mother` (FK to Sheep), `date`, `notes`, `lambs` (M2M to Sheep). Validates mother is female.
- **Milk** — `sheep` (FK), `date`, `milk` (decimal, liters), `is_active`
- **CalendarEvent** — `farm` (FK), `title`, `start`, `end`, `group_id`, `color`
- **Farm** (`accounts/models.py`) — `name`, `members` (M2M to User)
- **Profile** (`accounts/models.py`) — `user` (OneToOne), `role` (farmer/analyst/manager)

### API Pattern
- All API serializers use `SlugRelatedField(slug_field='earing')` for sheep references — accepts earing tags, not numeric IDs
- BirthEvent POST accepts `new_lambs` (list of `{earing, gender}`) to create lambs inline — sets mother, birthdate, farm automatically (family tree ready)
- All API views validate that referenced sheep belong to the active farm

## Key Design Decisions
- **Earing is NOT the PK** — `BigAutoField` is PK, earing is a CharField with `unique_together` on farm. This supports multi-farm and future changes.
- **No frontend framework** — vanilla JS was chosen over Vue/React for simplicity. Tabulator handles tables.
- **Family tree ready** — Sheep has `mother` FK with `related_name='children'`. Father field deferred for now. D3.js planned for genealogy visualization.
- **PWA over native app** — browser camera access via html5-qrcode + PWA for offline, no app store needed.

## Apps
- `sheepfold/` — core app (sheep, milk, births, calendar)
- `accounts/` — auth, farms, profiles, role helpers

## URLs
- Pages: `/` (homepage), `/new/` (create sheep), `/lamping/`, `/milking/`, `/calendar/`, `/<pk>/` (sheep detail)
- APIs: `/api/sheep/`, `/api/milk/`, `/api/birthevent/`, `/api/calendar/` (GET/POST), plus `/<pk>/` for DELETE

## Templates
- `base.html` — green theme, Bootstrap 5, offcanvas sidebar, Tabulator + Luxon CDN
- `sidebar.html` — role-based nav links, farm card, user badge
- Page templates: `homepage.html`, `sheep_form.html`, `milking.html`, `lamping.html`, `calendar.html`, `sheep_detail.html`
- Auth templates: `login.html`, `select_farm.html`

## Running
```bash
.\venv\Scripts\python.exe manage.py runserver
.\venv\Scripts\python.exe manage.py migrate
```

## Pending / Known Issues
- Farm icon needs changing to something more farm-like (currently building icon)
- Milk Analysis sidebar link points to placeholder
- Father field on Sheep model (deferred — add when family tree is built)
- Tests need to be written
- Lamping page old Django form view (`views.lamping`) still has dead POST handling code — API handles everything now
