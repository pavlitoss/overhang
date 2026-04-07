# Overhang — App Plan

## What is Overhang?

A business management tool for a solo 3D printing operation. It manages the catalog of printable entities, tracks filament inventory and costs, calculates margins, and generates Vinted listings — enabling rapid, well-formed ad posting and a clear view of profitability.

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
│   ├── catalog/        # Print entities, photos, 3D files
│   ├── inventory/      # Filament spools
│   ├── pricing/        # Cost engine, margin dashboard
│   ├── vinted/         # Listing template generator
│   └── core/           # Shared utilities, base templates, dashboard
├── templates/
├── static/
├── media/              # Uploaded files (Docker volume)
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── requirements.txt
└── .env.example
```

---

## Data Models

### `catalog` — `PrintEntity`

| Field | Type | Notes |
|---|---|---|
| title | CharField | |
| slug | SlugField | auto-generated |
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
| views_count | PositiveIntegerField | |
| created_at / updated_at | DateTimeField | |

### `catalog` — `EntityPhoto`

| Field | Type | Notes |
|---|---|---|
| entity | ForeignKey → PrintEntity | |
| image | ImageField | `media/entities/<slug>/` |
| is_primary | BooleanField | |
| order | PositiveIntegerField | drag-and-drop order |

### `catalog` — `EntityFile`

| Field | Type | Notes |
|---|---|---|
| entity | ForeignKey → PrintEntity | |
| file | FileField | `media/models/<slug>/` |
| file_type | CharField | stl, 3mf, obj |
| label | CharField | e.g. "Main body", "Support-free version" |

### `inventory` — `FilamentSpool`

| Field | Type | Notes |
|---|---|---|
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

### Dashboard `/`
- Cards: total entities, active listings, low-stock spools, portfolio value
- Low-stock spool alerts
- Quick links: add entity, generate listings

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

---

## Docker Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file: .env

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - media_files:/app/media
    depends_on:
      - db
    env_file: .env

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - media_files:/media
    depends_on:
      - web

volumes:
  postgres_data:
  media_files:
```

---

## Build Order

| Phase | Work |
|---|---|
| 1 | Project scaffold: settings split, Docker, Nginx, base template |
| 2 | Catalog app: entities, photos, files, CRUD |
| 3 | Inventory app: spools, weight deduction, low-stock alerts |
| 4 | Pricing app: cost engine, ratio dashboard, live HTMX recalc |
| 5 | Vinted app: listing generator, photo zip, status flow |
| 6 | Dashboard, polish, mobile layout |

---

## Future Roadmap

- **OctoPrint integration** — REST API for live print job data and real filament usage
- **Bambu Lab integration** — Local MQTT interface
- **Vinted automation** — Playwright-based posting (separate Docker service)
- **MinIO migration** — Drop-in S3 backend if local storage becomes limiting
- **Multi-color prints** — Multiple spools per entity with per-spool weight breakdown
- **Restock shopping list** — Auto-generate buy list from all spools below threshold
