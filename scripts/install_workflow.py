import json
import os
import plistlib
import subprocess
import sys
import time
import uuid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from refiner.config_loader import DEFAULT_RUNTIME_CONTEXT, GENERATION_MODEL, INTENT_MODEL, load_refiner_config
from refiner.glossary import ensure_glossary_file

SERVICES_DIR = os.path.expanduser("~/Library/Services")
TARGET_DIR = os.path.join(SERVICES_DIR, "AI提纯指令.workflow")
CONTENTS_DIR = os.path.join(TARGET_DIR, "Contents")
RUNNER_PATH = os.path.join(SCRIPT_DIR, "voice2code_runner.py")


def build_shell_script() -> str:
    default_runtime_context_json = json.dumps(DEFAULT_RUNTIME_CONTEXT, ensure_ascii=False)
    lines = [
        "#!/bin/zsh",
        "",
        "export PYTHONIOENCODING=utf-8",
        "export LANG=zh_CN.UTF-8",
        'export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"',
        'APP_CLI="$HOME/Applications/Voice2Code.app/Contents/MacOS/voice2code-cli"',
        'RUNNER_PATH="{}"'.format(RUNNER_PATH.replace('"', '\\"')),
        'DEFAULT_RUNTIME_CONTEXT_JSON="{}"'.format(default_runtime_context_json.replace('"', '\\"')),
        "",
        "build_runtime_context() {",
        '  INPUT_TEXT="$1" DEFAULT_RUNTIME_CONTEXT_JSON="$DEFAULT_RUNTIME_CONTEXT_JSON" python3 - <<\'PY\'',
        "import json",
        "import os",
        "import re",
        "import subprocess",
        "",
        "ctx = json.loads(os.environ.get(\"DEFAULT_RUNTIME_CONTEXT_JSON\", \"{}\"))",
        "input_text = os.environ.get(\"INPUT_TEXT\", \"\")",
        "ctx[\"selection_length\"] = len(input_text)",
        "ctx[\"target_surface\"] = \"automator_quick_action\"",
        "",
        "def osa_lines(lines):",
        "    args = []",
        "    for line in lines:",
        "        args.extend([\"-e\", line])",
        "    try:",
        "        return subprocess.check_output([\"osascript\", *args], stderr=subprocess.DEVNULL, text=True).strip()",
        "    except Exception:",
        "        return \"\"",
        "",
        "app = osa_lines(['tell application \"System Events\" to get name of first application process whose frontmost is true'])",
        "ctx[\"editor_name\"] = app",
        "title = \"\"",
        "if app:",
        "    safe_app = app.replace('\\\"', '\\\\\\\"')",
        "    title = osa_lines([",
        "        'tell application \"System Events\"',",
        "        f'tell process \"{safe_app}\"',",
        "        'try',",
        "        'return value of attribute \"AXTitle\" of front window',",
        "        'on error',",
        "        'return \"\"',",
        "        'end try',",
        "        'end tell',",
        "        'end tell',",
        "    ])",
        "match = re.search(r'(\\.[A-Za-z0-9]{1,8})(?=$|\\s|\\)|\\]|-|_)', title)",
        "if match:",
        "    ctx[\"file_type\"] = match.group(1).lower()",
        "",
        "print(json.dumps(ctx, ensure_ascii=False))",
        "PY",
        "}",
        "",
        'INPUT_TEXT=$(cat)',
        'if [ -z "$INPUT_TEXT" ]; then',
        '  exit 0',
        'fi',
        "",
        'if [ ! -x "$APP_CLI" ]; then',
        '  printf "[Voice2Code App 未安装或 CLI 不可执行: %s]\\n\\n%s" "$APP_CLI" "$INPUT_TEXT"',
        '  exit 1',
        'fi',
        "",
        'export V2C_RUNTIME_CONTEXT_JSON="$(build_runtime_context "$INPUT_TEXT")"',
        "",
        'printf "%s" "$INPUT_TEXT" | "$APP_CLI" --mode run-refine',
    ]
    return "\n".join(lines) + "\n"


def build_document_plist(script: str) -> dict:
    uuid_main = str(uuid.uuid4()).upper()
    uuid_input = str(uuid.uuid4()).upper()
    uuid_output = str(uuid.uuid4()).upper()
    return {
        "AMApplicationBuild": "523",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [
            {
                "action": {
                    "AMAccepts": {"Container": "List", "Optional": True, "Types": ["com.apple.cocoa.string"]},
                    "AMActionVersion": "2.0.3",
                    "AMApplication": ["Automator"],
                    "AMParameterProperties": {
                        "COMMAND_STRING": {},
                        "CheckedForUserDefaultShell": {},
                        "inputMethod": {},
                        "shell": {},
                        "source": {},
                    },
                    "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
                    "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
                    "ActionName": "Run Shell Script",
                    "ActionParameters": {
                        "COMMAND_STRING": script,
                        "CheckedForUserDefaultShell": True,
                        "inputMethod": 0,
                        "shell": "/bin/zsh",
                        "source": "",
                    },
                    "BundleIdentifier": "com.apple.RunShellScript",
                    "CFBundleVersion": "2.0.3",
                    "CanShowSelectedItemsWhenRun": False,
                    "CanShowWhenRun": True,
                    "Category": ["AMCategoryUtilities"],
                    "Class Name": "RunShellScriptAction",
                    "InputUUID": uuid_input,
                    "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
                    "OutputUUID": uuid_output,
                    "UUID": uuid_main,
                    "UnlocalizedApplications": ["Automator"],
                    "arguments": {
                        "0": {"default value": 0, "name": "inputMethod", "required": "0", "type": "0", "uuid": "0"},
                        "1": {"default value": False, "name": "CheckedForUserDefaultShell", "required": "0", "type": "0", "uuid": "1"},
                        "2": {"default value": "", "name": "source", "required": "0", "type": "0", "uuid": "2"},
                        "3": {"default value": "", "name": "COMMAND_STRING", "required": "0", "type": "0", "uuid": "3"},
                        "4": {"default value": "/bin/sh", "name": "shell", "required": "0", "type": "0", "uuid": "4"},
                    },
                    "isViewVisible": True,
                    "location": "300.000000:300.000000",
                    "nibPath": "/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib",
                },
                "isViewVisible": True,
            }
        ],
        "connectors": {},
        "workflowMetaData": {
            "applicationBundleIDsByPath": {},
            "applicationPaths": [],
            "inputTypeIdentifier": "com.apple.Automator.text",
            "outputTypeIdentifier": "com.apple.Automator.text",
            "presentationMode": 11,
            "processesInput": 1,
            "serviceInputTypeIdentifier": "com.apple.Automator.text",
            "serviceOutputTypeIdentifier": "com.apple.Automator.text",
            "serviceProcessesInput": 1,
            "systemImageName": "NSActionTemplate",
            "useAutomaticInputType": 0,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }


def build_info_plist() -> dict:
    return {
        "NSServices": [
            {
                "NSMenuItem": {"default": "AI提纯指令"},
                "NSMessage": "runWorkflowAsService",
                "NSReturnTypes": ["public.utf8-plain-text"],
                "NSSendTypes": ["public.utf8-plain-text"],
                "NSPortName": "Automator",
                "NSTimeout": "10000",
            }
        ]
    }


def refresh_service_registry() -> None:
    commands = [
        ["/System/Library/CoreServices/pbs", "-flush"],
        ["/usr/bin/killall", "pbs"],
        ["/System/Library/CoreServices/pbs", "-flush"],
    ]
    for command in commands:
        try:
            subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    time.sleep(0.1)


def verify_workflow_installation() -> bool:
    return (
        os.path.isdir(TARGET_DIR)
        and os.path.isfile(os.path.join(CONTENTS_DIR, "document.wflow"))
        and os.path.isfile(os.path.join(CONTENTS_DIR, "Info.plist"))
    )


def main() -> int:
    load_refiner_config()
    ensure_glossary_file()
    os.makedirs(SERVICES_DIR, exist_ok=True)
    os.makedirs(CONTENTS_DIR, exist_ok=True)

    document_plist = build_document_plist(build_shell_script())
    info_plist = build_info_plist()

    try:
        with open(os.path.join(CONTENTS_DIR, "document.wflow"), "wb") as f:
            plistlib.dump(document_plist, f)
        with open(os.path.join(CONTENTS_DIR, "Info.plist"), "wb") as f:
            plistlib.dump(info_plist, f)
    except Exception:
        return 1

    return 0 if verify_workflow_installation() else 1


if __name__ == "__main__":
    raise SystemExit(main())
