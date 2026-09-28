"""Optional VCS Tool adapter for BFT's repository boundary.

The adapter imports only the installed ``vcs_tool`` package facade.  It never
invokes Git directly, parses CLI output, or reaches into provider modules.
Filesystem-only BFT use therefore remains independent of VCS Tool.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Tuple

from core.repository import (
    RepositoryFile,
    RepositoryIntegrationError,
    RepositoryInventory,
    RepositoryReadSession,
    RepositoryStatus,
)


VCS_TOOL_DISTRIBUTION = "vcs-tool==0.5.0a1"
VCS_TOOL_RUNTIME_VERSION = "0.5.0-alpha.1"


def _warning_codes(result: object) -> Tuple[str, ...]:
    warnings = getattr(result, "warnings", ()) or ()
    return tuple(str(getattr(item, "code", "VCS_WARN_UNKNOWN")) for item in warnings)


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


@dataclass(frozen=True)
class VcsToolRepositoryReader:
    """Translate the pinned VCS Tool facade into BFT repository records."""

    denied_roots: Tuple[Path, ...] = ()
    git_executable: Optional[Path] = None
    timeout_seconds: float = 10.0
    operation_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "denied_roots",
            tuple(Path(item).resolve() for item in self.denied_roots),
        )
        if self.git_executable is not None:
            object.__setattr__(self, "git_executable", Path(self.git_executable))

    @staticmethod
    def _api() -> Any:
        try:
            api = import_module("vcs_tool")
        except ModuleNotFoundError as error:
            if error.name != "vcs_tool":
                raise
            raise RepositoryIntegrationError(
                "Repository mode requires the optional "
                f"{VCS_TOOL_DISTRIBUTION} distribution."
            ) from error

        version = str(getattr(api, "__version__", ""))
        if version != VCS_TOOL_RUNTIME_VERSION:
            found = version or "unknown"
            raise RepositoryIntegrationError(
                "Unsupported VCS Tool runtime version "
                f"{found!r}; expected {VCS_TOOL_RUNTIME_VERSION!r}."
            )
        return api

    def _tool(self, api: Any, root: Path, allowed_root: Path) -> Any:
        return api.VcsTool(
            root=Path(root).resolve(),
            allowed_roots=(Path(allowed_root).resolve(),),
            denied_roots=self.denied_roots,
            git_executable=self.git_executable,
            timeout_seconds=self.timeout_seconds,
            operation_timeout_seconds=self.operation_timeout_seconds,
            include_remote_url=False,
        )

    @staticmethod
    def _invoke(api: Any, operation: str, callback: Callable[[], Any]) -> Any:
        try:
            return callback()
        except Exception as error:
            error_type = getattr(api, "VcsError", None)
            if error_type is None or not isinstance(error, error_type):
                raise
            code = str(getattr(error, "code", "VCS_ERROR"))
            raise RepositoryIntegrationError(
                f"VCS Tool {operation} failed [{code}]: {error}"
            ) from error

    @staticmethod
    def _file(item: Any) -> RepositoryFile:
        return RepositoryFile(
            path=str(item.path),
            tracked=bool(item.is_tracked),
            untracked=bool(item.is_untracked),
            ignored=bool(item.is_ignored),
            index_state=_enum_value(item.index_status),
            worktree_state=_enum_value(item.worktree_status),
        )

    @classmethod
    def _inventory_from_file_result(cls, result: Any) -> RepositoryInventory:
        return RepositoryInventory(
            repository_root=Path(result.root_dir),
            files=tuple(cls._file(item) for item in result.files),
            provider_id=str(result.provider_id or "unknown"),
            provider_version=result.provider_version,
            warnings=_warning_codes(result),
        )

    @classmethod
    def _inventory_from_tree(cls, tree: Any) -> RepositoryInventory:
        def walk(node: Any) -> Iterator[Any]:
            vcs_file = getattr(node, "vcs_file", None)
            if vcs_file is not None:
                yield vcs_file
            for child in getattr(node, "children", ()):
                yield from walk(child)

        files = tuple(cls._file(item) for item in walk(tree.root))
        if int(tree.total_files) != len(files):
            raise RepositoryIntegrationError(
                "VCS Tool read-session tree count does not match its file inventory."
            )
        return RepositoryInventory(
            repository_root=Path(tree.root_dir),
            files=files,
            provider_id=str(tree.provider_id or "unknown"),
            provider_version=tree.provider_version,
            warnings=_warning_codes(tree),
        )

    def inspect(self, root: Path, *, allowed_root: Path) -> RepositoryStatus:
        api = self._api()
        result = self._invoke(
            api,
            "inspect",
            lambda: self._tool(api, root, allowed_root).inspect(),
        )
        worktree = result.worktree
        return RepositoryStatus(
            requested_root=Path(result.requested_dir),
            repository_root=(Path(result.root_dir) if result.root_dir is not None else None),
            is_repository=bool(result.is_repository),
            is_clean=(worktree.is_clean if worktree is not None else None),
            provider_id=str(result.provider_id or "unknown"),
            provider_version=result.provider_version,
            warnings=_warning_codes(result),
        )

    def list_files(
        self,
        root: Path,
        *,
        allowed_root: Path,
        include_tracked: bool,
        include_untracked: bool,
        include_ignored: bool,
    ) -> RepositoryInventory:
        api = self._api()
        tool = self._tool(api, root, allowed_root)
        options = api.VcsFileListOptions(
            include_tracked=include_tracked,
            include_untracked=include_untracked,
            include_ignored=include_ignored,
        )
        result = self._invoke(api, "list-files", lambda: tool.list_files(options))
        return self._inventory_from_file_result(result)

    def open_read_session(
        self,
        root: Path,
        *,
        allowed_root: Path,
        max_file_bytes: int,
    ) -> RepositoryReadSession:
        if not isinstance(max_file_bytes, int) or isinstance(max_file_bytes, bool):
            raise RepositoryIntegrationError("Repository read byte limit must be an integer.")
        if max_file_bytes <= 0:
            raise RepositoryIntegrationError("Repository read byte limit must be positive.")

        api = self._api()
        tool = self._tool(api, root, allowed_root)
        limits = api.VcsReadLimits(max_read_bytes_per_file=max_file_bytes)
        options = api.VcsReadSessionOptions(
            source_kind=api.ReadSourceKind.WORKING_TREE,
            content_access=api.VcsContentAccess(
                metadata=True,
                bounded_bytes=True,
                verified_spool=False,
            ),
            include_tracked=True,
            include_untracked=False,
            include_ignored=False,
            hash_mode=api.HashMode.INVENTORY,
            limits=limits,
            plan_consistency=api.PlanConsistency.CONTENT_DIGEST,
        )
        raw = self._invoke(api, "open-read-session", lambda: tool.open_read_session(options))
        try:
            tree = self._invoke(api, "tree", raw.tree)
            manifest = tree.plan_manifest
            token = tree.plan_token
            if manifest is None or not isinstance(token, str) or not token:
                raise RepositoryIntegrationError(
                    "VCS Tool did not return the required session plan manifest."
                )
            inventory = self._inventory_from_tree(tree)
            return _VcsToolReadSession(
                api=api,
                raw=raw,
                inventory=inventory,
                plan_token=token,
                plan_manifest_digest=str(manifest.manifest_digest),
            )
        except BaseException:
            raw.close()
            raise


@dataclass
class _VcsToolReadSession:
    api: Any
    raw: Any
    inventory: RepositoryInventory
    plan_token: str
    plan_manifest_digest: str
    _closed: bool = False

    def read_bytes(self, path: str) -> bytes:
        if self._closed:
            raise RepositoryIntegrationError("The repository read session is closed.")
        if path not in self.inventory.by_path():
            raise RepositoryIntegrationError(
                f"Repository path is not part of the approved read session: {path}"
            )
        result = VcsToolRepositoryReader._invoke(
            self.api,
            "read-bytes",
            lambda: self.raw.read_bytes(path, plan_token=self.plan_token),
        )
        content = result.content
        descriptor = result.descriptor
        if not isinstance(content, bytes):
            raise RepositoryIntegrationError("VCS Tool returned a non-bytes content payload.")
        if str(descriptor.path) != path:
            raise RepositoryIntegrationError("VCS Tool returned content for a different path.")
        if int(descriptor.size_bytes) != len(content):
            raise RepositoryIntegrationError("VCS Tool content size evidence does not match.")
        if not bool(descriptor.plan_verified):
            raise RepositoryIntegrationError("VCS Tool did not verify the read against its plan.")
        digest = str(descriptor.content_sha256 or "")
        if digest != hashlib.sha256(content).hexdigest():
            raise RepositoryIntegrationError("VCS Tool content digest evidence does not match.")
        return content

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.raw.close()

    def __enter__(self) -> "_VcsToolReadSession":
        if self._closed:
            raise RepositoryIntegrationError("The repository read session is closed.")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
