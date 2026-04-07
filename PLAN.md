# Overhang — App Plan

## What is Overhang?

A multi-tenant 3D printing business management tool. Each business (organization) runs in complete isolation — separate data, separate file storage — on a shared server. It manages the catalog of printable entities, tracks filament inventory and costs, calculates margins, sends print jobs directly to connected Bambu Lab printers, and generates Vinted listings.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Frontend | Django templates + HTMX + Alpine.js |
| Database | PostgreSQL 16 |
| CSS | Tailwind CSS (via CDN) |
| File storage | Local filesystem via Django `MEDIA_ROOT` (Docker volume) |
| Containerization | Docker Compose |
| Web server | Gunicorn + Nginx (serves media files) |

No Celery/Redis in MVP — all operations are synchronous.

---

## Project Structure

```
overhang/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/       # Users, Organizations, membership
│   ├── catalog/        # Print entities, photos, 3D files
│   ├── inventory/      # Filament spools
│   ├── pricing/        # Cost engine, margin dashboard
│   ├── printers/       # Bambu Lab printer registry + print jobs
│   ├── vinted/         # Listing template generator
│   └── core/           # Shared utilities, base templates, dashboard
├── templates/
├── static/
├── media/              # Uploaded files (Docker volume)
│   └── <org_slug>/     # Per-organization isolation
│       ├── entities/
│       └── models/
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── requirements.txt
└── .env.example
```

---

## Multi-Tenancy Model

### How it works

- Every business is an **Organization**
- Users sign up and are either **invited** to an org or create their own
- All data models (entities, spools, listings) carry an `organization` FK
- All queries are automatically scoped to the user's current org
- File uploads go to `media/<org_slug>/...` — no cross-org file access

### Roles (per organization)

| Role | Permissions |
|---|---|
| `owner` | Full access, manage members, delete org |
| `member` | Full access to org data, cannot manage members |

### URL structure

All app URLs are namespaced under the active organization. The user's current org is stored in the session (useful if multi-org membership is added later).

---

## Data Models

### `accounts` — `Organization`

| Field | Type | Notes |
|---|---|---|
| name | CharField | |
| slug | SlugField | used in file paths and URLs |
| owner | ForeignKey → User | |
| created_at | DateTimeField | |

### `accounts` — `Membership`

| Field | Type | Notes |
|---|---|---|
| user | ForeignKey → User | |
| organization | ForeignKey → Organization | |
| role | CharField | owner, member |
| joined_at | DateTimeField | |

### `catalog` — `PrintEntity`

| Field | Type | Notes |
|---|---|---|
| organization | ForeignKey → Organization | tenant scope |
| title | CharField | |
| slug | SlugField | unique per org |
| description | TextField | |
| category | CharField | miniature, functional, decorative, cosplay, other |
| tags | ManyToMany → Tag | |
| estimated_weight_g | DecimalField | grams of filament used |
| estimated_print_hours | DecimalField | |
| support_required | BooleanField | |
| material_type | CharField | PLA, PETG, TPU, ABS, ASA, other |
| preferred_color | ForeignKey → FilamentSpool | nullable |
| is_active | BooleanField | controls Vinted listing eligibility |
| is_favorite | BooleanField | |
| created_at / updated_at | DateTimeField | |

### `catalog` — `EntityPhoto`

| Field | Type | Notes |
|---|---|---|
| entity | ForeignKey → PrintEntity | |
| image | ImageField | `media/<org_slug>/entities/<slug>/` |
| is_primary | BooleanField | |
| order | PositiveIntegerField | drag-and-drop order |

### `catalog` — `EntityFile`

| Field | Type | Notes |
|---|---|---|
| entity | ForeignKey → PrintEntity | |
| file | FileField | `media/<org_slug>/models/<slug>/` |
| file_type | CharField | stl, 3mf, obj |
| label | CharField | e.g. "Main body", "Support-free version" |

### `inventory` — `FilamentSpool`

| Field | Type | Notes |
|---|---|---|
| organization | ForeignKey → Organization | tenant scope |
| brand | CharField | |
| material | CharField | PLA, PETG, TPU, ABS, ASA, other |
| color_name | CharField | e.g. "Galaxy Black" |
| color_hex | CharField | e.g. "#1a1a2e" |
| initial_weight_g | DecimalField | default 1000 |
| current_weight_g | DecimalField | updated after each print |
| price_paid | DecimalField | full spool price in € |
| restock_threshold_g | DecimalField | alert when below this, default 150 |
| purchased_at | DateField | |
| notes | TextField | |

**Computed properties:**
- `is_empty`: `current_weight_g <= 0`
- `cost_per_gram`: `price_paid / initial_weight_g`

### `pricing` — `PrintCost`

| Field | Type | Notes |
|---|---|---|
| entity | OneToOneField → PrintEntity | |
| filament_cost_override | DecimalField | nullable — auto-calc from spool if null |
| electricity_kwh_rate | DecimalField | default from global settings |
| printer_wattage | DecimalField | default 200W |
| time_overhead_minutes | DecimalField | setup, post-processing time |
| failure_rate_percent | DecimalField | default 10% |
| packaging_cost | DecimalField | default €0.50 |
| selling_price | DecimalField | |

**Computed properties:**
- `filament_cost` = `estimated_weight_g × spool.cost_per_gram`
- `electricity_cost` = `(estimated_print_hours × wattage / 1000) × kwh_rate`
- `base_cost` = filament + electricity + packaging + time overhead
- `total_cost` = `base_cost × (1 + failure_rate / 100)`
- `profit` = `selling_price − total_cost`
- `margin_percent` = `(profit / selling_price) × 100`
- `cost_ratio` = `selling_price / total_cost`

### `printers` — `Printer`

| Field | Type | Notes |
|---|---|---|
| organization | ForeignKey → Organization | tenant scope |
| name | CharField | e.g. "Bambu P1S - Workshop" |
| printer_type | CharField | bambu (only supported for now) |
| ip_address | GenericIPAddressField | local network IP |
| serial_number | CharField | from printer screen |
| access_code | CharField | from printer screen (stored encrypted) |
| is_online | BooleanField | updated via MQTT heartbeat |
| created_at | DateTimeField | |

**Bambu connectivity:**
- File transfer: FTPS to `<ip>:990` — uploads the 3MF from `EntityFile`
- Status/commands: MQTT to `<ip>:8883` (TLS) — start job, monitor progress
- Library: `bambu-connect` (community Python package)
- Credentials needed: IP, serial number, access code

### `printers` — `PrintJob`

| Field | Type | Notes |
|---|---|---|
| organization | ForeignKey → Organization | tenant scope |
| entity | ForeignKey → PrintEntity | what is being printed |
| printer | ForeignKey → Printer | target printer |
| entity_file | ForeignKey → EntityFile | the 3MF file to send |
| filament_spool | ForeignKey → FilamentSpool | which spool to deduct from |
| status | CharField | queued, uploading, printing, done, failed, cancelled |
| started_at | DateTimeField | nullable |
| finished_at | DateTimeField | nullable |
| actual_weight_g | DecimalField | nullable — filled on completion for accurate cost tracking |
| notes | TextField | |
| created_at | DateTimeField | |

**Job flow:**
1. User selects entity + printer + 3MF file + spool → creates `PrintJob` (status: queued)
2. App uploads 3MF via FTPS to printer
3. App sends start command via MQTT (status: printing)
4. MQTT messages update status in real time via HTMX polling
5. On completion: user confirms actual filament used → spool weight deducted

---

### `vinted` — `VintedListing`

| Field | Type | Notes |
|---|---|---|
| entity | ForeignKey → PrintEntity | |
| title | CharField | editable, pre-filled from entity |
| description | TextField | editable, generated from template |
| price | DecimalField | synced from PrintCost.selling_price |
| condition | CharField | always "new" |
| category_vinted | CharField | Vinted category string |
| generated_at | DateTimeField | |
| posted_at | DateTimeField | nullable, set manually |
| sold_at | DateTimeField | nullable |
| status | CharField | draft, posted, sold |
| vinted_url | URLField | nullable, pasted after posting |
| notes | TextField | |

---

## Pages & Views

### Auth
- `/login/` — Django's built-in auth
- `/logout/`
- `/register/` — create account + organization in one step
- All other views require login (`LoginRequiredMixin`)

### Dashboard `/`
- Cards: total entities, active listings, low-stock spools, portfolio value
- Low-stock spool alerts
- Quick links: add entity, generate listings
- Scoped to current user's organization

### Entity Catalog `/catalog/`
- Photo grid with title, cost ratio badge, status
- Filter by category, material, favorite, active
- HTMX inline: favorite toggle, active toggle

### Entity Detail `/catalog/<slug>/`
- Photo gallery
- Specs panel
- Cost breakdown (HTMX live recalculation)
- Filament availability indicator
- Vinted listing preview

### Entity Add/Edit `/catalog/add/` and `/catalog/<slug>/edit/`
- Multi-step form: info → photos → files → pricing
- Photo reordering (Sortable.js + HTMX)

### Filament Inventory `/inventory/`
- Table with color swatches, weight progress bars
- Red highlight for spools below threshold
- HTMX inline weight deduction (quick-log after a print)

### Cost Dashboard `/pricing/`
- Table: entity | cost | price | margin% | ratio
- Color-coded: green (ratio > 3x), yellow (2–3x), red (< 2x)
- Global defaults panel (electricity rate, wattage, failure rate)

### Vinted Listing Generator `/vinted/`
- List of active entities → Generate listing
- Copyable title + description + price
- Download photo zip bundle
- Mark as posted (paste Vinted URL)
- Mark as sold

### Printers `/printers/`
- List of registered printers with online/offline status
- Add printer (name, IP, serial, access code)
- Per-printer: active job status, job history

### Print Jobs `/printers/jobs/`
- Queue view: pending and active jobs
- Start a job: select entity → select 3MF file → select printer → select spool
- Live status updates via HTMX polling (MQTT → Django → page)
- Completed jobs: confirm actual filament used → auto-deducts from spool

### Organization Settings `/settings/`
- Edit org name
- View members, remove members (owner only)
- Invite new members by username

---

## Deployment

### Infrastructure

| Component | Details |
|---|---|
| Host | Home server running CasaOS |
| Exposure | Cloudflare Tunnel — no open router ports |
| SSL | Cloudflare terminates SSL — no Certbot needed |
| Domain | Subdomain e.g. `overhang.yourdomain.com` |
| Import | `docker-compose.yml` imported directly into CasaOS |

### Traffic flow

```
Browser → Cloudflare (SSL) → Tunnel → homeserver:8080 → nginx → gunicorn:8000 → Django
```

Nginx only handles internal proxying — no SSL config needed since Cloudflare handles it.

### Cloudflare Tunnel setup

1. In Cloudflare Zero Trust dashboard: create a tunnel, point it at `http://localhost:8080`
2. Add a public hostname: `overhang.yourdomain.com` → the tunnel
3. Done — traffic arrives at port 8080 on the homeserver

### Docker Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file: .env
    restart: unless-stopped

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - media_files:/app/media
    depends_on:
      - db
    env_file: .env
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - media_files:/media
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  media_files:
```

### Deploying an update

```bash
git pull
docker compose build web
docker compose up -d
```

### Django settings for Cloudflare

```python
# production.py
ALLOWED_HOSTS = ["overhang.yourdomain.com"]
CSRF_TRUSTED_ORIGINS = ["https://overhang.yourdomain.com"]

# Trust Cloudflare's forwarded headers
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

---

## Implementation Roadmap

Dependencies flow top to bottom — each phase relies on the ones above it being complete.

---

### Phase 1 — Project Scaffold
*Everything else is built on top of this.*

- [ ] Create Django project with `config/settings/` split (base / development / production)
- [ ] Add `requirements.txt` (Django, DRF, psycopg2, Pillow, python-dotenv)
- [ ] Write `Dockerfile` and `docker-compose.yml` (web + db + nginx)
- [ ] Write `nginx.conf` (proxy to gunicorn, serve `/media/`)
- [ ] Write `.env.example`
- [ ] Create `templates/base.html` with nav, Tailwind CDN, HTMX CDN
- [ ] Verify: `docker compose up` serves a blank Django page

---

### Phase 2 — Accounts (Auth + Multi-tenancy)
*Every other model scopes to Organization — this must exist first.*

- [ ] Create `accounts` app
- [ ] `Organization` model (name, slug, owner FK, created_at)
- [ ] `Membership` model (user, organization, role, joined_at)
- [ ] Registration view — creates User + Organization in one step
- [ ] Login / logout views (Django built-in auth)
- [ ] `LoginRequiredMixin` applied globally — unauthenticated users redirected to login
- [ ] Organization middleware — attaches current org to every request
- [ ] Organization settings page — edit name, view/remove members
- [ ] Verify: register → login → see empty dashboard scoped to org

---

### Phase 3 — Catalog
*Core data. Inventory (spool FK), Pricing (OneToOne), Printers (entity FK), and Vinted all depend on this.*

- [ ] Create `catalog` app
- [ ] `Tag` model
- [ ] `PrintEntity` model (all fields, org-scoped)
- [ ] `EntityPhoto` model + image upload to `media/<org_slug>/entities/<slug>/`
- [ ] `EntityFile` model + file upload to `media/<org_slug>/models/<slug>/` (STL, 3MF, OBJ)
- [ ] Entity list view (grid, filter by category / material / favorite / active)
- [ ] Entity detail view (photo gallery, specs)
- [ ] Entity add / edit forms
- [ ] HTMX inline: favorite toggle, active toggle
- [ ] Primary photo selection + photo reorder (Sortable.js)
- [ ] Verify: add entity with photos and a 3MF → files appear at correct org-scoped paths

---

### Phase 4 — Filament Inventory
*Required before Pricing (cost_per_gram) and before Print Jobs (spool deduction).*

- [ ] Create `inventory` app
- [ ] `FilamentSpool` model (org-scoped, all fields)
- [ ] Computed properties: `is_empty`, `cost_per_gram`
- [ ] Spool list view (color swatches, weight progress bars, low-stock highlights)
- [ ] Add / edit spool form
- [ ] HTMX inline weight deduction form (quick-log after a print)
- [ ] Low-stock flag visible on spool list and dashboard
- [ ] Verify: add spool → deduct weight → low-stock alert appears when below threshold

---

### Phase 5 — Pricing / Cost Engine
*Depends on Catalog (entity) and Inventory (spool cost_per_gram).*

- [ ] Create `pricing` app
- [ ] `PrintCost` model (OneToOne with PrintEntity)
- [ ] All computed properties as Python `@property` methods (filament_cost, electricity_cost, total_cost, margin_percent, cost_ratio)
- [ ] Global defaults stored in org-level settings (kWh rate, wattage, failure rate)
- [ ] Cost breakdown panel on entity detail page
- [ ] HTMX live recalculation when pricing inputs change
- [ ] Cost dashboard `/pricing/` — sortable table, color-coded ratio rows
- [ ] Verify: change spool price → cost_per_gram updates → entity cost recalculates automatically

---

### Phase 6 — Printers + Print Jobs
*Depends on Catalog (entity + EntityFile) and Inventory (FilamentSpool for deduction).*

- [ ] Create `printers` app
- [ ] `Printer` model (org-scoped, IP, serial, access code stored encrypted)
- [ ] `PrintJob` model (entity, printer, EntityFile, spool, status, timestamps)
- [ ] Printer list view with online/offline status
- [ ] Add printer form
- [ ] Bambu connectivity: test connection (ping MQTT on save)
- [ ] Print job creation: select entity → select 3MF → select printer → select spool
- [ ] FTPS upload of 3MF to Bambu printer (`bambu-connect`)
- [ ] MQTT start-print command
- [ ] Job status polling via HTMX (MQTT → Django view → page updates)
- [ ] Job completion: confirm actual filament used → spool weight auto-deducted
- [ ] Print job history per printer and per entity
- [ ] Verify: upload 3MF to printer → job starts → status updates → spool deducted on completion

---

### Phase 7 — Vinted Listing Generator
*Depends on Catalog (entity + photos) and Pricing (selling_price).*

- [ ] Create `vinted` app
- [ ] `VintedListing` model
- [ ] Description template engine (pulls entity title, description, material, price)
- [ ] Listing generator view — pre-filled, editable title + description + price
- [ ] One-click copy for title and description (Alpine.js clipboard)
- [ ] Photo zip bundler (Python `zipfile` stdlib — packages entity photos for download)
- [ ] Status flow: draft → posted (paste Vinted URL) → sold (record date)
- [ ] Listings overview `/vinted/` — filterable by status
- [ ] Verify: generate listing → copy description → download zip → mark as posted → mark as sold

---

### Phase 8 — Dashboard + Polish
*Pulls data from all apps — built last.*

- [ ] Summary cards: total entities, active listings, low-stock spools, total portfolio value
- [ ] Low-stock spool alerts on dashboard
- [ ] Recent print jobs widget
- [ ] Active Vinted listings count
- [ ] Mobile-responsive layout pass
- [ ] Verify: all cards reflect real data from each app

---

## Future Roadmap

- **OctoPrint integration** — REST API for live print job data (other printer brands)
- **Vinted automation** — Playwright-based posting (separate Docker service)
- **MinIO migration** — Drop-in S3 backend if local storage becomes limiting
- **Multi-color prints** — Multiple spools per entity with per-spool weight breakdown
- **Restock shopping list** — Auto-generate buy list from all spools below threshold
- **Multi-org membership** — One user belonging to multiple organizations with org switcher
