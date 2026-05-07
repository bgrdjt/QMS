# QMS Development Quick Start

This guide shows you how to work on QMS in Codespaces with a smooth, hot-reload dev loop comparable to modern web development.

## Your Dev Environment

```
Web Dev               QMS Equivalent
─────────             ──────────────
npm run dev       →   make dev
localhost:3000    →   localhost:5151
Browser UI        →   JSON API + Thunder Client / curl
React DevTools    →   make commands
package.json      →   Makefile
npm test          →   make test-all
```

## First-Time Setup

```bash
# 1. Install dependencies
make setup

# 2. Create test QMS folder with sample data
make env
```

This creates `TEST_QMS/` with:
- 7 sample documents (2 EFFECTIVE, 1 IN_REVIEW, 3 DRAFT, 1 INFORMAL)
- 3 team members with role history
- 8 audit log events
- 2 projects (PRJ-001, PRJ-002)
- Full folder structure

## Daily Dev Loop

### Start the Server

```bash
make dev
```

The server runs with **auto-reload enabled** — every time you save a Python file, it restarts automatically. Just like `npm run dev` hot reload.

Codespaces automatically forwards port 5151. Click the notification to open it in your browser.

### Test While You Work

Open a second terminal and use these commands:

```bash
# Quick checks
make ping           # {"status":"ok","version":"1.4"}
make stats          # Document counts, CR counts, review queue
make docs           # All documents in JSON
make roster         # Team members

# Pretty output
make register       # Tabular document list
make logs           # Audit trail

# Run tests
make test-new-doc       # Create a document, see it in register
make test-lifecycle     # Full Draft→Review→Approve cycle
make test-all           # All tests
```

### Make Changes

1. Edit any Python file in `server/` or `_SCRIPTS/`
2. Save
3. Server restarts automatically
4. Run `make test-all` or your custom test command
5. See results instantly

### Commit When It Works

```bash
git add .
git commit -m "Fixed roster role history endpoint"
git push
```

## Common Tasks

### Reset Test Data

```bash
make reset      # Wipes TEST_QMS and recreates from scratch
```

### Clean Python Cache

```bash
make clean      # Remove __pycache__, *.pyc files
```

### Start Fresh

```bash
make reset
make dev
```

## API Testing Tools

### In the Browser
Click the port 5151 forwarding notification → opens `http://localhost:5151/ping`

### Thunder Client (VS Code Extension)
1. Install Thunder Client extension
2. Create a new request
3. Set URL: `http://localhost:5151/documents`
4. Send

### curl (Terminal)
```bash
curl http://localhost:5151/ping | python -m json.tool
curl http://localhost:5151/documents | python -m json.tool
curl -X POST http://localhost:5151/documents/new \
  -H "Content-Type: application/json" \
  -d '{"doc_type":"SOP","title":"Test","owner":"Dev User"}'
```

## File Structure

```
QMS/
├── server/
│   ├── dms_server.py         ← Main Flask app (auto-reloads)
│   ├── routing_engine.py     ← Review/approval routing
│   ├── cr_engine.py           ← Change request engine
│   └── dms_config.json        ← Points to TEST_QMS (gitignored)
├── _SCRIPTS/
│   └── dms.py                 ← CLI tool
├── ribbon/                    ← VBA + XML for Word/Excel
├── docs/                      ← User guides (.docx)
├── installer/                 ← Windows installer (.bat)
├── legacy/                    ← qms_app.py (desktop GUI, reference only)
├── TEST_QMS/                  ← Test environment (gitignored)
│   ├── _REGISTER/
│   │   ├── document_register.csv
│   │   ├── team_roster.json
│   │   ├── audit_log.json
│   │   └── ...
│   ├── 01_QUALITY_MANUAL/
│   ├── 02_SOPs/
│   └── ...
├── setup_test_env.py          ← Creates TEST_QMS
├── Makefile                   ← Your "package.json scripts"
├── requirements.txt           ← Python dependencies
└── README.md                  ← Full architecture documentation
```

## What's Different from Web Dev

1. **No visual UI in Codespaces** — you're building the backend only. The desktop app (`qms_app.py`) is the UI layer and runs locally on Windows.

2. **JSON responses, not HTML** — when you open port 5151 in the browser, you see JSON. That's correct. Use Thunder Client or curl for structured testing.

3. **Documents live in TEST_QMS/** — the "database" is CSV/JSON files in a folder structure. Real deployments point to a network drive or cloud sync folder.

4. **Makefile, not package.json** — same concept, different syntax. `make dev` = `npm run dev`.

## Example Workflow

```bash
# Terminal 1 — server with auto-reload
make dev

# Terminal 2 — testing
make stats
# Edit server/dms_server.py — add a new route
# Save → server restarts automatically
make stats         # Test new route
make test-all      # Run full test suite
git commit -am "Added new stats endpoint"
```

## Troubleshooting

### Server won't start
```bash
make reset      # Recreate test environment
make dev
```

### Port 5151 is blocked
```bash
pkill -f dms_server    # Kill any old process
make dev
```

### Test data is corrupted
```bash
make reset      # Fresh start
```

### Python import errors
```bash
make setup      # Reinstall dependencies
```

## Next Steps

- Add a new API endpoint in `server/dms_server.py`
- Test it with `curl` or Thunder Client
- Add a test command to `Makefile`
- Commit and push

You now have a smooth, hot-reload dev loop for building QMS features. Welcome to backend dev in Codespaces!
