# Copilot Instructions - AFIP Electronic Invoice System

## Project Overview
Python desktop application for generating and managing electronic invoices (facturas electrónicas) through Argentina's AFIP (tax authority) web services. Built with PyQt5, Peewee ORM, and integrates with the PyAfipWs library for AFIP API communication.

## Architecture

### Core Components
- **Controllers** (`controladores/`): Business logic and AFIP WS integration
  - `Main.py`: Main workflow controller - processes invoices, generates CAE/CAEA, sends emails
  - `FE.py`: WSFEv1 wrapper for domestic electronic invoices
  - `FCE.py`: WsFECred wrapper for electronic credit invoices (FCE)
  - `EnvioEmailsPendientes.py`: Async email queue processor with retry logic
  - `ImpresionComprobantes.py`: QThread-based PDF generation
  
- **Models** (`modelos/`): Database entities using Peewee ORM
  - All models inherit from `ModeloBase` which configures MySQL/SQLite database
  - `Encabezado`: Invoice header (main record)
  - `IVA`, `Tributo`, `CbteRel`: Invoice details and relationships
  - `EmailsPendientes`: Email queue with CC/BCC support and error tracking

- **Views** (`vistas/`): PyQt5 UI components
  - Follow naming pattern: `{Feature}View` with corresponding `{Feature}Controller`

- **PyAfipWs** (`pyafipws/`): External library for AFIP web service communication
  - Don't modify directly - it's a third-party library
  - See `pyafipws/README.md` for documentation

### Data Flow
1. `Main.GeneraFE()` runs continuous loop processing invoices
2. For each pending invoice in `Encabezado` where `listo=0`:
   - Authenticates with AFIP using digital certificates (WSAA)
   - Creates invoice structure via `FE.CreaFE()`
   - Sends to AFIP for authorization (CAE)
   - Generates PDF invoice with QR code
   - Enqueues email via `encolar_email()`
3. Background thread processes `EmailsPendientes` queue with retry logic

## Configuration & Environment

### Key Files
- **`sistema.ini`**: Main configuration (DB, AFIP endpoints, certificates)
  - Sections: `[param]`, `[WSFEv1]`, `[WSAA]`, `[FACTURA]`
  - Database password is encrypted using Fernet (see `libs/Utiles.py::desencriptar`)
  - `homo = S` switches between homologation/production AFIP endpoints

- **`.env`**: SMTP credentials for email sending (dotenv format)

# Copilot Instructions — AFIP Electronic Invoice System

Purpose: concise guidance for AI coding agents to work productively in this repo.

Big picture
- Desktop PyQt5 app that issues electronic invoices via AFIP web services.
- Core domains: invoice processing (controladores/Main.py), AFIP WS adapters (`controladores/FE.py`, `FCE.py`), background email queue (`controladores/EnvioEmailsPendientes.py`), and models (`modelos/`).

Key files to inspect
- `controladores/Main.py` — main loop, `GeneraFE()` orchestrates CAE/CAEA flow.
- `controladores/FE.py` — WSFEv1 client wrappers and `Autenticar()` usage.
- `modelos/Encabezado.py` and `modelos/EmailsPendientes.py` — invoice and email queue shape.
- `libs/Utiles.py` — `desencriptar()` (Fernet) and helpers like `FechaMysql()`.
- `sistema.ini` — environment switches (`homo = S`), DB selection (`base`), and WSAA sections.
- `certificados/` — digital certs required for WSAA; TA files are `wsfe-*-ta.xml`.

Developer workflows
- Run locally: use the project Python env and run `main.py` (Windows recommended).
- Build exe: run `.
compila.bat` which uses PyInstaller and `version.txt`.
- Tests: manual test runner `test_nuevas_funcionalidades.py` (no automated test framework).
- Migrations: add scripts under `migrations/` and run them manually (see existing patterns).

Project-specific conventions
- ORM: use Peewee models via `modelos/ModeloBase.py` — do not run raw SQL.
- Error handling: public controller methods use `@inicializar_y_capturar_excepciones` (check `controladores/ControladorBase.py`).
- Dates: use `FechaMysql(date_obj)` for AFIP (YYYYMMDD).
- Boolean compat: `BitBooleanField` abstracts MySQL bit(1) vs SQLite boolean.

Integration & important patterns
- AFIP auth: WSAA tickets cached as `{service}-{empresa}-ta.xml` (auto-renew). Use `FE.Autenticar()` or `WsFECred.Autenticar()`.
- Avoid editing `pyafipws/` unless implementing a critical bugfix; treat it as bundled third-party code.
- Email sending: always enqueue via `controladores.EnvioEmailsPendientes.encolar_email(...)`; background processor reads `modelos/EmailsPendientes`.
- Debugging AFIP: set `grabaxml = True` in controllers to persist request/response XML; inspect `wsfev1.Resultado` and `ErrMsg`.

Concise code examples
- Enqueue email:
```python
from controladores.EnvioEmailsPendientes import encolar_email
encolar_email(destinatario='c@x.com', asunto='Factura #1', cuerpo_html='<b>OK</b>', adjunto_ruta='pdf/1.pdf')
```
- Format AFIP date:
```python
from libs.Utiles import FechaMysql
FechaMysql(date_obj)
```

Editing guidance
- If adding DB fields: update `modelos/` then add a script in `migrations/` mirroring existing migrations.
- When changing AFIP flows, update TA naming and `sistema.ini` service sections; test in homologation by setting `homo = S`.

Where to be careful
- Concurrency: `EmailsPendientes.procesando_desde` avoids races — preserve this when modifying queue logic.
- Certificates: missing/invalid files in `certificados/` cause WSAA auth failures.

If anything is unclear or you want more detail (examples, tests, or expanded walk-through), tell me which area to expand.
