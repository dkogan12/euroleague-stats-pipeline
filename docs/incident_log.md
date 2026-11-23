# Incident log

## 2026-11-23 - Fire drill (planned)
- What: Injected a duplicate player row and a -5 point score into season 2026 data.
- Caught by: duplicates (critical), valid_ranges (warning), points_reconcile (warning).
- Result: Pipeline stopped before saving. Email alert received via SNS.
- Follow-up: None needed. Normal run afterward passed all 5 checks.
