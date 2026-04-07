from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from .release_metadata import ReleaseContext


def _write_app_info_plist(context: ReleaseContext) -> None:
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key><string>zh_CN</string>
  <key>CFBundleExecutable</key><string>{context.app_executable_name}</string>
  <key>CFBundleIdentifier</key><string>{context.app_bundle_id}</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>CFBundleName</key><string>Voice2Code</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>{context.release_version}</string>
  <key>CFBundleVersion</key><string>{context.release_version}</string>
  <key>LSMinimumSystemVersion</key><string>{context.helper_min_macos}</string>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict>
</plist>
"""
    context.app_info_plist.write_text(plist, encoding="utf-8")

def build_app_bundle(context: ReleaseContext) -> None:
    context.app_executable_output.parent.mkdir(parents=True, exist_ok=True)
    (context.package_bundle_dir / "Contents" / "Resources").mkdir(parents=True, exist_ok=True)
    build_dir = Path(tempfile.mkdtemp(prefix="v2c_helper_build_"))
    built_arches: list[Path] = []
    try:
        for arch in context.helper_archs:
            arch_output = build_dir / f"{context.app_executable_name}_{arch}"
            env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET=context.helper_min_macos)
            result = subprocess.run(
                [
                    "/usr/bin/swiftc",
                    "-O",
                    "-target",
                    f"{arch}-apple-macos{context.helper_min_macos}",
                    "-framework",
                    "AppKit",
                    "-framework",
                    "Security",
                    str(context.app_source),
                    "-o",
                    str(arch_output),
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"swiftc failed for {arch}: {result.stderr.strip() or result.stdout.strip()}"
                )
            built_arches.append(arch_output)

        lipo_result = subprocess.run(
            ["/usr/bin/lipo", "-create", *[str(path) for path in built_arches], "-output", str(context.app_executable_output)],
            capture_output=True,
            text=True,
            check=False,
        )
        if lipo_result.returncode != 0:
            raise RuntimeError(f"lipo failed: {lipo_result.stderr.strip() or lipo_result.stdout.strip()}")
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

    context.app_executable_output.chmod(
        context.app_executable_output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )
    cli_path = context.app_executable_output.parent / context.app_cli_name
    if cli_path.exists() or cli_path.is_symlink():
        cli_path.unlink()
    os.symlink(context.app_executable_name, cli_path)
    _write_app_info_plist(context)
