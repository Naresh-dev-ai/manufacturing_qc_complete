# Manufacturing Production & Quality Control API — Complete learning baseline

This project provides a broad working baseline:
- JWT login and role-based access control
- Plants, production lines, products
- Raw materials and inventory movements
- Bills of materials (BOM) and material requirement calculations
- Production orders: create, start, complete, cancel
- Quality inspection records with validation
- Dashboard, production, inventory, and quality reports
- PostgreSQL, Alembic configuration, pytest, Docker Compose

This is a learning baseline, not a certified or production-hardened ERP. Review the notes at the end before real factory use.

## 1. Choose a setup method

### Option A: Local Python + local PostgreSQL
Install Python 3.11+ and PostgreSQL. Create a database named `manufacturing_qc`.
Copy `.env.example` to `.env`, then set the URL using your own PostgreSQL credentials:
`DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/manufacturing_qc`

Windows PowerShell:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```
If PowerShell blocks activation, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

macOS/Linux:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Run:
```bash
uvicorn app.main:app --reload
```

### Option B: Docker Compose
Install Docker Desktop, open a terminal in the project directory, and run:
```bash
docker compose up --build
```
This uses a local-only development password in `docker-compose.yml`. Never use those credentials in a deployed environment. Swagger is at `http://127.0.0.1:8000/docs`.

## 2. Initial administrator

At first startup, if the users table is empty, the app creates:
- username `admin`
- password `ChangeMe123!`

Change these settings in `.env` before first startup if desired. Change the JWT secret. These sample credentials are for local learning only.

## 3. Swagger login

Open `http://127.0.0.1:8000/docs`.
Use `POST /api/v1/auth/login`, click **Try it out**, and submit username/password as form fields (not JSON). Copy `access_token`, click **Authorize**, and paste the token. Swagger's OAuth2 flow may add the `Bearer` prefix automatically.

Expected shape:
```json
{"access_token": "<your-token>", "token_type": "bearer"}
```

## 4. Endpoints overview

- `GET /health`
- `POST /api/v1/auth/login`, `POST /api/v1/auth/users`, `GET /api/v1/auth/me`
- `GET/POST /api/v1/plants`
- `GET/POST /api/v1/production-lines`
- `GET/POST /api/v1/products`
- `GET/POST /api/v1/materials`
- `POST /api/v1/materials/{id}/stock-in`
- `POST /api/v1/materials/{id}/stock-out`
- `POST /api/v1/materials/{id}/adjustment`
- `GET /api/v1/materials/{id}/movements`
- `POST /api/v1/products/{id}/bom`
- `GET /api/v1/products/{id}/bom`
- `GET /api/v1/products/{id}/material-requirements?quantity=10`
- `POST /api/v1/production-orders`
- `POST /api/v1/production-orders/{id}/start`
- `POST /api/v1/production-orders/{id}/complete`
- `POST /api/v1/production-orders/{id}/cancel`
- `POST /api/v1/quality-inspections`
- `GET /api/v1/quality-inspections`
- `GET /api/v1/reports/dashboard`
- `GET /api/v1/reports/inventory-movements`
- `GET /api/v1/reports/production`
- `GET /api/v1/reports/quality`

## 5. Suggested end-to-end test flow

IDs in these examples assume a new empty database. Always use the actual IDs returned by your API.

### A. Create plant
`POST /api/v1/plants`
```json
{"code":"PLANT-001","name":"Hyderabad Manufacturing Plant","address":"Hyderabad, Telangana"}
```
Expected `201 Created`.

### B. Create production line
`POST /api/v1/production-lines`
```json
{"code":"LINE-001","name":"Assembly Line 1","plant_id":1,"description":"Main assembly line"}
```
Expected `201 Created`.

### C. Create product
`POST /api/v1/products`
```json
{"code":"PROD-001","name":"Industrial Pump","description":"Standard industrial pump","unit":"piece"}
```

### D. Create material
`POST /api/v1/materials`
```json
{"code":"STEEL-001","name":"Mild Steel","category":"Metal","unit":"kg","minimum_stock_level":20,"reorder_level":40,"supplier_reference":"SUP-1001"}
```

### E. Receive material
`POST /api/v1/materials/1/stock-in`
```json
{"quantity":100,"reference":"GRN-0001","remarks":"Initial steel delivery"}
```
Expected movement quantity `100.0`, balance `100.0`.

### F. Add BOM item
`POST /api/v1/products/1/bom`
```json
{"material_id":1,"quantity_per_product":2.5,"scrap_percent":5}
```
Meaning: each pump uses 2.5 kg steel, plus a 5% scrap allowance.

### G. Calculate requirements for 10 pumps
`GET /api/v1/products/1/material-requirements?quantity=10`
Expected calculation: `2.5 × 10 × 1.05 = 26.25 kg`. The response reports required quantity, available quantity, and whether stock is sufficient.

### H. Create production order
`POST /api/v1/production-orders`
```json
{"order_number":"WO-0001","product_id":1,"production_line_id":1,"planned_quantity":10,"notes":"First test production run"}
```
Expected status is `draft`.

### I. Start production
`POST /api/v1/production-orders/1/start`
No request body is needed. It checks the BOM, checks stock, and issues all required materials in one database transaction. With the example BOM it issues 26.25 kg, leaving 73.75 kg from the original 100 kg. The order becomes `in_progress`. If stock is insufficient, the transaction rolls back.

### J. Complete production
`POST /api/v1/production-orders/1/complete`
```json
{"produced_quantity":10}
```
Expected status becomes `completed` and `produced_quantity` is `10`.

### K. Record a quality inspection
First create a user with the quality inspector role via `POST /api/v1/auth/users` while logged in as admin:
```json
{"username":"quality1","full_name":"Quality Inspector","password":"QualityPass123!","role":"quality_inspector"}
```
Log in as `quality1`, authorize with that token, then submit `POST /api/v1/quality-inspections`:
```json
{"inspection_number":"QI-0001","production_order_id":1,"quantity_inspected":10,"quantity_passed":9,"quantity_failed":1,"decision":"fail","notes":"One unit failed the pressure test"}
```
Expected `201 Created`. Passed plus failed must equal inspected. A completed production order is required.

### L. Reports
Use `GET /api/v1/reports/dashboard`, `/api/v1/reports/production`, and `/api/v1/reports/quality`. The report responses are calculated from saved database rows, so values depend on your test records.

## 6. Expected status codes

- `200`: successful read or update
- `201`: created
- `401`: missing, invalid, or expired token
- `403`: authenticated but role not permitted
- `404`: record not found
- `409`: duplicate code, wrong workflow status, or insufficient stock
- `422`: request validation failed

## 7. Role outline

- `super_admin`: can create users and perform administrative operations
- `plant_manager`: create plants, lines, and production orders
- `production_manager`: create products/lines, operate production, and perform stock movements
- `production_supervisor`: perform stock movements and operate production
- `store_manager`: create materials, adjust stock, and receive/issue stock
- `quality_inspector`: record and read quality inspections
- `worker`: read-only access in this starter

## 8. Tests

Run:
```bash
pytest -q
```
The included test checks the health endpoint. Additional integration tests should use an isolated test database and test auth, stock rollback, BOM calculations, production transitions, and quality validation.

## 9. Alembic migrations

Alembic configuration is included. For a migration-managed database, avoid treating `create_all()` as your schema migration system. A safe next step is to disable startup table creation, generate a baseline migration against a fresh database, inspect it, then apply it with `alembic upgrade head`. Do not blindly autogenerate against a database already initialized by `create_all()` without checking the result.

## 10. Important limitations before real factory use

- Quantities are floats for learning convenience. Use `Decimal` and PostgreSQL `NUMERIC` for accurate fractional units, plus explicit units of measure.
- Production start consumes planned BOM quantities immediately. This starter does not model partial material issue, returns, scrap capture, lot/batch traceability, or reservation workflows.
- Completing an order records output quantity but does not add finished goods to inventory yet.
- Quality inspections are records; failed units are not automatically quarantined.
- Reports are simple summaries, not optimized analytics.
- Add robust tests, audit trails, backups, monitoring, rate limits, HTTPS, secret management, and migration discipline before production deployment.
