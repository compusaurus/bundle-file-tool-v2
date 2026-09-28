# TEAM — bundle_file_tool build 198 (FINAL)

Baseline-gated install of the purge guards. NEW files placed; the 3 existing files replaced only when the
live copy is the pre-guard baseline (idempotent skip if already guarded; fail-loud abort if divergent, with
.bak rollback). Guard logic unchanged from Build 198 (8/8 pytest). Follow-on: bundle_config.json deny-globs
via json_key_append_from_file.py (never manual), then regenerate + VALIDATE.
