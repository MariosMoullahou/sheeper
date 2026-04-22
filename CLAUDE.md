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

## Farm Isolation Rules (MUST follow for every new feature)
Every feature must enforce multi-farm data isolation. When adding new models, serializers, views, or API endpoints:

1. **Models** — every new data model must have a `farm` FK, or reach farm through a FK chain (e.g. `Milk → Sheep → Farm`)
2. **Querysets** — all ORM queries in views must filter by the active farm (`get_active_farm(request)`). Never return data from other farms.
3. **Serializers** — any `SlugRelatedField` or FK field must scope its queryset to the active farm via `__init__` + `self.context.get('farm')`. This prevents cross-farm lookups and information leakage.
4. **Views** — always pass `context={'farm': farm}` when instantiating serializers for write operations (POST/PUT). For read-only (GET), filter the queryset before serializing.
5. **Validation** — add explicit `validate_<field>` methods for FK fields that reference farm-scoped models, checking `obj.farm_id != farm.pk`.

## Coding Conventions

### Backend
- Use function-based views with `@api_view` — do NOT use DRF viewsets or class-based views
- Every page view must have `@login_required(login_url='login')` + `@role_required(ROLE_FARMER, ROLE_MANAGER)`
- Every API view must have `@login_required(login_url='login')` + `@api_view([...])` + `@api_role_required(ROLE_FARMER, ROLE_MANAGER)`
- API error responses use `{"field_name": "error message"}` format
- Use `get_object_or_404` with farm filter for detail views (e.g. `get_object_or_404(Sheep, pk=pk, farm=farm)`)
- Male sheep (rams) cannot have milk measurements — enforced in `MilkSerializer.validate_sheep`

### Frontend
- Vanilla JS only — no React, Vue, or any frontend framework
- Tabulator for all data tables — no other table libraries
- Bootstrap 5 for layout and components
- Use the green theme CSS variables (`--green-50` through `--green-900`) for custom styling
- Inline editing in Tabulator tables uses the `inlineEdit` helper function pattern with `cellEdited` event
- API calls use `fetch` with `X-CSRFToken` header from the cookie

### Page Structure — Table + Modal Form (standard for all CRUD pages)
Any new feature that lists records and lets users create new ones must follow this layout. Do NOT put the form side-by-side with the table, and do NOT use a Bootstrap collapse (it pushes the table down).

1. **Title row sits OUTSIDE the table card** — a flex row with the page title (`<h4>` in `color: var(--green-800)`) on the left and action buttons on the right. The "New ..." button uses `btn btn-success btn-sm` with `data-bs-toggle="modal" data-bs-target="#form-modal"`. Do not wrap the title in a `card-header` — the table card has no header.
2. **Table card** is just `<div class="card shadow-sm"><div class="card-body p-0"><div id="..."></div></div></div>` — a plain rounded white box containing the Tabulator. No header strip, no `card-header`.
3. **Form sits in a Bootstrap modal** with `id="form-modal"`. Use `modal-dialog-centered`; add `modal-dialog-scrollable` for longer forms. The modal header keeps the green gradient (`linear-gradient(135deg, var(--green-600), var(--green-700))`) with a white close button (`btn-close btn-close-white`).
4. **After a successful POST**, JS must close the modal:
   ```js
   bootstrap.Modal.getOrCreateInstance(document.getElementById('form-modal')).hide();
   ```
5. Reference implementations: `templates/sheep_form.html`, `templates/milking.html`, `templates/lamping.html`, `templates/health.html`. Use one as a starting point when building new CRUD pages.
6. Exception: pages whose primary UI is not a table (e.g. `bulk_milking.html` grid, `calendar.html`, `genealogy.html`) do not follow this pattern.

### API Design
- Use `SlugRelatedField(slug_field='earing')` for sheep references — never expose numeric PKs to the frontend for sheep
- POST endpoints return `201 Created` with the created object
- PUT endpoints return `200 OK` with the updated object
- DELETE endpoints return `204 No Content`
- All list endpoints return flat JSON arrays (no pagination wrapper yet)

## Testing Rules
- Always test farm isolation on new endpoints — verify that a user from Farm A cannot read/write data belonging to Farm B
- Test that role decorators block unauthorized roles
- Test validation rules (e.g. male sheep can't have milk, mother must be female)

## Pending / Known Issues
- Farm icon needs changing to something more farm-like (currently building icon)
- Milk Analysis sidebar link points to placeholder
- Father field on Sheep model (deferred — add when family tree is built)
- Tests need to be written
- Lamping page old Django form view (`views.lamping`) still has dead POST handling code — API handles everything now
