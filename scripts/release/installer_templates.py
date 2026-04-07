from __future__ import annotations


INSTALL_SCRIPT = """#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_APP_DIR="$SCRIPT_DIR/Voice2Code"
PACKAGE_BUNDLE_DIR="$SCRIPT_DIR/Voice2Code.app"
PACKAGE_APP_EXEC="$PACKAGE_BUNDLE_DIR/Contents/MacOS/Voice2Code"
PACKAGE_APP_CLI="$PACKAGE_BUNDLE_DIR/Contents/MacOS/voice2code-cli"
BUNDLED_BUILD_INFO="$PACKAGE_APP_DIR/BUILD_INFO.json"
BUNDLED_CONFIG="$PACKAGE_APP_DIR/config/voice2code_refiner_config.json"

TARGET_ROOT="$HOME/Library/Application Support/Voice2Code/Voice2CodeRefiner"
TARGET_CONFIG="$TARGET_ROOT/config/voice2code_refiner_config.json"
TARGET_BUILD_INFO="$TARGET_ROOT/BUILD_INFO.json"

APP_INSTALL_DIR="$HOME/Applications"
INSTALLED_APP_BUNDLE="$APP_INSTALL_DIR/Voice2Code.app"
INSTALLED_APP_EXEC="$INSTALLED_APP_BUNDLE/Contents/MacOS/Voice2Code"
INSTALLED_APP_CLI="$INSTALLED_APP_BUNDLE/Contents/MacOS/voice2code-cli"

WORKFLOW_DIR="$HOME/Library/Services/AI提纯指令.workflow"
WORKFLOW_INFO_PLIST="$WORKFLOW_DIR/Contents/Info.plist"
WORKFLOW_DOCUMENT="$WORKFLOW_DIR/Contents/document.wflow"
APP_ERROR_LOG="/tmp/Voice2Code_app_error.log"
TEMP_CONFIG=""
UI_CONFIRMED="false"
UI_PROVIDER_ID="gemini"
UI_PROXY_ENABLED="false"
UI_PROXY_SCHEME="http"
UI_PROXY_HOST="127.0.0.1"
UI_PROXY_PORT="7897"
UI_API_KEY_CONFIGURED="false"
UI_TEST_REQUESTED="false"
UI_TEST_PASSED="false"
UI_SMOKE_REQUESTED="false"
UI_SMOKE_PASSED="false"
UI_SMOKE_STATUS="未执行"
UI_INSTALL_ACTION="cancel"
UI_MESSAGE=""

INSTALL_PROGRAM_STATUS="未执行"
INSTALL_WORKFLOW_STATUS="未执行"
INSTALL_SMOKE_STATUS="未执行"
INSTALL_API_KEY_STATUS="未配置"

require_package_app() {
  [[ -x "$PACKAGE_APP_EXEC" && -x "$PACKAGE_APP_CLI" ]]
}

require_installed_app() {
  [[ -x "$INSTALLED_APP_EXEC" && -x "$INSTALLED_APP_CLI" ]]
}

provider_display_name() {
  case "${1:-gemini}" in
    openai) echo "OpenAI" ;;
    doubao) echo "Doubao" ;;
    *) echo "Gemini" ;;
  esac
}

show_notice() {
  local title="$1"
  local message="$2"
  local style="${3:-info}"
  local notice_exec=""
  if require_installed_app; then
    notice_exec="$INSTALLED_APP_EXEC"
  elif require_package_app; then
    notice_exec="$PACKAGE_APP_EXEC"
  fi
  if [[ -n "$notice_exec" ]] && "$notice_exec" --mode notice --title "$title" --message "$message" --style "$style" >/dev/null 2>&1; then
    return 0
  fi
  printf '%s\n\n%s\n' "$title" "$message"
}

read_build_field() {
  local file_path="$1"
  local key="$2"
  python3 - "$file_path" "$key" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]).expanduser()
key = sys.argv[2]
if not path.exists():
    print("")
    raise SystemExit(0)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
value = data.get(key, "")
print("" if value is None else str(value))
PY
}

load_helper_result() {
  local result_file="$1"
  python3 - "$result_file" <<'PY'
import json
import shlex
import sys

path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
fields = {
    "UI_CONFIRMED": data.get("confirmed", False),
    "UI_PROVIDER_ID": data.get("provider_id", "gemini"),
    "UI_PROXY_ENABLED": data.get("proxy_enabled", False),
    "UI_PROXY_SCHEME": data.get("proxy_scheme", "http"),
    "UI_PROXY_HOST": data.get("proxy_host", "127.0.0.1"),
    "UI_PROXY_PORT": data.get("proxy_port", 7897),
    "UI_API_KEY_CONFIGURED": data.get("api_key_configured", False),
    "UI_TEST_REQUESTED": data.get("test_requested", False),
    "UI_TEST_PASSED": data.get("test_passed", False),
    "UI_SMOKE_REQUESTED": data.get("smoke_requested", False),
    "UI_SMOKE_PASSED": data.get("smoke_passed", False),
    "UI_SMOKE_STATUS": data.get("smoke_status", "未执行"),
    "UI_INSTALL_ACTION": data.get("install_action", ""),
    "UI_MESSAGE": data.get("message", ""),
}
for key, value in fields.items():
    if isinstance(value, bool):
        rendered = "true" if value else "false"
    else:
        rendered = str(value)
    print(f"{key}={shlex.quote(rendered)}")
PY
}

refresh_services_registry() {
  /System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true
  /usr/bin/killall pbs >/dev/null 2>&1 || true
  /System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true
  sleep 0.2
}

refresh_services_registry_async() {
  (
    /System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true
    /usr/bin/killall pbs >/dev/null 2>&1 || true
    /System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true
  ) >/dev/null 2>&1 &
}

verify_workflow_installation() {
  [[ -d "$WORKFLOW_DIR" && -f "$WORKFLOW_INFO_PLIST" && -f "$WORKFLOW_DOCUMENT" ]]
}

read_network_mode_message() {
  python3 - "$TARGET_CONFIG" "$BUNDLED_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

target = Path(sys.argv[1]).expanduser()
bundled = Path(sys.argv[2])
source = target if target.exists() else bundled
if not source.exists():
    print("直连")
    raise SystemExit(0)
data = json.loads(source.read_text(encoding="utf-8"))
network = data.get("network", {})
enabled = bool(network.get("proxy_enabled", False))
scheme = str(network.get("proxy_scheme", "http") or "http").strip() or "http"
host = str(network.get("proxy_host", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1"
port = int(network.get("proxy_port", 7897) or 7897)
print(f"代理：{scheme}://{host}:{port}" if enabled else "直连")
PY
}

read_provider_message() {
  python3 - "$TARGET_CONFIG" "$BUNDLED_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

target = Path(sys.argv[1]).expanduser()
bundled = Path(sys.argv[2])
source = target if target.exists() else bundled
if not source.exists():
    print("Gemini")
    raise SystemExit(0)
data = json.loads(source.read_text(encoding="utf-8"))
provider = ((data.get("provider") or {}).get("provider_id", "gemini") or "gemini").strip().lower()
display = {
    "gemini": "Gemini",
    "openai": "OpenAI",
    "doubao": "Doubao",
}.get(provider, provider or "Gemini")
print(display)
PY
}

build_install_summary_message() {
  local installed_version installed_time
  installed_version="$(read_build_field "$TARGET_BUILD_INFO" "release_version")"
  installed_time="$(read_build_field "$TARGET_BUILD_INFO" "build_timestamp")"
  cat <<EOF
程序已安装：${INSTALL_PROGRAM_STATUS}
Quick Action 已注册：${INSTALL_WORKFLOW_STATUS}
转写烟测：${INSTALL_SMOKE_STATUS}

当前已安装版本：${installed_version:-未知}
当前已安装构建时间：${installed_time:-未知}
当前 AI Provider：$(read_provider_message)
当前网络方式：$(read_network_mode_message)
API Key：${INSTALL_API_KEY_STATUS}

App 路径：
${INSTALLED_APP_BUNDLE}

Quick Action 路径：
${WORKFLOW_DIR}
EOF
}

fallback_install_confirmation() {
  printf '\n[Voice2Code 安装 - 终端兼容模式]\n'
  printf '将安装 Voice2Code.app、本地运行环境和 AI提纯指令.workflow。\n'
  printf '继续安装？[Y/n] '
  read -r answer
  case "${answer:-Y}" in
    [Nn]*)
      UI_CONFIRMED="false"
      UI_INSTALL_ACTION="cancel"
      UI_MESSAGE="用户取消了安装。"
      ;;
    *)
      UI_CONFIRMED="true"
      UI_INSTALL_ACTION="install"
      UI_MESSAGE="已在终端兼容模式下确认安装。"
      ;;
  esac
}

launch_install_ui() {
  local result_file stderr_file helper_error
  result_file="$(mktemp)"
  stderr_file="$(mktemp)"
  if require_package_app && "$PACKAGE_APP_EXEC" \
    --mode install \
    --result-file "$result_file" \
    --bundled-build-info "$BUNDLED_BUILD_INFO" \
    --installed-build-info "$TARGET_BUILD_INFO" \
    --bundled-config "$BUNDLED_CONFIG" \
    --target-config "$TARGET_CONFIG" 2>"$stderr_file"; then
    eval "$(load_helper_result "$result_file")"
  else
    helper_error=""
    [[ -f "$stderr_file" ]] && helper_error="$(<"$stderr_file")"
    if [[ ! -x "$PACKAGE_APP_EXEC" ]]; then
      helper_error="app_missing_or_not_executable: $PACKAGE_APP_EXEC"
    fi
    printf '[%s] mode=install\n%s\n\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "${helper_error:-app_failed_without_stderr}" >> "$APP_ERROR_LOG"
    echo "Voice2Code 图形安装器启动失败，已切换到终端兼容模式。" >&2
    [[ -n "$helper_error" ]] && echo "$helper_error" >&2
    fallback_install_confirmation
  fi
  rm -f "$result_file" "$stderr_file"
}

perform_install() {
  if [[ ! -d "$PACKAGE_APP_DIR" || ! -f "$BUNDLED_BUILD_INFO" || ! -d "$PACKAGE_BUNDLE_DIR" ]]; then
    return 1
  fi

  if [[ -f "$TARGET_CONFIG" ]]; then
    TEMP_CONFIG="$(mktemp)"
    cp "$TARGET_CONFIG" "$TEMP_CONFIG"
  fi

  mkdir -p "$TARGET_ROOT" "$APP_INSTALL_DIR"
  rsync -a --delete --exclude '.DS_Store' "$PACKAGE_APP_DIR/" "$TARGET_ROOT/"
  rsync -a --delete --exclude '.DS_Store' "$PACKAGE_BUNDLE_DIR/" "$INSTALLED_APP_BUNDLE/"

  if [[ -n "$TEMP_CONFIG" && -f "$TEMP_CONFIG" ]]; then
    mkdir -p "$(dirname "$TARGET_CONFIG")"
    mv "$TEMP_CONFIG" "$TARGET_CONFIG"
  fi

  if ! python3 "$TARGET_ROOT/scripts/install_workflow.py"; then
    INSTALL_PROGRAM_STATUS="已完成"
    INSTALL_WORKFLOW_STATUS="未注册"
    return 1
  fi

  local bundled_version bundled_time installed_version installed_time
  bundled_version="$(read_build_field "$BUNDLED_BUILD_INFO" "release_version")"
  bundled_time="$(read_build_field "$BUNDLED_BUILD_INFO" "build_timestamp")"
  installed_version="$(read_build_field "$TARGET_BUILD_INFO" "release_version")"
  installed_time="$(read_build_field "$TARGET_BUILD_INFO" "build_timestamp")"
  if [[ -n "$installed_version" && "$installed_version" == "$bundled_version" && "$installed_time" == "$bundled_time" ]]; then
    INSTALL_PROGRAM_STATUS="已完成"
  else
    INSTALL_PROGRAM_STATUS="失败"
    return 1
  fi

  if verify_workflow_installation; then
    INSTALL_WORKFLOW_STATUS="已注册"
    refresh_services_registry_async
  else
    INSTALL_WORKFLOW_STATUS="未注册"
    return 1
  fi

  return 0
}

launch_initialize_config() {
  local result_file stderr_file helper_error
  result_file="$(mktemp)"
  stderr_file="$(mktemp)"
  if require_installed_app && "$INSTALLED_APP_EXEC" \
    --mode initialize-config \
    --result-file "$result_file" \
    --bundled-build-info "$BUNDLED_BUILD_INFO" \
    --installed-build-info "$TARGET_BUILD_INFO" \
    --bundled-config "$BUNDLED_CONFIG" \
    --target-config "$TARGET_CONFIG" 2>"$stderr_file"; then
    eval "$(load_helper_result "$result_file")"
  else
    helper_error=""
    [[ -f "$stderr_file" ]] && helper_error="$(<"$stderr_file")"
    printf '[%s] mode=initialize-config\n%s\n\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "${helper_error:-app_failed_without_stderr}" >> "$APP_ERROR_LOG"
    echo "Voice2Code 初始化配置窗口启动失败。" >&2
    [[ -n "$helper_error" ]] && echo "$helper_error" >&2
    UI_CONFIRMED="false"
    UI_MESSAGE="初始化配置窗口启动失败。"
  fi
  rm -f "$result_file" "$stderr_file"
}

launch_install_ui
if [[ "$UI_CONFIRMED" != "true" ]]; then
  exit 0
fi

if ! perform_install; then
  show_notice "Voice2Code 安装未完整完成" "$(build_install_summary_message)" "error"
  exit 1
fi

launch_initialize_config
if [[ "$UI_CONFIRMED" != "true" ]]; then
  show_notice "Voice2Code 初始化配置未完成" "$(build_install_summary_message)

程序与 Quick Action 已安装，但尚未完成初始化配置。请重新打开 Voice2Code.app 完成 Provider、网络方式与 API Key 配置。" "error"
  exit 1
fi

exit 0
"""


CONFIGURE_PROXY_SCRIPT = """#!/bin/zsh
set -euo pipefail

INSTALLED_APP_BUNDLE="$HOME/Applications/Voice2Code.app"
INSTALLED_APP_EXEC="$INSTALLED_APP_BUNDLE/Contents/MacOS/Voice2Code"
TARGET_ROOT="$HOME/Library/Application Support/Voice2Code/Voice2CodeRefiner"
TARGET_CONFIG="$TARGET_ROOT/config/voice2code_refiner_config.json"
TARGET_BUILD_INFO="$TARGET_ROOT/BUILD_INFO.json"
APP_ERROR_LOG="/tmp/Voice2Code_app_error.log"

if [[ ! -x "$INSTALLED_APP_EXEC" ]]; then
  echo "未检测到已安装的 Voice2Code.app：$INSTALLED_APP_EXEC" >&2
  exit 1
fi

if ! "$INSTALLED_APP_EXEC" \
  --mode open-settings \
  --installed-build-info "$TARGET_BUILD_INFO" \
  --target-config "$TARGET_CONFIG" \
  --bundled-config "$TARGET_CONFIG"; then
  printf '[%s] mode=open-settings\napp_failed_without_stderr\n\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" >> "$APP_ERROR_LOG"
  echo "Voice2Code 设置页启动失败。详细错误已写入：$APP_ERROR_LOG" >&2
  exit 1
fi
"""


INSTALL_README = """# Voice2Code 安装与使用说明

## 0. 发布信息

- 版本号：`__RELEASE_VERSION__`
- 更新时间：`__RELEASE_DATE__`
- 适用范围：__RELEASE_SCOPE__

## 1. 当前形态

本版本开始采用 **最小 App 控制壳架构**：

- `Voice2Code.app` 负责初始化配置、设置页、Provider 选择、网络方式与当前版本的 API Key 管理
- `AI提纯指令.workflow` 继续作为跨应用 Quick Action 触发入口
- Python Refiner Core 继续保留在本地运行目录中
- 当前不再把“系统级安全存储是否打通”作为安装完成门禁

## 2. 安装流程

1. 双击 `install.command`
2. 安装器会先显示安装确认窗口
3. 程序会安装：
   - `~/Applications/Voice2Code.app`
   - `~/Library/Application Support/Voice2Code/Voice2CodeRefiner`
   - `~/Library/Services/AI提纯指令.workflow`
4. 安装后会自动进入初始化配置窗口：
   - 选择 AI Provider
   - 选择直连 / 代理
   - 输入 API Key
   - 连通测试
   - 保存配置
   - 自动执行一条最小转写烟测
   - 在同一窗口内显示完成态

说明：

- 当前安装器已收简为两个阶段：
  - 第 1 阶段：安装确认
  - 第 2 阶段：初始化配置 + 自动烟测 + 完成态
- 成功路径不再额外弹出第三个独立“安装完成”总结窗

## 3. Quick Action 运行链路

Quick Action 不再承担复杂配置与凭据逻辑。它现在只负责：

- 获取选中文本
- 调用 `Voice2Code.app` 内的本地 CLI
- 由 App CLI 调用本地 Refiner Core
- 把结果回填到当前选中文本

## 4. 如何确认安装成功

安装成功至少应满足：

- `~/Applications/Voice2Code.app` 存在
- `~/Library/Services/AI提纯指令.workflow` 存在
- 初始化配置已通过一次 Provider 连通测试
- 初始化配置窗口中的自动转写烟测已给出结果
- 若当前环境无法持久化保存 API Key，可通过环境变量继续使用

## 5. 如何打开设置页

安装后如需再次修改 Provider、网络方式或 API Key，可双击：

- `配置代理.command`

该命令会直接打开 `Voice2Code.app` 的设置页。

## 6. API Key 说明

- 当前版本以 `Voice2Code.app` 作为配置与运行控制壳
- 若当前环境支持，App 会尝试持久化保存 API Key
- 若当前系统环境不支持持久化保存，仍可通过环境变量继续使用：
  - `V2C_API_KEY`
  - `V2C_GEMINI_API_KEY`
  - `V2C_OPENAI_API_KEY`
  - `V2C_DOUBAO_API_KEY`
- 当前版本不再把系统安全存储是否可用作为安装完成门禁
- 当前版本不宣称已完成系统级无感安全存储，这部分仍属于后续增强方向

## 7. 快捷键绑定

请前往：

- `系统设置 -> 键盘 -> 键盘快捷键 -> 服务 -> 文本`

找到 `AI提纯指令` 后绑定你习惯的快捷键。
"""


RELEASE_NOTES = """# Voice2Code Release Notes

## __RELEASE_VERSION__ · __RELEASE_DATE__

### 本版重点

- 交付形态从 `Quick Action + shell + 临时 helper` 升级为 **Quick Action + Voice2Code.app**
- `Voice2Code.app` 当前作为最小控制壳承担：
  - 初始化配置
  - Provider 选择
  - 网络配置
  - 当前版本的 API Key 管理
  - 本地 CLI 执行入口
- Quick Action 降级为稳定触发器，不再直接参与 secret 写入与复杂配置逻辑
- 安装器已收简为两个阶段：
  - 安装确认
  - 初始化配置 + 自动烟测 + 完成态（同窗切换）
- 成功路径不再额外弹出第三个独立“安装完成”总结窗
- 旧的 `SecKeychain*` / `security add-generic-password` 路线已移除
- 当前版本不再把系统安全存储是否通过作为安装门禁；相关能力已冻结为后续增强专项

### 当前范围

- 仍保留现有 Python Refiner Core
- 仍保留两层架构、双语 contract、provider-neutral service layer
- 当前版本不包含 App Store 发布、公证或完整签名流程
- 当前版本不宣称已完成系统级无感安全存储
- 当前发布目标是“稳定可交付”，不是继续扩大产品包装层改造
"""
