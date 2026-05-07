# QMS DMS Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-05-07

### Added - Repository Organization & Development Environment

#### Repository Structure
- **Organized file layout** following Claude's architecture specification:
  - `server/` — Flask REST API, routing engine, CR engine
  - `_SCRIPTS/` — CLI controller for document operations
  - `ribbon/` — Word and Excel VBA modules with customUI XML
  - `docs/` — User guides and reference documentation
  - `installer/` — Windows installation batch script
  - `legacy/` — Desktop app preserved for reference
- **Created missing core modules**:
  - `server/cr_engine.py` — Change Request lifecycle management engine
  - `_SCRIPTS/dms.py` — Command-line interface for API operations

#### Development Environment
- **Auto-reload Flask server** — Hot reload on file save (`debug=True`, `use_reloader=True`)
- **Test environment setup** (`setup_test_env.py`):
  - Creates `TEST_QMS/` folder with complete QMS structure
  - Seeds 7 sample documents across all lifecycle states
  - Populates 3 team members with role history
  - Generates 8 audit log events
  - Configures 2 sample projects (PRJ-001, PRJ-002)
  - Pre-configures `server/dms_config.json` pointing to test data

#### Development Tools
- **Makefile** with 15+ commands for rapid development:
  - `make setup` — Install Python and npm dependencies
  - `make env` — Create test environment with sample data
  - `make dev` — Start server with auto-reload
  - `make ping` / `make stats` / `make docs` / `make roster` — API testing
  - `make register` — Pretty-print document register
  - `make test-new-doc` — Create test document
  - `make test-lifecycle` — Run Draft→Review→Approve cycle
  - `make test-all` — Full test suite
  - `make reset` — Wipe and recreate test environment
  - `make clean` — Remove Python cache files

#### Documentation
- **DEV_GUIDE.md** — Complete quick-start guide for daily development
- **README.md** — Existing comprehensive architecture documentation (preserved)
- **CHANGELOG.md** — Version history and change tracking (this file)

#### Configuration Files
- `.devcontainer/devcontainer.json` — Codespaces Python 3.12 environment
- `.gitignore` — Excludes config secrets, test data, and client documents
- `requirements.txt` — Python dependencies (Flask, CORS, PDF generation)

### Changed

#### Server Configuration
- Updated `server/dms_server.py`:
  - Changed `host` from `127.0.0.1` to `0.0.0.0` for Codespaces port forwarding
  - Enabled `debug=True` for detailed error messages
  - Enabled `use_reloader=True` for automatic restart on file changes

### Fixed

#### File Organization
- Corrected widespread filename/content mismatches in uploaded files:
  - Recovered Word ribbon VBA from misnamed `.py` file → `ribbon/QMS_WordRibbon_v1_4_COMPLETE.bas`
  - Recovered Excel ribbon VBA from misnamed `.py` file → `ribbon/QMS_ExcelRibbon.bas`
  - Recovered customUI XML files from misnamed extensions → `ribbon/customUI14_fixed.xml` and `ribbon/customUI_excel.xml`
  - Recovered installer batch script from misnamed `.xml` file → `installer/install_v1_3c.bat`
  - Recovered documentation from misnamed binaries → `docs/QMS_DMS_User_Guide_v1_3.docx` and `docs/QMS_Document_Control_Reference_Guide.docx`
  - Consolidated server sources to canonical v1.4 versions

### Technical Details

#### Architecture
- **Backend**: Flask REST API on port 5151
- **Data Storage**: CSV/JSON files in QMS Root folder structure
- **Standards Compliance**: ISO 13485:2016, ISO 9001:2015, ISO 14971:2019, FDA QMSR
- **Deployment Model**: Client-isolated QMS Root folders (network/cloud)

#### API Endpoints (localhost:5151)
- Core: `/ping`, `/config`, `/documents`, `/documents/<id>/promote`
- Change Requests: `/cr`, `/cr/<id>`, `/cr/new`, `/cr/<id>/approve`, `/cr/<id>/make-effective`
- Routing: `/routing/queue`, `/routing/submit-review`, `/routing/complete-review`
- Team: `/roster`, `/roster/add`, `/roster/<id>/role-history`
- Stats: `/stats`, `/audit-log`, `/review-due`

#### Development Workflow
1. `make env` — One-time test environment setup
2. `make dev` — Start server with auto-reload (Terminal 1)
3. `make test-all` — Run tests while developing (Terminal 2)
4. Edit Python files → Server auto-restarts
5. `git commit` → Push when features work

#### Test Environment Data
- **Documents**:
  - QM-001 (EFFECTIVE) — Quality Manual
  - SOP-001 (EFFECTIVE) — Document Control Procedure
  - SOP-002 (DRAFT) — Incoming Inspection
  - SOP-003 (IN_REVIEW) — Risk Management Process
  - PRJ-001-DC-001 (DRAFT) — Design Requirements Specification
  - FS-001 (APPROVED, INFORMAL) — Feasibility Study
  - CR-0001 (DRAFT) — CR Form for SOP-001 Rev2
- **Team Members**:
  - QA Lead (Approver, Management Rep) — qa.lead@acmemedical.com
  - Tech Reviewer (Technical Reviewer, Design Engineer) — tech@acmemedical.com
  - Dev User (Developer, Document Author) — dev@acmemedical.com

### Migration Notes

#### For Existing Deployments
- No changes to existing client QMS Root folders required
- Server configuration file (`dms_config.json`) format unchanged
- All API endpoints remain backward compatible
- Desktop app (`qms_app.py`) unchanged (preserved in `legacy/`)

#### For New Codespaces Instances
1. Clone repository
2. Run `make setup` to install dependencies
3. Run `make env` to create test environment
4. Run `make dev` to start server
5. Test with `make test-all`

### Repository Statistics
- **Python modules**: 3 (dms_server, routing_engine, cr_engine)
- **VBA modules**: 2 (Word ribbon, Excel ribbon)
- **XML ribbon definitions**: 2
- **Documentation files**: 3 (.docx user guides + DEV_GUIDE.md)
- **Test environment**: 7 documents, 3 team members, 2 projects
- **Makefile commands**: 15+ development shortcuts

---

## Version History

### [1.4.0] - 2026-05-07
Repository organization, development environment setup, auto-reload server, test data framework, Makefile tooling, comprehensive documentation.

### [1.3.0] - Prior Release
Original functionality: Flask server, routing engine, Word/Excel ribbons, desktop GUI, installer. Architecture defined in README.md.

---

**For detailed architecture and API documentation**, see [README.md](README.md)  
**For daily development workflow**, see [DEV_GUIDE.md](DEV_GUIDE.md)
