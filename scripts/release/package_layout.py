from __future__ import annotations

import shutil
import zipfile

from .release_metadata import ReleaseContext


COPYTREE_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".DS_Store",
    "build_dist.py",
    "release",
)


def clean_dist(context: ReleaseContext) -> None:
    if context.package_dir.exists():
        shutil.rmtree(context.package_dir)
    if context.zip_path.exists():
        context.zip_path.unlink()
    if context.legacy_package_dir != context.package_dir and context.legacy_package_dir.exists():
        shutil.rmtree(context.legacy_package_dir)
    if context.legacy_zip_path != context.zip_path and context.legacy_zip_path.exists():
        context.legacy_zip_path.unlink()
    if context.dist_release_notes.exists():
        context.dist_release_notes.unlink()
    context.dist_dir.mkdir(parents=True, exist_ok=True)


def copy_payload(context: ReleaseContext) -> None:
    context.package_app_dir.mkdir(parents=True, exist_ok=True)
    for relative_target, source in context.included_paths:
        target = context.package_app_dir / relative_target
        if source.is_dir():
            shutil.copytree(source, target, ignore=COPYTREE_IGNORE)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def build_zip(context: ReleaseContext) -> None:
    with zipfile.ZipFile(context.zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(context.package_dir.rglob("*")):
            if path.is_dir() or path.name == ".DS_Store":
                continue
            zf.write(path, path.relative_to(context.dist_dir))
