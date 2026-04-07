#!/usr/bin/env python3
"""Diagnose whether macOS Keychain write failures come from the system or app-bundle code."""

from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_SWIFT = REPO_ROOT / "scripts" / "installer_ui.swift"
ENTITLEMENTS_TEMPLATE = (
    REPO_ROOT / "scripts" / "release" / "voice2code_app.entitlements.plist.template"
)


def run(cmd: list[str], *, input_text: str | None = None) -> dict[str, object]:
    proc = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def print_result(label: str, result: dict[str, object]) -> None:
    print(f"\n## {label}")
    print("$ " + " ".join(result["cmd"]))  # type: ignore[index]
    print(f"exit={result['returncode']}")
    if result["stdout"]:
        print("--- stdout ---")
        print(result["stdout"])
    if result["stderr"]:
        print("--- stderr ---")
        print(result["stderr"])


def assemble_app_bundle(app_bundle: Path) -> tuple[dict[str, object], Path]:
    app_macos = app_bundle / "Contents" / "MacOS"
    app_exec = app_macos / "Voice2Code"
    app_cli = app_macos / "voice2code-cli"
    app_info = app_bundle / "Contents" / "Info.plist"
    app_macos.mkdir(parents=True, exist_ok=True)
    compile_result = run(
        [
            "swiftc",
            "-framework",
            "AppKit",
            "-framework",
            "Security",
            str(INSTALLER_SWIFT),
            "-o",
            str(app_exec),
        ]
    )
    if compile_result["returncode"] == 0:
        plistlib.dump(
            {
                "CFBundleExecutable": "Voice2Code",
                "CFBundleIdentifier": "com.voice2code.app.diagnostic",
                "CFBundleInfoDictionaryVersion": "6.0",
                "CFBundleName": "Voice2Code",
                "CFBundlePackageType": "APPL",
                "CFBundleShortVersionString": "diagnostic",
                "CFBundleVersion": "diagnostic",
                "LSMinimumSystemVersion": "11.0",
                "NSPrincipalClass": "NSApplication",
            },
            app_info.open("wb"),
        )
        if not app_cli.exists():
            app_cli.symlink_to("Voice2Code")
    return compile_result, app_cli


def run_app_probe(app_cli: Path) -> dict[str, object]:
    return run(
        [
            str(app_cli),
            "--mode",
            "keychain-probe",
            "--provider-id",
            "gemini",
        ]
    )


def resolve_codesign_identity() -> tuple[str, str, dict[str, object]]:
    identity = os.environ.get("V2C_CODESIGN_IDENTITY", "").strip()
    identities_result = run(["security", "find-identity", "-v", "-p", "codesigning"])
    if not identity and identities_result["stdout"]:
        match = re.search(r'"([^"]+)"', str(identities_result["stdout"]))
        if match:
            identity = match.group(1)
    return identity, str(identities_result["stdout"]), identities_result


def resolve_team_id(identity: str) -> tuple[str, dict[str, object] | None]:
    team_id = os.environ.get("V2C_TEAM_ID", "").strip()
    if team_id or not identity:
        return team_id, None
    subject_result = run(
        [
            "sh",
            "-c",
            f"security find-certificate -c {json.dumps(identity)} -p | openssl x509 -noout -subject",
        ]
    )
    subject = str(subject_result["stdout"])
    match = re.search(r"\bOU=([A-Z0-9]+)\b", subject)
    return (match.group(1) if match else ""), subject_result


def sign_app_bundle(
    app_bundle: Path,
    *,
    identity: str,
    team_id: str,
    provisioning_profile: str | None,
) -> tuple[dict[str, object], dict[str, object], dict[str, object] | None]:
    with tempfile.TemporaryDirectory(prefix="v2c-entitlements-diag-") as temp_dir:
        entitlements_path = Path(temp_dir) / "Voice2Code.entitlements"
        template = ENTITLEMENTS_TEMPLATE.read_text(encoding="utf-8")
        entitlements_path.write_text(
            template.replace("__TEAM_ID__", team_id).replace("__BUNDLE_ID__", "com.voice2code.app.diagnostic"),
            encoding="utf-8",
        )
        if provisioning_profile:
            profile_path = Path(provisioning_profile).expanduser()
            shutil.copy2(profile_path, app_bundle / "Contents" / "embedded.provisionprofile")
        sign_result = run(
            [
                "codesign",
                "--force",
                "--deep",
                "--sign",
                identity,
                "--entitlements",
                str(entitlements_path),
                str(app_bundle),
            ]
        )
    verify_result = run(
        [
            "codesign",
            "--verify",
            "--deep",
            "--strict",
            "--verbose=2",
            str(app_bundle),
        ]
    )
    assess_result = run(["spctl", "--assess", "-vv", str(app_bundle)])
    return sign_result, verify_result, assess_result


def collect_recent_policy_logs(app_name: str) -> dict[str, object]:
    predicate = (
        f'eventMessage CONTAINS[c] "{app_name}" '
        'OR eventMessage CONTAINS[c] "No matching profile found" '
        'OR eventMessage CONTAINS[c] "Restricted entitlements not validated" '
        'OR eventMessage CONTAINS[c] "Disallowing com.voice2code.app"'
    )
    return run(
        [
            "log",
            "show",
            "--style",
            "syslog",
            "--last",
            "2m",
            "--predicate",
            predicate,
        ]
    )


def main() -> int:
    print("# Voice2Code Keychain Diagnostics")
    print(f"user={os.environ.get('USER', '')}")
    print(f"home={Path.home()}")

    sw_vers = run(["sw_vers"])
    print_result("macOS Version", sw_vers)

    default_keychain = run(["security", "default-keychain", "-d", "user"])
    print_result("Default Keychain", default_keychain)

    list_keychains = run(["security", "list-keychains", "-d", "user"])
    print_result("Keychain Search List", list_keychains)

    login_path = Path.home() / "Library" / "Keychains" / "login.keychain-db"
    file_info = run(["file", str(login_path)])
    print_result("Login Keychain File", file_info)

    show_info = run(["security", "show-keychain-info", str(login_path)])
    print_result("Login Keychain Info", show_info)

    service = f"Voice2Code.Diag.{uuid.uuid4().hex[:8]}"
    account = "diagnostic"
    secret = f"diag-{uuid.uuid4().hex}"

    add_default = run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            account,
            "-s",
            service,
            "-w",
            secret,
        ]
    )
    print_result("Write via security (default keychain)", add_default)

    add_explicit = run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            account,
            "-s",
            service,
            "-w",
            secret,
            str(login_path),
        ]
    )
    print_result("Write via security (explicit login.keychain-db)", add_explicit)

    find_default = run(
        [
            "security",
            "find-generic-password",
            "-a",
            account,
            "-s",
            service,
            "-w",
        ]
    )
    print_result("Read via security", find_default)

    delete_default = run(
        [
            "security",
            "delete-generic-password",
            "-a",
            account,
            "-s",
            service,
        ]
    )
    print_result("Delete via security", delete_default)

    identity, identity_list_output, identities_result = resolve_codesign_identity()
    print_result("Available Code Signing Identities", identities_result)
    team_id, subject_result = resolve_team_id(identity)
    if subject_result is not None:
        print_result("Signing Certificate Subject", subject_result)

    app_probe_result: dict[str, object] | None = None
    signed_probe_result: dict[str, object] | None = None
    signed_profile_probe_result: dict[str, object] | None = None
    signed_logs_result: dict[str, object] | None = None
    signed_profile_logs_result: dict[str, object] | None = None
    sign_result: dict[str, object] | None = None
    verify_result: dict[str, object] | None = None
    assess_result: dict[str, object] | None = None
    profile_sign_result: dict[str, object] | None = None
    profile_verify_result: dict[str, object] | None = None
    profile_assess_result: dict[str, object] | None = None
    if shutil.which("swiftc") and INSTALLER_SWIFT.exists():
        with tempfile.TemporaryDirectory(prefix="v2c-keychain-diag-") as temp_dir:
            app_bundle = Path(temp_dir) / "Voice2Code.app"
            compile_result, app_cli = assemble_app_bundle(app_bundle)
            print_result("Compile Voice2Code.app executable", compile_result)
            if compile_result["returncode"] == 0:
                app_probe_result = run_app_probe(app_cli)
                print_result("Run keychain probe via Voice2Code.app bundle", app_probe_result)
                if identity and team_id:
                    signed_bundle = Path(temp_dir) / "Voice2Code-signed.app"
                    shutil.copytree(app_bundle, signed_bundle)
                    sign_result, verify_result, assess_result = sign_app_bundle(
                        signed_bundle,
                        identity=identity,
                        team_id=team_id,
                        provisioning_profile=None,
                    )
                    print_result("Sign Voice2Code.app (developer identity)", sign_result)
                    print_result("Verify signed Voice2Code.app", verify_result)
                    print_result("Assess signed Voice2Code.app", assess_result)
                    if sign_result["returncode"] == 0:
                        signed_probe_result = run_app_probe(
                            signed_bundle / "Contents" / "MacOS" / "voice2code-cli"
                        )
                        print_result("Run keychain probe via signed Voice2Code.app", signed_probe_result)
                        if signed_probe_result["returncode"] != 0:
                            signed_logs_result = collect_recent_policy_logs("Voice2Code-signed.app")
                            print_result("Recent policy logs for signed Voice2Code.app", signed_logs_result)

                    provisioning_profile = os.environ.get("V2C_PROVISIONING_PROFILE", "").strip()
                    if provisioning_profile:
                        profiled_bundle = Path(temp_dir) / "Voice2Code-profiled.app"
                        shutil.copytree(app_bundle, profiled_bundle)
                        profile_sign_result, profile_verify_result, profile_assess_result = sign_app_bundle(
                            profiled_bundle,
                            identity=identity,
                            team_id=team_id,
                            provisioning_profile=provisioning_profile,
                        )
                        print_result("Sign Voice2Code.app (developer identity + profile)", profile_sign_result)
                        print_result("Verify profiled Voice2Code.app", profile_verify_result)
                        print_result("Assess profiled Voice2Code.app", profile_assess_result)
                        if profile_sign_result["returncode"] == 0:
                            signed_profile_probe_result = run_app_probe(
                                profiled_bundle / "Contents" / "MacOS" / "voice2code-cli"
                            )
                            print_result(
                                "Run keychain probe via signed+profiled Voice2Code.app",
                                signed_profile_probe_result,
                            )
                            if signed_profile_probe_result["returncode"] != 0:
                                signed_profile_logs_result = collect_recent_policy_logs(
                                    "Voice2Code-profiled.app"
                                )
                                print_result(
                                    "Recent policy logs for signed+profiled Voice2Code.app",
                                    signed_profile_logs_result,
                                )

    summary = {
        "security_default_write_ok": add_default["returncode"] == 0,
        "security_explicit_write_ok": add_explicit["returncode"] == 0,
        "security_read_ok": find_default["returncode"] == 0,
        "app_probe_ok": (
            app_probe_result["returncode"] == 0 if app_probe_result is not None else None
        ),
        "codesign_identity": identity or None,
        "team_id": team_id or None,
        "signed_app_probe_ok": (
            signed_probe_result["returncode"] == 0 if signed_probe_result is not None else None
        ),
        "signed_profile_app_probe_ok": (
            signed_profile_probe_result["returncode"] == 0
            if signed_profile_probe_result is not None
            else None
        ),
    }
    print("\n## Summary")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if summary["app_probe_ok"] is False and identity and team_id and summary["signed_app_probe_ok"] is False:
        print(
            "\nDiagnosis: the modern SecItem path fails both in an unsigned app bundle and "
            "after developer signing with restricted entitlements. Combined with the policy "
            "logs / spctl rejection, this indicates the remaining gate is provisioning-profile-"
            "backed entitlement validation, not the old SecKeychain helper code."
        )
        return 3

    if not summary["security_default_write_ok"] and not summary["security_explicit_write_ok"]:
        print(
            "\nDiagnosis: the old system-level security CLI path is failing outside "
            "Voice2Code code. This confirms the legacy file-keychain route is not reliable "
            "in this environment."
        )
        return 1

    if summary["app_probe_ok"] is False:
        print(
            "\nDiagnosis: security CLI write works, but the real Voice2Code.app bundle "
            "still fails the modern SecItem-based probe. This points to an app-shape, "
            "signature, or entitlement issue rather than the old helper route."
        )
        return 2

    print(
        "\nDiagnosis: basic Keychain write/read appears usable in this environment. "
        "If Voice2Code still fails, inspect app-side configuration save flow."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
