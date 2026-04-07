from __future__ import annotations

import stat
from pathlib import Path

from .build_helper import build_app_bundle
from .installer_templates import CONFIGURE_PROXY_SCRIPT, INSTALL_README, INSTALL_SCRIPT, RELEASE_NOTES
from .package_layout import build_zip, clean_dist, copy_payload
from .release_metadata import ReleaseContext, build_release_context, render_template, write_build_info


def write_install_assets(context: ReleaseContext) -> None:
    install_script_path = context.package_dir / "install.command"
    install_script_path.write_text(render_template(INSTALL_SCRIPT, context).rstrip() + "\n", encoding="utf-8")
    install_script_path.chmod(install_script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    configure_proxy_path = context.package_dir / "配置代理.command"
    configure_proxy_path.write_text(render_template(CONFIGURE_PROXY_SCRIPT, context).rstrip() + "\n", encoding="utf-8")
    configure_proxy_path.chmod(configure_proxy_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    readme_path = context.package_dir / "使用说明与安装.md"
    readme_path.write_text(render_template(INSTALL_README, context), encoding="utf-8")

    package_release_notes_path = context.package_dir / "RELEASE_NOTES.md"
    package_release_notes_path.write_text(render_template(RELEASE_NOTES, context), encoding="utf-8")

    context.dist_release_notes.write_text(render_template(RELEASE_NOTES, context), encoding="utf-8")


def main() -> int:
    context = build_release_context(Path(__file__).resolve().parents[2])
    clean_dist(context)
    copy_payload(context)
    write_build_info(context)
    build_app_bundle(context)
    write_install_assets(context)
    build_zip(context)
    print(f"dist package ready: {context.zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
