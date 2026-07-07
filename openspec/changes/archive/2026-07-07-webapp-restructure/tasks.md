# Tasks: Webapp Restructure

## 1. Run history (backend)

- [x] 1.1 `webapp/backend/services/run_history.py`: record create/update, log path, merged listing (live + persisted; stale `running` → failed), stored-log read, prune-to-200
- [x] 1.2 `routers/jobs.py`: `_start_job` gains kind/label/paths/folder_name + runs_dir, tees logs to the run's file, writes the record at start/finish; wire every launch endpoint; `GET /api/jobs` returns the merged history; add `GET /api/jobs/{id}/log`
- [x] 1.3 Backend tests: record lifecycle, merged listing, interrupted-run reporting, log retrieval, prune

## 2. Frontend IA

- [x] 2.1 `App.tsx`: nav = Applications / Contacts / Queue / Profiles; Prompts into AccountMenu; hash fallbacks (`#dashboard`, `#static` → applications)
- [x] 2.2 `ApplicationsPage`: unified two-source table (QUEUED + built), state column + filter chips, GENERATED→BUILT display, insight chip + status select + sort carried over, Add-JD panel + Build-all, failed-run chip from `/api/jobs`
- [x] 2.3 `RowActions` dropdown component (Build/Delete for queued; Re-build/ATS/Notes/Drive + disabled Apply for built)
- [x] 2.4 `QueuePage` rewrite: scheduled section + run history with expandable stored logs, polling while running
- [x] 2.5 `ContactsPage`: queued profile inputs (Enrich/Enrich-all) + completed contacts table
- [x] 2.6 `ProfilesPage`: registry header (list/active/switch) above the absorbed Static Content editors; remove `DashboardPage`/`StaticContentPage`
- [x] 2.7 UI renames (Build/Re-build/BUILT) with breadcrumb comments; types updated

## 3. E2E + verification

- [x] 3.1 Update e2e suites: navigation, applications (ex-dashboard), queue (runs view), profiles (ex-static-content)
- [x] 3.2 Full pytest green; frontend build + lint clean
