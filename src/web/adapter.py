"""Web adapter over the renderer-independent BFT service."""

from __future__ import annotations

import shutil
import hashlib
import os
import sys
import tempfile
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterable, Optional

from core.checking import SUBJECT_OUTPUT
from core.exceptions import BundleFileToolError
from core.rule_sources import available_presets
from core.service import BundleToolService, PlanResult
from core.user_state import UserStateStore
from core.version import __version__
from core.splash import web_splash_settings
from web.jobs import JobManager, JobRecord


MAX_JSON_BYTES = 1024 * 1024
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
MAX_UPLOADS = 8
MAX_PLANS = 16


@dataclass(frozen=True)
class UploadRecord:
    id: str
    name: str
    path: Path
    size: int

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "size": self.size}


class WebAdapter:
    """Translate HTTP-shaped data into calls on ``BundleToolService``."""

    def __init__(self, service: Optional[BundleToolService] = None,
                 *, job_manager: Optional[JobManager] = None,
                 state: Optional[UserStateStore] = None) -> None:
        self.service = service or BundleToolService()
        self.jobs = job_manager or JobManager()
        self.state = state or UserStateStore()
        self._plans: "OrderedDict[str, PlanResult]" = OrderedDict()
        self._uploads: "OrderedDict[str, UploadRecord]" = OrderedDict()
        self._lock = threading.RLock()
        self._temp_root = Path(tempfile.mkdtemp(prefix="bft_web_"))
        self._closed = False

    def bootstrap(self) -> Dict[str, Any]:
        presets = available_presets()
        return {
            "schema": "bft.web-bootstrap.v1",
            "version": __version__,
            "workspace_revision": hashlib.sha256(b"".join(
                (Path(__file__).parent / "static" / name).read_bytes()
                for name in ("index.html", "app.js", "app.css",
                             "pysplashx-splash.mjs", "pysplashx-splash.css"))).hexdigest(),
            "platform": sys.platform,
            "path_picker": "browser" if os.environ.get("BFT_WEB_BROWSER_PICKER") == "1" else "native",
            "profiles": self.service.available_profiles(),
            "default_profile": self.service.default_profile(),
            "presets": [
                {"name": name, "label": body.get("label", name)}
                for name, body in sorted(presets.items())
            ],
            "defaults": {
                "source_path": str(self.state.get("last_source_dir", "") or self.service._setting('global_settings.input_dir', '')),
                "bundle_path": str(self.state.get("last_bundle_open_dir", "") or ""),
                "bundle_output_dir": str(self.state.get("last_bundle_save_dir", "") or self.service._setting('global_settings.output_dir', '')),
                "extract_output_dir": self.service._setting('global_settings.output_dir', ''),
                "default_mode": self.service._setting('app_defaults.default_mode', 'bundle'),
                "overwrite_policy": self.service._setting('app_defaults.overwrite_policy', 'prompt'),
                "add_headers": self.service._setting('app_defaults.add_headers', True),
                "dry_run": self.service._setting('app_defaults.dry_run_default', True),
                "max_file_mb": float(self.service._effective_max_file_mb(None)),
                "web_skin": str(self.state.get("web_skin", "studio") or "studio"),
            },
            "limits": {
                "upload_bytes": MAX_UPLOAD_BYTES,
                "plans": MAX_PLANS,
                "uploads": MAX_UPLOADS,
            },
            "local_only": True,
            "splash": web_splash_settings(),
        }

    def set_web_skin(self, payload: Any) -> Dict[str, Any]:
        """Apply and persist one of the deliberately small web appearance set."""
        if not isinstance(payload, dict):
            raise BundleFileToolError("The appearance request must be a JSON object.")
        skin = payload.get("skin")
        if skin not in {"studio", "midnight"}:
            raise BundleFileToolError("'skin' must be 'studio' or 'midnight'.")
        return {"skin": skin, "persisted": self.state.set_and_save("web_skin", skin)}

    @staticmethod
    def _required_text(payload: Dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BundleFileToolError(f"'{key}' must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _optional_text(payload: Dict[str, Any], key: str) -> Optional[str]:
        value = payload.get(key)
        if value in (None, ""):
            return None
        if not isinstance(value, str):
            raise BundleFileToolError(f"'{key}' must be a string when provided.")
        return value.strip() or None

    @staticmethod
    def _string_list(payload: Dict[str, Any], key: str,
                     *, allow_none: bool = False) -> Optional[list[str]]:
        value = payload.get(key)
        if value is None and allow_none:
            return None
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise BundleFileToolError(f"'{key}' must be a list of strings.")
        return [item for item in (part.strip() for part in value) if item]

    def _store_plan(self, result: PlanResult) -> str:
        with self._lock:
            plan_id = uuid.uuid4().hex
            self._plans[plan_id] = result
            while len(self._plans) > MAX_PLANS:
                self._plans.popitem(last=False)
            return plan_id

    def _plan(self, plan_id: str) -> PlanResult:
        with self._lock:
            result = self._plans.get(plan_id)
            if result is None:
                raise BundleFileToolError(
                    "The selection plan is no longer available; create and review a new plan.")
            self._plans.move_to_end(plan_id)
            return result

    @staticmethod
    def _serialize_plan(plan_id: str, result: PlanResult) -> Dict[str, Any]:
        payload = result.to_dict()
        payload.update({
            "plan_id": plan_id,
            "base_path": str(result.base_path),
            "output_path": (
                str(result.inputs["output_path"])
                if result.inputs.get("output_path") is not None else None
            ),
            "rules": [
                {
                    "id": rule.id,
                    "label": rule.label or rule.id,
                    "layer": rule.layer.display,
                    "layer_label": rule.layer.label,
                    "action": rule.action.value,
                    "pattern": rule.pattern,
                    "locked": rule.layer.display in {"0", "5"},
                }
                for rule in result.rules
            ],
        })
        return payload

    def submit(self, action: str, payload: Dict[str, Any]) -> JobRecord:
        if not isinstance(payload, dict):
            raise BundleFileToolError("The request body must be a JSON object.")
        factories = {
            "plan": self._plan_work,
            "replan": self._replan_work,
            "check-selection": self._check_selection_work,
            "create": self._create_work,
            "check-bundle": self._check_bundle_work,
            "validate": self._validate_work,
            "extract": self._extract_work,
        }
        factory = factories.get(action)
        if factory is None:
            raise BundleFileToolError(f"Unknown web operation '{action}'.")
        return self.jobs.submit(action, factory(payload))

    def _plan_work(self, payload: Dict[str, Any]):
        source_values = payload.get("sources")
        if source_values is None:
            source_values = [self._required_text(payload, "source")]
        if (not isinstance(source_values, list) or not source_values
                or not all(isinstance(item, str) and item.strip()
                           for item in source_values)):
            raise BundleFileToolError("'sources' must contain one or more local paths.")
        sources = [Path(item.strip()) for item in source_values]
        base = self._optional_text(payload, "base_path")
        preset = self._string_list(payload, "presets", allow_none=True)
        include = self._string_list(payload, "include")
        exclude = self._string_list(payload, "exclude")
        output = self._optional_text(payload, "output_path")
        max_file_mb = payload.get("max_file_mb")

        def work(cancel, progress):
            result = self.service.plan_bundle(
                sources=sources,
                base_path=Path(base) if base else None,
                preset=preset,
                include=include,
                exclude=exclude,
                max_file_mb=max_file_mb,
                output_path=Path(output) if output else None,
                progress=progress,
                cancel=cancel,
            )
            plan_id = self._store_plan(result)
            if len(sources) == 1:
                self.state.set_and_save("last_source_dir", str(sources[0]))
            return {"plan": self._serialize_plan(plan_id, result)}
        return work

    def _replan_work(self, payload: Dict[str, Any]):
        plan = self._plan(self._required_text(payload, "plan_id"))
        overrides = payload.get("overrides", [])
        if not isinstance(overrides, list):
            raise BundleFileToolError("'overrides' must be a list.")
        parsed = []
        for item in overrides:
            if (not isinstance(item, (list, tuple)) or len(item) != 2
                    or item[0] not in {"include", "exclude"}
                    or not isinstance(item[1], str) or not item[1].strip()):
                raise BundleFileToolError(
                    "Each override must be ['include'|'exclude', 'path or pattern'].")
            parsed.append((item[0], item[1].strip()))

        requested_output = self._optional_text(payload, "output_path")

        def work(cancel, progress):
            changes: Dict[str, Any] = {"overrides": parsed}
            if "output_path" in payload:
                changes["output_path"] = (
                    Path(requested_output) if requested_output is not None else None
                )
            result = self.service.replan(
                plan, progress=progress, cancel=cancel, **changes)
            plan_id = self._store_plan(result)
            return {"plan": self._serialize_plan(plan_id, result)}
        return work

    def _check_selection_work(self, payload: Dict[str, Any]):
        plan = self._plan(self._required_text(payload, "plan_id"))
        profile = self._optional_text(payload, "profile")

        def work(cancel, progress):
            result = self.service.check_selection(
                plan, profile=profile, progress=progress, cancel=cancel)
            return {"check": result.to_dict()}
        return work

    def _create_work(self, payload: Dict[str, Any]):
        plan = self._plan(self._required_text(payload, "plan_id"))
        output = Path(self._required_text(payload, "output_path"))
        profile = self._optional_text(payload, "profile")
        estimate = plan.estimate()
        if estimate.requires_confirmation and payload.get("confirm_large") is not True:
            raise BundleFileToolError(
                "This plan is classified as large or extreme. Confirm the capacity "
                "estimate before creating the bundle.")

        def work(cancel, progress):
            result = self.service.create_bundle(
                sources=plan.sources,
                base_path=plan.base_path,
                profile=profile,
                output_path=output,
                plan=plan,
                progress=progress,
                cancel=cancel,
            )
            checked = self.service.check_bundle(
                output, profile=profile, progress=progress,
                cancel=cancel, subject=SUBJECT_OUTPUT)
            self.state.set_and_save("last_bundle_save_dir", str(output.parent))
            return {"bundle": result.to_dict(), "check": checked.to_dict()}
        return work

    def _source(self, payload: Dict[str, Any]) -> tuple[Path, str]:
        upload_id = self._optional_text(payload, "upload_id")
        if upload_id:
            with self._lock:
                upload = self._uploads.get(upload_id)
                if upload is None:
                    raise BundleFileToolError(
                        "The uploaded bundle is no longer available; upload it again.")
                self._uploads.move_to_end(upload_id)
                return upload.path, upload.name
        path = Path(self._required_text(payload, "bundle_path"))
        return path, str(path)

    @staticmethod
    def _entries(manifest) -> list[Dict[str, Any]]:
        return [
            {
                "path": entry.path,
                "size": entry.file_size_bytes,
                "encoding": entry.encoding,
                "binary": bool(entry.is_binary),
                "eol": entry.eol_style,
            }
            for entry in manifest.entries
        ]

    def _check_bundle_work(self, payload: Dict[str, Any]):
        source, label = self._source(payload)
        profile = self._optional_text(payload, "profile")
        encoding = self._optional_text(payload, "encoding")

        def work(cancel, progress):
            loaded = self.service.load_checked_bundle(
                source, profile=profile, encoding=encoding,
                progress=progress, cancel=cancel)
            checked = replace(loaded.check, label=label)
            if not payload.get("upload_id"):
                self.state.set_and_save("last_bundle_open_dir", str(source.parent))
            return {
                "check": checked.to_dict(),
                "entries": self._entries(loaded.manifest),
            }
        return work

    def _validate_work(self, payload: Dict[str, Any]):
        source, _label = self._source(payload)
        profile = self._optional_text(payload, "profile")
        encoding = self._optional_text(payload, "encoding")

        def work(_cancel, progress):
            result = self.service.validate_bundle(
                source, profile=profile, encoding=encoding, progress=progress)
            return {"validation": result.to_dict()}
        return work

    def _extract_work(self, payload: Dict[str, Any]):
        source, _label = self._source(payload)
        output = Path(self._required_text(payload, "output_dir"))
        profile = self._optional_text(payload, "profile")
        encoding = self._optional_text(payload, "encoding")
        policy = str(payload.get("overwrite_policy", self.service._setting('app_defaults.overwrite_policy', 'prompt'))).lower()
        if policy not in {"prompt", "skip", "rename", "overwrite"}:
            raise BundleFileToolError("Unknown overwrite policy.")

        def work(cancel, progress):
            result = self.service.extract_bundle(
                source, output,
                profile=profile,
                encoding=encoding,
                overwrite_policy=policy,
                add_headers=bool(payload.get("add_headers", self.service._setting('app_defaults.add_headers', True))),
                dry_run=bool(payload.get("dry_run", self.service._setting('app_defaults.dry_run_default', True))),
                progress=progress,
                cancel=cancel,
            )
            return {"extraction": result.to_dict()}
        return work

    def add_upload(self, name: str, length: int, stream: BinaryIO) -> UploadRecord:
        if length < 0 or length > MAX_UPLOAD_BYTES:
            raise BundleFileToolError(
                f"Bundle upload must be no larger than {MAX_UPLOAD_BYTES} bytes.")
        safe_name = Path(name or "bundle.txt").name or "bundle.txt"
        suffix = Path(safe_name).suffix[:16]
        upload_id = uuid.uuid4().hex
        destination = self._temp_root / f"{upload_id}{suffix}"
        remaining = length
        with destination.open("xb") as target:
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    destination.unlink(missing_ok=True)
                    raise BundleFileToolError("The bundle upload ended before its declared size.")
                target.write(chunk)
                remaining -= len(chunk)
        record = UploadRecord(upload_id, safe_name, destination, length)
        with self._lock:
            self._uploads[upload_id] = record
            while len(self._uploads) > MAX_UPLOADS:
                _old_id, old = self._uploads.popitem(last=False)
                old.path.unlink(missing_ok=True)
        return record

    def remove_upload(self, upload_id: str) -> bool:
        with self._lock:
            record = self._uploads.pop(upload_id, None)
        if record is None:
            return False
        record.path.unlink(missing_ok=True)
        return True

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self.jobs.close()
        shutil.rmtree(self._temp_root, ignore_errors=True)
