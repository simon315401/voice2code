from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


RELEASE_VERSION = "v0.3.8"
RELEASE_DATE = "2026-04-02"
RELEASE_SCOPE = "macOS Quick Action 安装包，适用于 Cursor / antigravity / 通用 AI 对话输入整理场景"
PACKAGE_BASENAME = "Voice2Code_安装包"
HELPER_MIN_MACOS = "11.0"
HELPER_ARCHS = ("arm64", "x86_64")


@dataclass(frozen=True)
class ReleaseContext:
    project_root: Path
    dist_dir: Path
    package_basename: str
    release_version: str
    release_date: str
    release_scope: str
    package_name: str
    package_dir: Path
    package_app_dir: Path
    package_bundle_dir: Path
    zip_path: Path
    dist_release_notes: Path
    build_timestamp: str
    build_info_file: Path
    app_source: Path
    app_bundle_id: str
    app_executable_name: str
    app_cli_name: str
    app_executable_output: Path
    app_info_plist: Path
    helper_min_macos: str
    helper_archs: tuple[str, ...]
    included_paths: list[tuple[str, Path]]
    legacy_package_dir: Path
    legacy_zip_path: Path


def build_release_context(project_root: Path) -> ReleaseContext:
    dist_dir = project_root / "dist"
    package_name = f"{PACKAGE_BASENAME}_{RELEASE_VERSION}"
    package_dir = dist_dir / package_name
    package_app_dir = package_dir / "Voice2Code"
    package_bundle_dir = package_dir / "Voice2Code.app"
    return ReleaseContext(
        project_root=project_root,
        dist_dir=dist_dir,
        package_basename=PACKAGE_BASENAME,
        release_version=RELEASE_VERSION,
        release_date=RELEASE_DATE,
        release_scope=RELEASE_SCOPE,
        package_name=package_name,
        package_dir=package_dir,
        package_app_dir=package_app_dir,
        package_bundle_dir=package_bundle_dir,
        zip_path=dist_dir / f"{package_name}.zip",
        dist_release_notes=dist_dir / "RELEASE_NOTES.md",
        build_timestamp=time.strftime("%Y-%m-%d %H:%M:%S %z"),
        build_info_file=package_app_dir / "BUILD_INFO.json",
        app_source=project_root / "scripts" / "installer_ui.swift",
        app_bundle_id="com.voice2code.app",
        app_executable_name="Voice2Code",
        app_cli_name="voice2code-cli",
        app_executable_output=package_bundle_dir / "Contents" / "MacOS" / "Voice2Code",
        app_info_plist=package_bundle_dir / "Contents" / "Info.plist",
        helper_min_macos=HELPER_MIN_MACOS,
        helper_archs=HELPER_ARCHS,
        included_paths=[
            ("scripts", project_root / "scripts"),
            ("config", project_root / "config"),
            ("docs/Voice2Code_Architecture.md", project_root / "docs" / "Voice2Code_Architecture.md"),
            ("docs/Voice2Code_PRD.md", project_root / "docs" / "Voice2Code_PRD.md"),
        ],
        legacy_package_dir=dist_dir / PACKAGE_BASENAME,
        legacy_zip_path=dist_dir / f"{PACKAGE_BASENAME}.zip",
    )


def render_template(text: str, context: ReleaseContext) -> str:
    return (
        text.replace("__RELEASE_VERSION__", context.release_version)
        .replace("__RELEASE_DATE__", context.release_date)
        .replace("__RELEASE_SCOPE__", context.release_scope)
    )


def write_build_info(context: ReleaseContext) -> None:
    build_info = {
        "release_version": context.release_version,
        "release_date": context.release_date,
        "build_timestamp": context.build_timestamp,
        "release_scope": context.release_scope,
        "source_root": str(context.project_root),
    }
    context.build_info_file.write_text(
        json.dumps(build_info, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
