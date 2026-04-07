import AppKit
import CryptoKit
import Foundation
import Security

struct BuildInfo: Decodable {
    let releaseVersion: String?
    let releaseDate: String?
    let buildTimestamp: String?

    enum CodingKeys: String, CodingKey {
        case releaseVersion = "release_version"
        case releaseDate = "release_date"
        case buildTimestamp = "build_timestamp"
    }
}

struct InstallerResult: Encodable {
    let mode: String
    let confirmed: Bool
    let providerId: String
    let proxyEnabled: Bool
    let proxyScheme: String
    let proxyHost: String
    let proxyPort: Int
    let apiKeyConfigured: Bool
    let testRequested: Bool
    let testPassed: Bool
    let smokeRequested: Bool
    let smokePassed: Bool
    let smokeStatus: String
    let installAction: String
    let versionRelation: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case mode
        case confirmed
        case providerId = "provider_id"
        case proxyEnabled = "proxy_enabled"
        case proxyScheme = "proxy_scheme"
        case proxyHost = "proxy_host"
        case proxyPort = "proxy_port"
        case apiKeyConfigured = "api_key_configured"
        case testRequested = "test_requested"
        case testPassed = "test_passed"
        case smokeRequested = "smoke_requested"
        case smokePassed = "smoke_passed"
        case smokeStatus = "smoke_status"
        case installAction = "install_action"
        case versionRelation = "version_relation"
        case message
    }
}

enum LaunchMode: String {
    case install = "install"
    case initializeConfig = "initialize-config"
    case configureNetwork = "configure-network"
    case openSettings = "open-settings"
    case runRefine = "run-refine"
    case keychainProbe = "keychain-probe"
    case notice = "notice"
}

enum NoticeStyle: String {
    case info
    case error
}

enum VersionRelation: String {
    case firstInstall = "first_install"
    case upgrade = "upgrade"
    case reinstall = "reinstall"
    case downgrade = "downgrade"
    case installedUnknown = "installed_unknown"
}

struct ProxyState {
    var enabled: Bool
    var scheme: String
    var host: String
    var port: Int

    var endpoint: String {
        "\(scheme)://\(host):\(port)"
    }
}

struct ProviderOption {
    let id: String
    let displayName: String
    let baseURL: String
    let apiStyle: String
    let intentModel: String
    let generationModel: String
    let keychainService: String
    let keychainAccount: String
}

struct ProviderState {
    var providerId: String
    var intentModel: String
    var generationModel: String
}

private struct VaultEnvelope: Codable {
    let schemaVersion: Int
    let cipher: String
    let salt: String
    let nonce: String
    let ciphertext: String
    let tag: String

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case cipher
        case salt
        case nonce
        case ciphertext
        case tag
    }
}

private let providerCatalog: [ProviderOption] = [
    ProviderOption(
        id: "gemini",
        displayName: "Gemini",
        baseURL: "https://generativelanguage.googleapis.com/v1beta",
        apiStyle: "gemini_generate_content",
        intentModel: "gemini-3.1-flash-lite-preview",
        generationModel: "gemini-3.1-flash-lite-preview",
        keychainService: "Voice2Code.GeminiAPIKey",
        keychainAccount: "default"
    ),
    ProviderOption(
        id: "openai",
        displayName: "OpenAI",
        baseURL: "https://api.openai.com/v1",
        apiStyle: "openai_chat_completions",
        intentModel: "gpt-5.4-nano",
        generationModel: "gpt-5.4-nano",
        keychainService: "Voice2Code.OpenAIAPIKey",
        keychainAccount: "default"
    ),
    ProviderOption(
        id: "doubao",
        displayName: "Doubao",
        baseURL: "https://ark.cn-beijing.volces.com/api/v3",
        apiStyle: "openai_chat_completions",
        intentModel: "doubao-seed-1-6-250615",
        generationModel: "doubao-seed-1-6-250615",
        keychainService: "Voice2Code.DoubaoAPIKey",
        keychainAccount: "default"
    ),
]

private func providerOption(for providerId: String) -> ProviderOption {
    providerCatalog.first(where: { $0.id == providerId }) ?? providerCatalog[0]
}

struct LaunchOptions {
    var mode: LaunchMode = .install
    var resultFile: String = ""
    var bundledBuildInfoPath: String = ""
    var installedBuildInfoPath: String = ""
    var bundledConfigPath: String = ""
    var targetConfigPath: String = ""
    var title: String = ""
    var message: String = ""
    var style: NoticeStyle = .info
    var providerId: String = "gemini"

    static func parse(from arguments: [String]) -> LaunchOptions {
        var options = LaunchOptions()
        var index = 0
        while index < arguments.count {
            let key = arguments[index]
            let next = index + 1 < arguments.count ? arguments[index + 1] : ""
            switch key {
            case "--mode":
                options.mode = LaunchMode(rawValue: next) ?? .install
                index += 2
            case "--result-file":
                options.resultFile = next
                index += 2
            case "--bundled-build-info":
                options.bundledBuildInfoPath = next
                index += 2
            case "--installed-build-info":
                options.installedBuildInfoPath = next
                index += 2
            case "--bundled-config":
                options.bundledConfigPath = next
                index += 2
            case "--target-config":
                options.targetConfigPath = next
                index += 2
            case "--title":
                options.title = next
                index += 2
            case "--message":
                options.message = next
                index += 2
            case "--style":
                options.style = NoticeStyle(rawValue: next) ?? .info
                index += 2
            case "--provider-id":
                let value = next.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
                options.providerId = value.isEmpty ? "gemini" : value
                index += 2
            default:
                index += 1
            }
        }
        return options
    }
}

private func loadBuildInfo(path: String) -> BuildInfo? {
    guard !path.isEmpty else { return nil }
    let fileURL = URL(fileURLWithPath: path)
    guard let data = try? Data(contentsOf: fileURL) else { return nil }
    return try? JSONDecoder().decode(BuildInfo.self, from: data)
}

private func credentialBaseQuery(service: String, account: String) -> [String: Any] {
    return [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: service,
        kSecAttrAccount as String: account,
        kSecUseDataProtectionKeychain as String: true,
    ]
}

private func credentialBaseQuery(providerId: String) -> [String: Any] {
    let provider = providerOption(for: providerId)
    return credentialBaseQuery(service: provider.keychainService, account: provider.keychainAccount)
}

private func appSupportBaseURL() -> URL {
    FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/Voice2Code", isDirectory: true)
}

private func installSecretURL() -> URL {
    appSupportBaseURL().appendingPathComponent(".install_secret", isDirectory: false)
}

private func credentialsVaultURL() -> URL {
    appSupportBaseURL().appendingPathComponent("credentials.vault", isDirectory: false)
}

private func randomData(length: Int) -> Data {
    var bytes = [UInt8](repeating: 0, count: length)
    let status = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
    guard status == errSecSuccess else {
        return Data()
    }
    return Data(bytes)
}

private func ensureProtectedFileSystemLayout() throws {
    let fm = FileManager.default
    let baseURL = appSupportBaseURL()
    if !fm.fileExists(atPath: baseURL.path) {
        try fm.createDirectory(at: baseURL, withIntermediateDirectories: true, attributes: [
            .posixPermissions: 0o700,
        ])
    } else {
        try? fm.setAttributes([.posixPermissions: 0o700], ofItemAtPath: baseURL.path)
    }
}

private func ensureInstallSecret() throws -> Data {
    try ensureProtectedFileSystemLayout()
    let url = installSecretURL()
    let fm = FileManager.default
    if fm.fileExists(atPath: url.path) {
        return try Data(contentsOf: url)
    }
    let secret = randomData(length: 32)
    guard !secret.isEmpty else {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [
            NSLocalizedDescriptionKey: "生成本地凭据密钥失败。",
        ])
    }
    try secret.write(to: url, options: .atomic)
    try? fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
    return secret
}

private func deriveVaultKey(installSecret: Data, salt: Data) -> SymmetricKey {
    let ikm = SymmetricKey(data: installSecret)
    return HKDF<SHA256>.deriveKey(
        inputKeyMaterial: ikm,
        salt: salt,
        info: Data("Voice2Code Protected Local Vault v1".utf8),
        outputByteCount: 32
    )
}

private func loadVaultMap() -> [String: String] {
    let url = credentialsVaultURL()
    guard
        let data = try? Data(contentsOf: url),
        let envelope = try? JSONDecoder().decode(VaultEnvelope.self, from: data),
        let salt = Data(base64Encoded: envelope.salt),
        let nonce = Data(base64Encoded: envelope.nonce),
        let ciphertext = Data(base64Encoded: envelope.ciphertext),
        let tag = Data(base64Encoded: envelope.tag),
        let installSecret = try? ensureInstallSecret()
    else {
        return [:]
    }
    do {
        let sealed = try AES.GCM.SealedBox(
            nonce: AES.GCM.Nonce(data: nonce),
            ciphertext: ciphertext,
            tag: tag
        )
        let key = deriveVaultKey(installSecret: installSecret, salt: salt)
        let plain = try AES.GCM.open(sealed, using: key)
        let object = try JSONSerialization.jsonObject(with: plain) as? [String: String]
        return object ?? [:]
    } catch {
        return [:]
    }
}

private func saveVaultMap(_ map: [String: String]) throws {
    try ensureProtectedFileSystemLayout()
    let salt = randomData(length: 16)
    let key = deriveVaultKey(installSecret: try ensureInstallSecret(), salt: salt)
    let plaintext = try JSONSerialization.data(withJSONObject: map, options: [.sortedKeys])
    let sealed = try AES.GCM.seal(plaintext, using: key)
    let envelope = VaultEnvelope(
        schemaVersion: 1,
        cipher: "AES-256-GCM",
        salt: salt.base64EncodedString(),
        nonce: sealed.nonce.withUnsafeBytes { Data($0).base64EncodedString() },
        ciphertext: sealed.ciphertext.base64EncodedString(),
        tag: sealed.tag.base64EncodedString()
    )
    let url = credentialsVaultURL()
    let encoded = try JSONEncoder().encode(envelope)
    try encoded.write(to: url, options: .atomic)
    try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
}

private func loadAPIKeyFromVault(providerId: String) -> String {
    loadVaultMap()[providerId]?
        .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
}

private func saveAPIKeyToVault(providerId: String, apiKey: String) throws {
    let secret = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !secret.isEmpty else {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [
            NSLocalizedDescriptionKey: "API Key 不能为空。",
        ])
    }
    var map = loadVaultMap()
    map[providerId] = secret
    try saveVaultMap(map)
}

private func loadStoredAPIKey(providerId: String) -> String {
    var query = credentialBaseQuery(providerId: providerId)
    query[kSecReturnData as String] = true
    query[kSecMatchLimit as String] = kSecMatchLimitOne
    var item: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &item)
    if status == errSecSuccess, let data = item as? Data {
        return String(data: data, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    }
    return loadAPIKeyFromVault(providerId: providerId)
}

private func loadEnvAPIKey(providerId: String) -> String {
    let providerEnvKey = "V2C_\(providerId.trimmingCharacters(in: .whitespacesAndNewlines).uppercased())_API_KEY"
    let providerValue = ProcessInfo.processInfo.environment[providerEnvKey]?
        .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    if !providerValue.isEmpty {
        return providerValue
    }
    return ProcessInfo.processInfo.environment["V2C_API_KEY"]?
        .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
}

private func saveAPIKeyToKeychain(providerId: String, apiKey: String) throws {
    let provider = providerOption(for: providerId)
    let secret = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !secret.isEmpty else {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [
            NSLocalizedDescriptionKey: "\(provider.displayName) API Key 不能为空。",
        ])
    }
    guard let secretData = secret.data(using: .utf8) else {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [
            NSLocalizedDescriptionKey: "API Key 编码失败。",
        ])
    }
    var query = credentialBaseQuery(providerId: providerId)
    query[kSecValueData as String] = secretData

    let addStatus = SecItemAdd(query as CFDictionary, nil)
    if addStatus == errSecSuccess {
        return
    }
    guard addStatus == errSecDuplicateItem else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(addStatus), userInfo: [
            NSLocalizedDescriptionKey: "\(provider.displayName) API Key 保存失败：\((SecCopyErrorMessageString(addStatus, nil) as String?) ?? "OSStatus \(addStatus)")",
        ])
    }

    let attributesToUpdate = [kSecValueData as String: secretData] as CFDictionary
    let updateStatus = SecItemUpdate(credentialBaseQuery(providerId: providerId) as CFDictionary, attributesToUpdate)
    guard updateStatus == errSecSuccess else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(updateStatus), userInfo: [
            NSLocalizedDescriptionKey: "\(provider.displayName) API Key 更新失败：\((SecCopyErrorMessageString(updateStatus, nil) as String?) ?? "OSStatus \(updateStatus)")",
        ])
    }
}

private func deleteStoredAPIKey(providerId: String) throws {
    let status = SecItemDelete(credentialBaseQuery(providerId: providerId) as CFDictionary)
    guard status == errSecSuccess || status == errSecItemNotFound else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(status), userInfo: nil)
    }
    var map = loadVaultMap()
    map.removeValue(forKey: providerId)
    try saveVaultMap(map)
}

private func loadSecret(service: String, account: String) -> String {
    var query = credentialBaseQuery(service: service, account: account)
    query[kSecReturnData as String] = true
    query[kSecMatchLimit as String] = kSecMatchLimitOne
    var item: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &item)
    guard status == errSecSuccess, let data = item as? Data else {
        return ""
    }
    return String(data: data, encoding: .utf8)?
        .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
}

private func saveSecret(service: String, account: String, value: String) throws {
    guard let secretData = value.data(using: .utf8) else {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [NSLocalizedDescriptionKey: "Secret 编码失败。"])
    }
    var query = credentialBaseQuery(service: service, account: account)
    query[kSecValueData as String] = secretData
    let addStatus = SecItemAdd(query as CFDictionary, nil)
    if addStatus == errSecSuccess {
        return
    }
    guard addStatus == errSecDuplicateItem else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(addStatus), userInfo: nil)
    }
    let updateStatus = SecItemUpdate(
        credentialBaseQuery(service: service, account: account) as CFDictionary,
        [kSecValueData as String: secretData] as CFDictionary
    )
    guard updateStatus == errSecSuccess else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(updateStatus), userInfo: nil)
    }
}

private func deleteSecret(service: String, account: String) throws {
    let status = SecItemDelete(credentialBaseQuery(service: service, account: account) as CFDictionary)
    guard status == errSecSuccess || status == errSecItemNotFound else {
        throw NSError(domain: NSOSStatusErrorDomain, code: Int(status), userInfo: nil)
    }
}

private func runKeychainProbe(providerId: String) throws {
    let provider = providerOption(for: providerId)
    let probeService = "\(provider.keychainService).probe.\(UUID().uuidString)"
    let probeAccount = "diagnostic"
    let probeKey = "probe-\(UUID().uuidString)"
    try saveSecret(service: probeService, account: probeAccount, value: probeKey)
    let loaded = loadSecret(service: probeService, account: probeAccount)
    guard loaded == probeKey else {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [
            NSLocalizedDescriptionKey: "Keychain probe 读取失败。",
        ])
    }
    try saveSecret(service: probeService, account: probeAccount, value: "\(probeKey)-updated")
    let updated = loadSecret(service: probeService, account: probeAccount)
    guard updated == "\(probeKey)-updated" else {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [
            NSLocalizedDescriptionKey: "Keychain probe 更新失败。",
        ])
    }
    try deleteSecret(service: probeService, account: probeAccount)
    if !loadSecret(service: probeService, account: probeAccount).isEmpty {
        throw NSError(domain: "Voice2CodeInstaller", code: -1, userInfo: [
            NSLocalizedDescriptionKey: "\(provider.displayName) Keychain probe 删除失败。",
        ])
    }
}

private func loadProviderState(targetConfigPath: String, bundledConfigPath: String) -> ProviderState {
    let fm = FileManager.default
    let candidatePath: String
    if !targetConfigPath.isEmpty, fm.fileExists(atPath: targetConfigPath) {
        candidatePath = targetConfigPath
    } else {
        candidatePath = bundledConfigPath
    }
    guard
        !candidatePath.isEmpty,
        let data = try? Data(contentsOf: URL(fileURLWithPath: candidatePath)),
        let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
        let provider = root["provider"] as? [String: Any]
    else {
        let fallback = providerOption(for: "gemini")
        return ProviderState(providerId: fallback.id, intentModel: fallback.intentModel, generationModel: fallback.generationModel)
    }

    let providerId = (provider["provider_id"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() ?? "gemini"
    let providerDefaults = providerOption(for: providerId)
    let providers = provider["providers"] as? [String: Any]
    let currentProvider = providers?[providerDefaults.id] as? [String: Any]
    return ProviderState(
        providerId: providerDefaults.id,
        intentModel: (currentProvider?["intent_model"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
            ? (currentProvider?["intent_model"] as? String ?? providerDefaults.intentModel)
            : providerDefaults.intentModel,
        generationModel: (currentProvider?["generation_model"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
            ? (currentProvider?["generation_model"] as? String ?? providerDefaults.generationModel)
            : providerDefaults.generationModel
    )
}

private func loadProxyState(targetConfigPath: String, bundledConfigPath: String) -> ProxyState {
    let fm = FileManager.default
    let candidatePath: String
    if !targetConfigPath.isEmpty, fm.fileExists(atPath: targetConfigPath) {
        candidatePath = targetConfigPath
    } else {
        candidatePath = bundledConfigPath
    }
    guard
        !candidatePath.isEmpty,
        let data = try? Data(contentsOf: URL(fileURLWithPath: candidatePath)),
        let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
        let network = root["network"] as? [String: Any]
    else {
        return ProxyState(enabled: false, scheme: "http", host: "127.0.0.1", port: 7897)
    }
    let scheme = (network["proxy_scheme"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    let host = (network["proxy_host"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines)
    let port = network["proxy_port"] as? Int ?? Int("\(network["proxy_port"] ?? 7897)") ?? 7897
    let enabled = network["proxy_enabled"] as? Bool ?? false
    return ProxyState(
        enabled: enabled,
        scheme: (scheme?.isEmpty == false ? scheme! : "http"),
        host: (host?.isEmpty == false ? host! : "127.0.0.1"),
        port: port
    )
}

private func versionComponents(_ version: String) -> [Int] {
    let digits = version.split(whereSeparator: { !"0123456789".contains($0) }).compactMap { Int($0) }
    return digits.isEmpty ? [0] : digits
}

private func compareVersions(_ lhs: String, _ rhs: String) -> ComparisonResult {
    let a = versionComponents(lhs)
    let b = versionComponents(rhs)
    let count = max(a.count, b.count)
    for idx in 0..<count {
        let av = idx < a.count ? a[idx] : 0
        let bv = idx < b.count ? b[idx] : 0
        if av < bv { return .orderedAscending }
        if av > bv { return .orderedDescending }
    }
    return .orderedSame
}

private func parseBuildDate(_ value: String) -> Date? {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.dateFormat = "yyyy-MM-dd HH:mm:ss Z"
    return formatter.date(from: value)
}

private func detectVersionRelation(bundled: BuildInfo?, installed: BuildInfo?) -> VersionRelation {
    guard let installed else { return .firstInstall }
    guard
        let bundledVersion = bundled?.releaseVersion, !bundledVersion.isEmpty,
        let installedVersion = installed.releaseVersion, !installedVersion.isEmpty
    else {
        return .installedUnknown
    }

    let versionCompare = compareVersions(bundledVersion, installedVersion)
    if versionCompare == .orderedDescending { return .upgrade }
    if versionCompare == .orderedAscending { return .downgrade }

    guard
        let bundledTime = bundled?.buildTimestamp, !bundledTime.isEmpty,
        let installedTime = installed.buildTimestamp, !installedTime.isEmpty,
        let bundledDate = parseBuildDate(bundledTime),
        let installedDate = parseBuildDate(installedTime)
    else {
        return .reinstall
    }

    if bundledDate > installedDate { return .upgrade }
    if bundledDate < installedDate { return .downgrade }
    return .reinstall
}

private func versionRelationText(_ relation: VersionRelation) -> String {
    switch relation {
    case .firstInstall:
        return "首次安装"
    case .upgrade:
        return "检测到旧版本，可升级安装"
    case .reinstall:
        return "当前为同版本，将执行覆盖安装"
    case .downgrade:
        return "当前已安装更高版本，继续将执行降级覆盖"
    case .installedUnknown:
        return "已检测到已安装副本，但版本信息不完整，将允许覆盖安装"
    }
}

private func installButtonTitle(for mode: LaunchMode, relation: VersionRelation) -> String {
    switch mode {
    case .initializeConfig:
        return "保存配置"
    case .configureNetwork, .openSettings:
        return "保存"
    case .runRefine, .keychainProbe:
        return "继续"
    case .notice:
        return "关闭"
    case .install:
        switch relation {
        case .firstInstall:
            return "安装"
        case .upgrade:
            return "升级安装"
        case .reinstall:
            return "覆盖安装"
        case .downgrade, .installedUnknown:
            return "继续安装"
        }
    }
}

private func clearProxyEnvironment(_ environment: inout [String: String]) {
    for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"] {
        environment.removeValue(forKey: key)
    }
}

private func runConnectivityCheck(providerState: ProviderState, proxyState: ProxyState?, apiKey: String) -> (Bool, String) {
    let provider = providerOption(for: providerState.providerId)
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
    let payload: String
    let targetURL: String
    let headers: [String]
    switch provider.apiStyle {
    case "gemini_generate_content":
        payload = #"{"contents":[{"parts":[{"text":"ping"}]}]}"#
        targetURL = "\(provider.baseURL)/models/\(providerState.intentModel):generateContent"
        headers = ["Content-Type: application/json", "x-goog-api-key: \(apiKey)"]
    default:
        payload = #"{"model":"\#(providerState.intentModel)","messages":[{"role":"user","content":"ping"}],"response_format":{"type":"json_object"}}"#
        targetURL = "\(provider.baseURL)/chat/completions"
        headers = ["Content-Type: application/json", "Authorization: Bearer \(apiKey)"]
    }
    process.arguments = [
        "-sS", "-o", "-", "-w", "\nHTTP_CODE:%{http_code}", "-X", "POST",
        "--connect-timeout", "3", "--max-time", "8", targetURL,
    ]
    for header in headers {
        process.arguments?.append(contentsOf: ["-H", header])
    }
    process.arguments?.append(contentsOf: ["-d", payload])
    var env = ProcessInfo.processInfo.environment
    clearProxyEnvironment(&env)
    if let proxyState, proxyState.enabled {
        let proxyURL = proxyState.endpoint
        if proxyState.scheme == "socks5" {
            env["ALL_PROXY"] = proxyURL
            env["all_proxy"] = proxyURL
        }
        env["HTTP_PROXY"] = proxyURL
        env["HTTPS_PROXY"] = proxyURL
        env["http_proxy"] = proxyURL
        env["https_proxy"] = proxyURL
    }
    process.environment = env

    let output = Pipe()
    let error = Pipe()
    process.standardOutput = output
    process.standardError = error
    do {
        try process.run()
        process.waitUntilExit()
        let data = output.fileHandleForReading.readDataToEndOfFile()
        let raw = String(data: data, encoding: .utf8) ?? ""
        let marker = "\nHTTP_CODE:"
        let code: String
        let body: String
        if let range = raw.range(of: marker, options: .backwards) {
            body = String(raw[..<range.lowerBound])
            code = String(raw[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
        } else {
            body = raw
            code = ""
        }
        if process.terminationStatus == 0, code == "200" {
            return (true, "已通过 \(provider.displayName) 连通测试，可继续保存当前配置。")
        }
        let err = String(data: error.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        if !body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            let compactBody = body.replacingOccurrences(of: "\n", with: " ").prefix(220)
            return (false, "\(provider.displayName) 连通测试失败（HTTP \(code.isEmpty ? "未知" : code)）：\(compactBody)")
        }
        if !err.isEmpty {
            return (false, "\(provider.displayName) 连通测试失败：\(err.trimmingCharacters(in: .whitespacesAndNewlines))")
        }
        return (false, "\(provider.displayName) 连通测试失败，请检查网络配置或 API Key。")
    } catch {
        return (false, "\(provider.displayName) 连通测试失败：\(error.localizedDescription)")
    }
}

private func installedRootURL() -> URL {
    FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/Voice2Code/Voice2CodeRefiner", isDirectory: true)
}

private func installedRunnerURL() -> URL {
    installedRootURL().appendingPathComponent("scripts/voice2code_runner.py", isDirectory: false)
}

private func installedConfigURL() -> URL {
    installedRootURL().appendingPathComponent("config/voice2code_refiner_config.json", isDirectory: false)
}

private func loadInstalledProviderState() -> ProviderState {
    loadProviderState(targetConfigPath: installedConfigURL().path, bundledConfigPath: installedConfigURL().path)
}

private func runRefineCLI() -> Int32 {
    let inputData = FileHandle.standardInput.readDataToEndOfFile()
    guard !inputData.isEmpty else {
        return EXIT_SUCCESS
    }
    let runnerURL = installedRunnerURL()
    guard FileManager.default.fileExists(atPath: runnerURL.path) else {
        fputs("[Voice2Code App 未找到本地运行入口]\n", stderr)
        return EXIT_FAILURE
    }
    let providerState = loadInstalledProviderState()
    let apiKey = {
        let envKey = loadEnvAPIKey(providerId: providerState.providerId)
        if !envKey.isEmpty {
            return envKey
        }
        return loadStoredAPIKey(providerId: providerState.providerId)
    }()
    if apiKey.isEmpty {
        fputs("failed to resolve provider API key from environment or persisted app credential store\n", stderr)
        return EXIT_FAILURE
    }
    return runRefineProcess(
        runnerURL: runnerURL,
        inputData: inputData,
        providerState: providerState,
        apiKey: apiKey
    )
}

@discardableResult
private func runRefineProcess(
    runnerURL: URL,
    inputData: Data,
    providerState: ProviderState,
    apiKey: String
) -> Int32 {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
    process.arguments = [runnerURL.path]
    var env = ProcessInfo.processInfo.environment
    env["PYTHONIOENCODING"] = "utf-8"
    env["LANG"] = "zh_CN.UTF-8"
    env["V2C_PROVIDER"] = providerState.providerId
    env["V2C_INTENT_MODEL"] = providerState.intentModel
    env["V2C_GENERATION_MODEL"] = providerState.generationModel
    env["V2C_\(providerState.providerId.uppercased())_API_KEY"] = apiKey
    process.environment = env

    let stdinPipe = Pipe()
    let stdoutPipe = Pipe()
    let stderrPipe = Pipe()
    process.standardInput = stdinPipe
    process.standardOutput = stdoutPipe
    process.standardError = stderrPipe

    do {
        try process.run()
        stdinPipe.fileHandleForWriting.write(inputData)
        stdinPipe.fileHandleForWriting.closeFile()
        process.waitUntilExit()
        let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
        let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
        if !stdoutData.isEmpty {
            FileHandle.standardOutput.write(stdoutData)
        }
        if !stderrData.isEmpty {
            FileHandle.standardError.write(stderrData)
        }
        return process.terminationStatus
    } catch {
        fputs("failed to run Voice2Code core: \(error.localizedDescription)\n", stderr)
        return EXIT_FAILURE
    }
}

private func runRefinementSmokeTest(providerState: ProviderState, apiKey: String) -> (Bool, String) {
    let runnerURL = installedRunnerURL()
    guard FileManager.default.fileExists(atPath: runnerURL.path) else {
        return (false, "未执行（本地运行入口不可用）")
    }
    let sampleInput = "整理一下这段需求表达，让它更适合继续交给 AI 执行。"
    let inputData = sampleInput.data(using: .utf8) ?? Data()
    let outputPipe = Pipe()
    let errorPipe = Pipe()

    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
    process.arguments = [runnerURL.path]
    var env = ProcessInfo.processInfo.environment
    env["PYTHONIOENCODING"] = "utf-8"
    env["LANG"] = "zh_CN.UTF-8"
    env["V2C_PROVIDER"] = providerState.providerId
    env["V2C_INTENT_MODEL"] = providerState.intentModel
    env["V2C_GENERATION_MODEL"] = providerState.generationModel
    env["V2C_\(providerState.providerId.uppercased())_API_KEY"] = apiKey
    process.environment = env
    let stdinPipe = Pipe()
    process.standardInput = stdinPipe
    process.standardOutput = outputPipe
    process.standardError = errorPipe

    do {
        try process.run()
        stdinPipe.fileHandleForWriting.write(inputData)
        stdinPipe.fileHandleForWriting.closeFile()
        process.waitUntilExit()
        let stdoutText = String(
            data: outputPipe.fileHandleForReading.readDataToEndOfFile(),
            encoding: .utf8
        ) ?? ""
        let stderrText = String(
            data: errorPipe.fileHandleForReading.readDataToEndOfFile(),
            encoding: .utf8
        ) ?? ""
        if process.terminationStatus == 0, !stdoutText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return (true, "通过")
        }
        if !stderrText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            let compact = stderrText.replacingOccurrences(of: "\n", with: " ").prefix(160)
            return (false, "失败（不影响安装）：\(compact)")
        }
        return (false, "失败（不影响安装）")
    } catch {
        return (false, "失败（不影响安装）：\(error.localizedDescription)")
    }
}

final class InstallerWindowController: NSWindowController, NSWindowDelegate, NSTextFieldDelegate {
    private enum FlowStage {
        case editing
        case runningSmoke
        case completed
    }

    private let mode: LaunchMode
    private let resultFile: String
    private let targetConfigPath: String
    private let bundledConfigPath: String
    private let versionRelation: VersionRelation
    private let bundledBuildInfo: BuildInfo?
    private let installedBuildInfo: BuildInfo?

    private let heroIconView = NSImageView()
    private let titleLabel = NSTextField(labelWithString: "")
    private let subtitleLabel = NSTextField(labelWithString: "")
    private let relationBadgeLabel = NSTextField(labelWithString: "")
    private let relationLabel = NSTextField(labelWithString: "")
    private let bundledLabel = NSTextField(labelWithString: "")
    private let installedLabel = NSTextField(labelWithString: "")
    private let providerPopupButton = NSPopUpButton(frame: .zero, pullsDown: false)
    private let modeSegmentedControl = NSSegmentedControl(labels: ["直连", "代理"], trackingMode: .selectOne, target: nil, action: nil)
    private let endpointField = NSTextField(string: "")
    private let apiKeyField = NSSecureTextField(string: "")
    private let apiKeyHintLabel = NSTextField(labelWithString: "")
    private let hintLabel = NSTextField(labelWithString: "代理地址示例：http://127.0.0.1:7897 或 socks5://127.0.0.1:7897")
    private let statusLabel = NSTextField(labelWithString: "")
    private let installFlowLabel = NSTextField(labelWithString: "")
    private let completedSummaryLabel = NSTextField(wrappingLabelWithString: "")
    private let testButton = NSButton(title: "测试连接", target: nil, action: nil)
    private let primaryButton = NSButton(title: "", target: nil, action: nil)
    private let cancelButton = NSButton(title: "取消", target: nil, action: nil)

    private var currentProxyState: ProxyState
    private var currentProviderState: ProviderState
    private var lastTestRequested = false
    private var lastTestPassed = false
    private var hasCompleted = false
    private var persistenceWarning = ""
    private var lastSmokeRequested = false
    private var lastSmokePassed = false
    private var lastSmokeStatus = "未执行"
    private var currentStage: FlowStage = .editing
    private var completedResult: InstallerResult?
    private let endpointGroup = NSStackView()
    private let apiKeyGroup = NSStackView()
    private let hintContainer = NSView()
    private let statusContainer = NSView()
    private let networkBox = NSView()
    private let completedCard = NSView()

    init(
        mode: LaunchMode,
        resultFile: String,
        targetConfigPath: String,
        bundledConfigPath: String,
        bundledBuildInfo: BuildInfo?,
        installedBuildInfo: BuildInfo?,
        initialProxyState: ProxyState,
        initialProviderState: ProviderState
    ) {
        self.mode = mode
        self.resultFile = resultFile
        self.targetConfigPath = targetConfigPath
        self.bundledConfigPath = bundledConfigPath
        self.bundledBuildInfo = bundledBuildInfo
        self.installedBuildInfo = installedBuildInfo
        self.versionRelation = detectVersionRelation(bundled: bundledBuildInfo, installed: installedBuildInfo)
        self.currentProxyState = initialProxyState
        self.currentProviderState = initialProviderState

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 700, height: mode == .install ? 460 : 560),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.isReleasedWhenClosed = false
        window.center()
        window.title = mode == .install ? "Voice2Code 安装" : (mode == .initializeConfig ? "Voice2Code 初始化配置" : "Voice2Code 配置")
        window.titlebarAppearsTransparent = true
        window.isMovableByWindowBackground = true
        super.init(window: window)
        window.delegate = self
        buildUI()
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    private func buildUI() {
        guard let contentView = window?.contentView else { return }
        contentView.wantsLayer = true
        contentView.layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor

        let stack = NSStackView()
        stack.orientation = .vertical
        stack.spacing = 18
        stack.translatesAutoresizingMaskIntoConstraints = false

        heroIconView.image = NSImage(systemSymbolName: mode == .install ? "bolt.badge.clock.fill" : "key.radiowaves.forward.fill", accessibilityDescription: nil)
        heroIconView.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 26, weight: .semibold)
        heroIconView.contentTintColor = mode == .install ? NSColor.systemBlue : NSColor.systemTeal
        heroIconView.translatesAutoresizingMaskIntoConstraints = false
        heroIconView.setContentHuggingPriority(.required, for: .horizontal)
        heroIconView.setContentCompressionResistancePriority(.required, for: .horizontal)

        titleLabel.font = NSFont.systemFont(ofSize: 26, weight: .bold)
        titleLabel.stringValue = mode == .install ? "安装 Voice2Code Quick Action" : (mode == .initializeConfig ? "初始化 Voice2Code" : "配置 Voice2Code")

        subtitleLabel.font = NSFont.systemFont(ofSize: 13, weight: .regular)
        subtitleLabel.textColor = NSColor.secondaryLabelColor
        subtitleLabel.lineBreakMode = .byWordWrapping
        subtitleLabel.maximumNumberOfLines = 2
        subtitleLabel.stringValue = mode == .install
            ? "先完成安装。安装成功后会进入初始化配置，选择 AI Provider、录入对应 API Key、选择网络方式并完成连通测试。"
            : (mode == .initializeConfig
                ? "请完成首次初始化配置。保存前必须通过一次 Provider 连通测试。"
                : "该配置只影响 Voice2Code 当前选择的 Provider 请求链路。修改后需重新通过一次连通测试才能保存。")

        relationBadgeLabel.font = NSFont.systemFont(ofSize: 12, weight: .semibold)
        relationBadgeLabel.alignment = .center
        relationBadgeLabel.stringValue = mode == .install ? versionRelationText(versionRelation) : (mode == .initializeConfig ? "首次运行前需完成" : "仅影响 Voice2Code")

        relationLabel.font = NSFont.systemFont(ofSize: 16, weight: .semibold)
        relationLabel.textColor = NSColor.labelColor
        relationLabel.lineBreakMode = .byWordWrapping
        relationLabel.maximumNumberOfLines = 2
        relationLabel.stringValue = mode == .install
            ? installSummaryText()
            : (mode == .initializeConfig
                ? "请先配置默认 Provider、网络方式与 API Key，并在通过连通测试后保存。"
                : "你可以更新 Voice2Code 的 Provider、网络方式或 API Key。保存前必须重新通过连通测试。")

        bundledLabel.textColor = NSColor.tertiaryLabelColor
        bundledLabel.lineBreakMode = .byWordWrapping
        bundledLabel.maximumNumberOfLines = 1
        bundledLabel.font = NSFont.systemFont(ofSize: 12, weight: .regular)
        bundledLabel.stringValue = "安装包 v\(bundledBuildInfo?.releaseVersion?.replacingOccurrences(of: "v", with: "") ?? "未知") · \(bundledBuildInfo?.buildTimestamp ?? "未知")"

        installedLabel.textColor = NSColor.tertiaryLabelColor
        installedLabel.lineBreakMode = .byWordWrapping
        installedLabel.maximumNumberOfLines = 1
        installedLabel.font = NSFont.systemFont(ofSize: 12, weight: .regular)
        if let installedBuildInfo {
            installedLabel.stringValue = "已安装 v\(installedBuildInfo.releaseVersion?.replacingOccurrences(of: "v", with: "") ?? "未知") · \(installedBuildInfo.buildTimestamp ?? "未知")"
        } else {
            installedLabel.stringValue = "当前未检测到已安装副本。"
        }

        let titleStack = NSStackView(views: [titleLabel, subtitleLabel])
        titleStack.orientation = .vertical
        titleStack.spacing = 4

        let heroRow = NSStackView(views: [heroIconView, titleStack])
        heroRow.orientation = .horizontal
        heroRow.spacing = 12
        heroRow.alignment = .centerY

        let versionBox = makeCardView(background: NSColor.controlBackgroundColor.withAlphaComponent(0.38), border: NSColor.separatorColor.withAlphaComponent(0.28))
        let versionStack = NSStackView()
        versionStack.orientation = .vertical
        versionStack.spacing = 8
        versionStack.addArrangedSubview(makeBadgeContainer(for: relationBadgeLabel))
        versionStack.addArrangedSubview(relationLabel)
        if mode == .install {
            versionStack.addArrangedSubview(bundledLabel)
            versionStack.addArrangedSubview(installedLabel)
        }
        embed(versionStack, in: versionBox)

        installFlowLabel.textColor = NSColor.secondaryLabelColor
        installFlowLabel.lineBreakMode = .byWordWrapping
        installFlowLabel.maximumNumberOfLines = 3
        installFlowLabel.font = NSFont.systemFont(ofSize: 13, weight: .regular)
        installFlowLabel.stringValue = "安装只负责部署 Quick Action、本地运行文件与 Voice2Code.app。安装成功后会自动打开初始化配置窗口，继续选择 Provider、配置 API Key、网络方式并完成连通测试。"

        providerPopupButton.addItems(withTitles: providerCatalog.map { $0.displayName })
        providerPopupButton.target = self
        providerPopupButton.action = #selector(changeProvider(_:))
        if let index = providerCatalog.firstIndex(where: { $0.id == currentProviderState.providerId }) {
            providerPopupButton.selectItem(at: index)
        }

        let networkLabel = NSTextField(labelWithString: "网络方式")
        networkLabel.font = NSFont.systemFont(ofSize: 14, weight: .semibold)

        modeSegmentedControl.target = self
        modeSegmentedControl.action = #selector(toggleNetworkMode(_:))
        modeSegmentedControl.selectedSegment = currentProxyState.enabled ? 1 : 0
        modeSegmentedControl.segmentStyle = .rounded
        modeSegmentedControl.setWidth(88, forSegment: 0)
        modeSegmentedControl.setWidth(88, forSegment: 1)

        endpointField.placeholderString = "http://127.0.0.1:7897"
        endpointField.stringValue = currentProxyState.endpoint
        endpointField.font = NSFont.monospacedSystemFont(ofSize: 15, weight: .medium)
        endpointField.bezelStyle = .roundedBezel
        endpointField.delegate = self

        apiKeyField.placeholderString = "请输入 API Key"
        apiKeyField.font = NSFont.monospacedSystemFont(ofSize: 14, weight: .regular)
        apiKeyField.bezelStyle = .roundedBezel
        apiKeyField.delegate = self

        apiKeyHintLabel.textColor = NSColor.secondaryLabelColor
        apiKeyHintLabel.lineBreakMode = .byWordWrapping
        apiKeyHintLabel.maximumNumberOfLines = 2
        apiKeyHintLabel.font = NSFont.systemFont(ofSize: 12, weight: .regular)
        apiKeyHintLabel.stringValue = ""

        hintLabel.textColor = NSColor.secondaryLabelColor
        hintLabel.lineBreakMode = .byWordWrapping
        hintLabel.maximumNumberOfLines = 2
        hintLabel.font = NSFont.systemFont(ofSize: 12, weight: .regular)

        statusLabel.textColor = NSColor.secondaryLabelColor
        statusLabel.lineBreakMode = .byWordWrapping
        statusLabel.maximumNumberOfLines = 3
        statusLabel.font = NSFont.systemFont(ofSize: 13, weight: .medium)
        statusLabel.stringValue = "请先填写 API Key，并完成一次连通测试。"

        let networkStack = NSStackView()
        networkStack.orientation = .vertical
        networkStack.spacing = 12
        let providerLabel = NSTextField(labelWithString: "AI Provider")
        providerLabel.font = NSFont.systemFont(ofSize: 14, weight: .semibold)
        networkStack.addArrangedSubview(providerLabel)
        networkStack.addArrangedSubview(providerPopupButton)
        networkStack.addArrangedSubview(networkLabel)
        networkStack.addArrangedSubview(modeSegmentedControl)
        endpointGroup.orientation = .vertical
        endpointGroup.spacing = 8
        endpointGroup.addArrangedSubview(endpointField)
        endpointGroup.addArrangedSubview(hintLabel)
        networkStack.addArrangedSubview(endpointGroup)
        apiKeyGroup.orientation = .vertical
        apiKeyGroup.spacing = 8
        let apiKeyLabel = NSTextField(labelWithString: "API Key")
        apiKeyLabel.font = NSFont.systemFont(ofSize: 14, weight: .semibold)
        apiKeyGroup.addArrangedSubview(apiKeyLabel)
        apiKeyGroup.addArrangedSubview(apiKeyField)
        apiKeyGroup.addArrangedSubview(apiKeyHintLabel)
        networkStack.addArrangedSubview(apiKeyGroup)
        statusContainer.wantsLayer = true
        statusContainer.layer?.cornerRadius = 12
        statusContainer.layer?.backgroundColor = NSColor.textBackgroundColor.withAlphaComponent(0.5).cgColor
        statusContainer.translatesAutoresizingMaskIntoConstraints = false
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        statusContainer.addSubview(statusLabel)
        NSLayoutConstraint.activate([
            statusLabel.leadingAnchor.constraint(equalTo: statusContainer.leadingAnchor, constant: 12),
            statusLabel.trailingAnchor.constraint(equalTo: statusContainer.trailingAnchor, constant: -12),
            statusLabel.topAnchor.constraint(equalTo: statusContainer.topAnchor, constant: 10),
            statusLabel.bottomAnchor.constraint(equalTo: statusContainer.bottomAnchor, constant: -10),
        ])
        networkStack.addArrangedSubview(statusContainer)

        networkBox.wantsLayer = true
        networkBox.layer?.cornerRadius = 16
        networkBox.layer?.borderWidth = 1
        networkBox.layer?.borderColor = NSColor.separatorColor.withAlphaComponent(0.42).cgColor
        networkBox.layer?.backgroundColor = NSColor.controlBackgroundColor.withAlphaComponent(0.54).cgColor
        embed(networkStack, in: networkBox)

        completedCard.wantsLayer = true
        completedCard.layer?.cornerRadius = 16
        completedCard.layer?.borderWidth = 1
        completedCard.layer?.borderColor = NSColor.separatorColor.withAlphaComponent(0.42).cgColor
        completedCard.layer?.backgroundColor = NSColor.controlBackgroundColor.withAlphaComponent(0.54).cgColor
        completedSummaryLabel.maximumNumberOfLines = 0
        completedSummaryLabel.font = NSFont.systemFont(ofSize: 16, weight: .semibold)
        embed(completedSummaryLabel, in: completedCard)
        completedCard.isHidden = true

        testButton.target = self
        testButton.action = #selector(testConnection(_:))
        testButton.bezelStyle = .rounded
        testButton.setButtonType(.momentaryPushIn)
        if #available(macOS 11.0, *) {
            testButton.image = NSImage(systemSymbolName: "wave.3.right.circle", accessibilityDescription: nil)
            testButton.imagePosition = .imageLeading
        }
        primaryButton.target = self
        primaryButton.action = #selector(confirmAction(_:))
        primaryButton.title = installButtonTitle(for: mode, relation: versionRelation)
        primaryButton.bezelStyle = .rounded
        primaryButton.keyEquivalent = "\r"
        cancelButton.target = self
        cancelButton.action = #selector(cancelAction(_:))
        cancelButton.bezelStyle = .rounded

        let buttonViews: [NSView]
        if mode == .install {
            buttonViews = [cancelButton, primaryButton]
        } else {
            buttonViews = [cancelButton, testButton, primaryButton]
        }
        let buttonStack = NSStackView(views: buttonViews)
        buttonStack.orientation = .horizontal
        buttonStack.spacing = 12
        buttonStack.alignment = .centerY
        buttonStack.distribution = .fillProportionally

        stack.addArrangedSubview(heroRow)
        stack.addArrangedSubview(versionBox)
        if mode == .install {
            stack.addArrangedSubview(makeInfoStrip(for: installFlowLabel))
        } else {
            stack.addArrangedSubview(networkBox)
            stack.addArrangedSubview(completedCard)
        }
        stack.addArrangedSubview(buttonStack)

        contentView.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 28),
            stack.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -28),
            stack.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 28),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: contentView.bottomAnchor, constant: -24),
            endpointField.widthAnchor.constraint(greaterThanOrEqualToConstant: 460),
        ])

        primaryButton.contentTintColor = .white
        primaryButton.wantsLayer = true
        primaryButton.layer?.cornerRadius = 10
        primaryButton.layer?.backgroundColor = NSColor.systemBlue.cgColor
        primaryButton.layer?.borderWidth = 0
        primaryButton.layer?.masksToBounds = true
        primaryButton.heightAnchor.constraint(equalToConstant: 36).isActive = true
        cancelButton.heightAnchor.constraint(equalToConstant: 36).isActive = true
        testButton.heightAnchor.constraint(equalToConstant: 36).isActive = true

        refreshUI()
    }

    private func makeCardView(background: NSColor = NSColor.controlBackgroundColor.withAlphaComponent(0.58), border: NSColor = NSColor.separatorColor.withAlphaComponent(0.45)) -> NSView {
        let view = NSView()
        view.wantsLayer = true
        view.layer?.cornerRadius = 16
        view.layer?.borderWidth = 1
        view.layer?.borderColor = border.cgColor
        view.layer?.backgroundColor = background.cgColor
        return view
    }

    private func embed(_ child: NSView, in container: NSView) {
        child.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(child)
        NSLayoutConstraint.activate([
            child.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 18),
            child.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -18),
            child.topAnchor.constraint(equalTo: container.topAnchor, constant: 16),
            child.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -16),
        ])
    }

    private func makeBadgeContainer(for label: NSTextField) -> NSView {
        let container = NSView()
        container.wantsLayer = true
        container.layer?.cornerRadius = 11
        container.layer?.backgroundColor = badgeBackgroundColor().cgColor
        label.textColor = badgeForegroundColor()
        label.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(label)
        NSLayoutConstraint.activate([
            label.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 10),
            label.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -10),
            label.topAnchor.constraint(equalTo: container.topAnchor, constant: 5),
            label.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -5),
        ])
        return container
    }

    private func makeInfoStrip(for label: NSTextField) -> NSView {
        let container = NSView()
        container.wantsLayer = true
        container.layer?.cornerRadius = 14
        container.layer?.backgroundColor = NSColor.systemBlue.withAlphaComponent(0.08).cgColor
        container.layer?.borderWidth = 1
        container.layer?.borderColor = NSColor.systemBlue.withAlphaComponent(0.14).cgColor
        label.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(label)
        NSLayoutConstraint.activate([
            label.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 16),
            label.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -16),
            label.topAnchor.constraint(equalTo: container.topAnchor, constant: 12),
            label.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -12),
        ])
        return container
    }

    private func badgeBackgroundColor() -> NSColor {
        switch versionRelation {
        case .firstInstall:
            return NSColor.systemBlue.withAlphaComponent(0.16)
        case .upgrade:
            return NSColor.systemGreen.withAlphaComponent(0.16)
        case .reinstall:
            return NSColor.systemOrange.withAlphaComponent(0.16)
        case .downgrade:
            return NSColor.systemRed.withAlphaComponent(0.14)
        case .installedUnknown:
            return NSColor.systemGray.withAlphaComponent(0.16)
        }
    }

    private func badgeForegroundColor() -> NSColor {
        switch versionRelation {
        case .firstInstall:
            return NSColor.systemBlue
        case .upgrade:
            return NSColor.systemGreen
        case .reinstall:
            return NSColor.systemOrange
        case .downgrade:
            return NSColor.systemRed
        case .installedUnknown:
            return NSColor.secondaryLabelColor
        }
    }

    private func installSummaryText() -> String {
        switch versionRelation {
        case .firstInstall:
            return "将安装新的 Voice2Code Quick Action，并创建本地运行环境。"
        case .upgrade:
            return "已检测到旧版本安装，可直接升级到当前安装包版本。"
        case .reinstall:
            return "当前系统内已存在同版本副本，本次将执行覆盖安装。"
        case .downgrade:
            return "当前系统内存在更高版本副本；继续安装将执行降级覆盖。"
        case .installedUnknown:
            return "已检测到已安装副本，但版本信息不完整；本次允许继续覆盖安装。"
        }
    }

    private func selectedProvider() -> ProviderOption {
        let index = max(providerPopupButton.indexOfSelectedItem, 0)
        if index < providerCatalog.count {
            return providerCatalog[index]
        }
        return providerCatalog[0]
    }

    private func refreshProviderUI() {
        let provider = selectedProvider()
        currentProviderState.providerId = provider.id
        currentProviderState.intentModel = provider.intentModel
        currentProviderState.generationModel = provider.generationModel
        let hasStoredKey = !loadStoredAPIKey(providerId: provider.id).isEmpty
        apiKeyField.placeholderString = hasStoredKey ? "已配置，留空则保持不变" : "请输入 \(provider.displayName) API Key"
        apiKeyHintLabel.stringValue = hasStoredKey
            ? "当前环境已保存 \(provider.displayName) API Key。若需更换，可输入新 key；若不修改可留空。"
            : "\(provider.displayName) API Key 不会写入安装包；若当前环境支持，App 会尝试持久化保存。"
    }

    private func refreshUI() {
        networkBox.isHidden = currentStage == .completed
        completedCard.isHidden = currentStage != .completed
        if currentStage == .completed {
            testButton.isHidden = true
            cancelButton.isHidden = true
            primaryButton.isHidden = false
            primaryButton.title = "完成"
            primaryButton.isEnabled = true
            return
        }
        let proxyEnabled = modeSegmentedControl.selectedSegment == 1
        endpointField.isEnabled = proxyEnabled
        endpointGroup.isHidden = !proxyEnabled
        let requiresConnectivityTest = mode == .initializeConfig || mode == .configureNetwork
        testButton.isHidden = false
        cancelButton.isHidden = false
        testButton.isEnabled = requiresConnectivityTest
        refreshProviderUI()
        if !requiresConnectivityTest {
            return
        }
        primaryButton.isEnabled = lastTestPassed
        primaryButton.title = installButtonTitle(for: mode, relation: versionRelation)
        let providerName = selectedProvider().displayName
        if !proxyEnabled {
            statusLabel.stringValue = hasUsableAPIKey()
                ? "当前将使用直连方式。完成 \(providerName) 连通测试后才能保存。"
                : "当前将使用直连方式。请先填写 \(providerName) API Key，再进行测试。"
            statusLabel.textColor = NSColor.secondaryLabelColor
        } else if !lastTestRequested {
            statusLabel.stringValue = hasUsableAPIKey()
                ? "当前将通过代理连接。填写代理地址后，请先通过 \(providerName) 连通测试再保存。"
                : "当前将通过代理连接。请填写代理地址和 \(providerName) API Key，再进行测试。"
            statusLabel.textColor = NSColor.secondaryLabelColor
        }
    }

    private func hasUsableAPIKey() -> Bool {
        let entered = apiKeyField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        return !entered.isEmpty || !loadStoredAPIKey(providerId: selectedProvider().id).isEmpty
    }

    private func resolvedAPIKey() -> String? {
        let entered = apiKeyField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        if !entered.isEmpty {
            return entered
        }
        let stored = loadStoredAPIKey(providerId: selectedProvider().id)
        return stored.isEmpty ? nil : stored
    }

    private func resetConnectivityState() {
        lastTestRequested = false
        lastTestPassed = false
        persistenceWarning = ""
        lastSmokeRequested = false
        lastSmokePassed = false
        lastSmokeStatus = "未执行"
        currentStage = .editing
        completedResult = nil
        if mode != .install {
            primaryButton.isEnabled = false
        }
    }

    private func writeResultAndTerminate(_ result: InstallerResult) {
        guard !hasCompleted else { return }
        hasCompleted = true
        guard !resultFile.isEmpty else {
            NSApp.stop(nil)
            window?.close()
            return
        }
        do {
            let encoded = try JSONEncoder().encode(result)
            try encoded.write(to: URL(fileURLWithPath: resultFile))
        } catch {
            fputs("failed to write installer result: \(error)\n", stderr)
            NSApp.terminate(nil)
            return
        }
        NSApp.stop(nil)
        window?.close()
    }

    private func buildInstallerResult(confirmed: Bool, installAction: String, message: String) -> InstallerResult {
        InstallerResult(
            mode: mode.rawValue,
            confirmed: confirmed,
            providerId: selectedProvider().id,
            proxyEnabled: currentProxyState.enabled,
            proxyScheme: currentProxyState.scheme,
            proxyHost: currentProxyState.host,
            proxyPort: currentProxyState.port,
            apiKeyConfigured: !loadStoredAPIKey(providerId: selectedProvider().id).isEmpty,
            testRequested: lastTestRequested,
            testPassed: lastTestPassed,
            smokeRequested: lastSmokeRequested,
            smokePassed: lastSmokePassed,
            smokeStatus: lastSmokeStatus,
            installAction: installAction,
            versionRelation: versionRelation.rawValue,
            message: message
        )
    }

    private func enterRunningSmokeStage() {
        currentStage = .runningSmoke
        statusLabel.stringValue = "正在执行安装后转写烟测..."
        statusLabel.textColor = NSColor.secondaryLabelColor
        primaryButton.isEnabled = false
        cancelButton.isEnabled = false
        testButton.isEnabled = false
        providerPopupButton.isEnabled = false
        modeSegmentedControl.isEnabled = false
        endpointField.isEnabled = false
        apiKeyField.isEnabled = false
        window?.displayIfNeeded()
    }

    private func completedSummaryText(result: InstallerResult) -> String {
        let providerName = selectedProvider().displayName
        let networkMessage = currentProxyState.enabled ? "代理：\(currentProxyState.endpoint)" : "直连"
        let apiKeyStatus = result.apiKeyConfigured ? "已配置" : (lastTestPassed ? "当前会话已验证（未持久化）" : "未配置")
        let releaseVersion = bundledBuildInfo?.releaseVersion ?? installedBuildInfo?.releaseVersion ?? "未知"
        let buildTimestamp = bundledBuildInfo?.buildTimestamp ?? installedBuildInfo?.buildTimestamp ?? "未知"
        let workflowPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Services/AI提纯指令.workflow", isDirectory: true).path
        let appPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Applications/Voice2Code.app", isDirectory: true).path
        return """
程序已安装：已完成
Quick Action 已注册：已注册
转写烟测：\(result.smokeStatus)

当前已安装版本：\(releaseVersion)
当前已安装构建时间：\(buildTimestamp)
当前 AI Provider：\(providerName)
当前网络方式：\(networkMessage)
API Key：\(apiKeyStatus)

App 路径：
\(appPath)

Quick Action 路径：
\(workflowPath)
"""
    }

    private func enterCompletedStage(result: InstallerResult) {
        currentStage = .completed
        completedResult = result
        titleLabel.stringValue = "Voice2Code 安装完成"
        subtitleLabel.stringValue = "当前操作已经完成。"
        relationBadgeLabel.stringValue = "已可开始使用"
        relationLabel.stringValue = result.smokePassed
            ? "初始化配置与自动转写烟测均已完成。"
            : "初始化配置已完成，自动转写烟测未通过，但不影响后续继续使用。"
        completedSummaryLabel.stringValue = completedSummaryText(result: result)
        primaryButton.title = "完成"
        primaryButton.isEnabled = true
        refreshUI()
    }

    private func parseCurrentProxyState() -> ProxyState? {
        if modeSegmentedControl.selectedSegment == 0 {
            return ProxyState(enabled: false, scheme: "http", host: "127.0.0.1", port: 7897)
        }

        let text = endpointField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, let components = URLComponents(string: text) else {
            statusLabel.stringValue = "代理地址不能为空。"
            statusLabel.textColor = NSColor.systemRed
            return nil
        }
        guard let scheme = components.scheme?.lowercased(), ["http", "https", "socks5"].contains(scheme) else {
            statusLabel.stringValue = "代理地址协议只支持 http / https / socks5。"
            statusLabel.textColor = NSColor.systemRed
            return nil
        }
        guard let host = components.host, !host.isEmpty, let port = components.port else {
            statusLabel.stringValue = "代理地址必须包含主机和端口。"
            statusLabel.textColor = NSColor.systemRed
            return nil
        }
        return ProxyState(enabled: true, scheme: scheme, host: host, port: port)
    }

    @objc private func toggleNetworkMode(_ sender: NSButton) {
        resetConnectivityState()
        refreshUI()
    }

    private func resolvedTargetConfigPath() -> String {
        let trimmed = targetConfigPath.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            return trimmed
        }
        return installedConfigURL().path
    }

    private func resolvedBundledConfigPath() -> String {
        let trimmed = bundledConfigPath.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            return trimmed
        }
        return resolvedTargetConfigPath()
    }

    private func persistConfiguration(apiKeyConfigured: Bool) throws {
        let targetPath = resolvedTargetConfigPath()
        let bundledPath = resolvedBundledConfigPath()
        let targetURL = URL(fileURLWithPath: targetPath)
        let bundledURL = URL(fileURLWithPath: bundledPath)
        let fm = FileManager.default

        var root: [String: Any]
        if fm.fileExists(atPath: targetPath),
           let data = try? Data(contentsOf: targetURL),
           let parsed = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            root = parsed
        } else if fm.fileExists(atPath: bundledPath),
                  let data = try? Data(contentsOf: bundledURL),
                  let parsed = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            root = parsed
        } else {
            root = [:]
        }

        let provider = selectedProvider()
        root["provider"] = [
            "provider_id": provider.id,
            "providers": [
                provider.id: [
                    "intent_model": currentProviderState.intentModel,
                    "generation_model": currentProviderState.generationModel,
                ],
            ],
        ]
        root["network"] = [
            "proxy_enabled": currentProxyState.enabled,
            "proxy_scheme": currentProxyState.scheme,
            "proxy_host": currentProxyState.host,
            "proxy_port": currentProxyState.port,
        ]
        var credentials = (root["credentials"] as? [String: Any]) ?? [:]
        var configuredProviders = (credentials["configured_providers"] as? [String: Any]) ?? [:]
        configuredProviders[provider.id] = apiKeyConfigured
        credentials["configured_providers"] = configuredProviders
        credentials["gemini_api_key_configured"] = configuredProviders["gemini"] as? Bool ?? false
        root["credentials"] = credentials

        try fm.createDirectory(at: targetURL.deletingLastPathComponent(), withIntermediateDirectories: true, attributes: nil)
        var data = try JSONSerialization.data(withJSONObject: root, options: [.prettyPrinted, .sortedKeys])
        data.append(0x0A)
        try data.write(to: targetURL, options: .atomic)
    }

    @objc private func changeProvider(_ sender: Any?) {
        resetConnectivityState()
        refreshUI()
    }

    func controlTextDidChange(_ obj: Notification) {
        resetConnectivityState()
        refreshUI()
    }

    @objc private func testConnection(_ sender: Any?) {
        guard let proxyState = parseCurrentProxyState() else { return }
        guard let apiKey = resolvedAPIKey(), !apiKey.isEmpty else {
            statusLabel.stringValue = "请先填写 \(selectedProvider().displayName) API Key。若当前系统已保存 key，也可留空并直接测试。"
            statusLabel.textColor = NSColor.systemRed
            return
        }
        currentProxyState = proxyState
        lastTestRequested = true
        statusLabel.stringValue = "正在测试 \(selectedProvider().displayName) 连通性..."
        statusLabel.textColor = NSColor.secondaryLabelColor
        testButton.isEnabled = false
        primaryButton.isEnabled = false
        cancelButton.isEnabled = false
        DispatchQueue.global(qos: .userInitiated).async {
            let result = runConnectivityCheck(providerState: self.currentProviderState, proxyState: proxyState.enabled ? proxyState : nil, apiKey: apiKey)
            DispatchQueue.main.async {
                self.lastTestPassed = result.0
                self.statusLabel.stringValue = result.1
                self.statusLabel.textColor = result.0 ? NSColor.systemGreen : NSColor.systemRed
                self.testButton.isEnabled = true
                self.primaryButton.isEnabled = result.0 || self.mode == .install
                self.cancelButton.isEnabled = true
            }
        }
    }

    @objc private func confirmAction(_ sender: Any?) {
        if currentStage == .completed, let result = completedResult {
            writeResultAndTerminate(result)
            return
        }
        guard let proxyState = parseCurrentProxyState() else { return }
        currentProxyState = proxyState
        let enteredApiKey = apiKeyField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let effectiveAPIKey = resolvedAPIKey()
        if mode == .initializeConfig || mode == .configureNetwork {
            guard effectiveAPIKey != nil else {
                statusLabel.stringValue = "请先填写 \(selectedProvider().displayName) API Key。"
                statusLabel.textColor = NSColor.systemRed
                return
            }
            guard lastTestRequested && lastTestPassed else {
                statusLabel.stringValue = "保存前必须先通过一次 \(selectedProvider().displayName) 连通测试。"
                statusLabel.textColor = NSColor.systemRed
                return
            }
            if !enteredApiKey.isEmpty {
                do {
                    try saveAPIKeyToKeychain(providerId: selectedProvider().id, apiKey: enteredApiKey)
                } catch {
                    do {
                        try saveAPIKeyToVault(providerId: selectedProvider().id, apiKey: enteredApiKey)
                    } catch {
                        persistenceWarning = "\(selectedProvider().displayName) API Key 未能完成持久化保存。你仍可通过环境变量继续使用。"
                    }
                }
            }
            let persistedAPIKeyAvailable = !loadStoredAPIKey(providerId: selectedProvider().id).isEmpty
            do {
                try persistConfiguration(apiKeyConfigured: persistedAPIKeyAvailable)
            } catch {
                statusLabel.stringValue = "保存配置文件失败：\(error.localizedDescription)"
                statusLabel.textColor = NSColor.systemRed
                return
            }
            if mode == .configureNetwork {
                let finalMessage = !persistenceWarning.isEmpty ? persistenceWarning : "配置已保存。"
                if !persistenceWarning.isEmpty {
                    statusLabel.textColor = NSColor.systemOrange
                } else {
                    statusLabel.textColor = NSColor.systemGreen
                }
                writeResultAndTerminate(self.buildInstallerResult(
                    confirmed: true,
                    installAction: "save",
                    message: finalMessage
                ))
                return
            }
            enterRunningSmokeStage()
            let providerState = currentProviderState
            let smokeAPIKey = effectiveAPIKey ?? ""
            DispatchQueue.global(qos: .userInitiated).async {
                let smoke = runRefinementSmokeTest(
                    providerState: providerState,
                    apiKey: smokeAPIKey
                )
                DispatchQueue.main.async {
                    self.lastSmokeRequested = true
                    self.lastSmokePassed = smoke.0
                    self.lastSmokeStatus = smoke.1
                    let finalMessage: String
                    if !self.persistenceWarning.isEmpty {
                        finalMessage = self.persistenceWarning
                    } else {
                        finalMessage = smoke.0 ? "配置已保存，安装后烟测已通过。" : "配置已保存，但安装后烟测未通过。"
                    }
                    let result = self.buildInstallerResult(
                        confirmed: true,
                        installAction: self.mode == .install ? "install" : "save",
                        message: finalMessage
                    )
                    self.enterCompletedStage(result: result)
                }
            }
            return
        }
        writeResultAndTerminate(buildInstallerResult(
            confirmed: true,
            installAction: (mode == .install ? "install" : "save"),
            message: statusLabel.stringValue
        ))
    }

    @objc private func cancelAction(_ sender: Any?) {
        if currentStage == .completed {
            if let result = completedResult {
                writeResultAndTerminate(result)
            } else {
                writeResultAndTerminate(buildInstallerResult(
                    confirmed: false,
                    installAction: "cancel",
                    message: "用户取消了当前操作。"
                ))
            }
            return
        }
        writeResultAndTerminate(buildInstallerResult(
            confirmed: false,
            installAction: "cancel",
            message: "用户取消了当前操作。"
        ))
    }

    func windowWillClose(_ notification: Notification) {
        if !hasCompleted, NSApp.isRunning {
            cancelAction(nil)
        }
    }
}

final class NoticeWindowController: NSWindowController, NSWindowDelegate {
    private let titleText: String
    private let messageText: String
    private let style: NoticeStyle

    init(title: String, message: String, style: NoticeStyle) {
        self.titleText = title
        self.messageText = message
        self.style = style
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 520, height: 220),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.title = title
        window.center()
        super.init(window: window)
        window.delegate = self
        buildUI()
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    private func buildUI() {
        guard let contentView = window?.contentView else { return }
        contentView.wantsLayer = true
        contentView.layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.spacing = 18
        stack.translatesAutoresizingMaskIntoConstraints = false

        let iconView = NSImageView()
        iconView.image = NSImage(systemSymbolName: style == .error ? "xmark.octagon.fill" : "checkmark.seal.fill", accessibilityDescription: nil)
        iconView.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 30, weight: .semibold)
        iconView.contentTintColor = style == .error ? NSColor.systemRed : NSColor.systemGreen
        iconView.setContentHuggingPriority(.required, for: .horizontal)

        let titleLabel = NSTextField(labelWithString: titleText)
        titleLabel.font = NSFont.systemFont(ofSize: 22, weight: .bold)
        titleLabel.textColor = style == .error ? NSColor.systemRed : NSColor.labelColor

        let subtitleLabel = NSTextField(labelWithString: style == .error ? "本次操作没有完整完成。" : "当前操作已经完成。")
        subtitleLabel.font = NSFont.systemFont(ofSize: 13, weight: .regular)
        subtitleLabel.textColor = NSColor.secondaryLabelColor

        let headerText = NSStackView(views: [titleLabel, subtitleLabel])
        headerText.orientation = .vertical
        headerText.spacing = 4

        let heroRow = NSStackView(views: [iconView, headerText])
        heroRow.orientation = .horizontal
        heroRow.spacing = 12
        heroRow.alignment = .centerY

        let messageLabel = NSTextField(wrappingLabelWithString: messageText)
        messageLabel.maximumNumberOfLines = 0
        messageLabel.font = NSFont.systemFont(ofSize: 14, weight: .regular)

        let messageCard = NSView()
        messageCard.wantsLayer = true
        messageCard.layer?.cornerRadius = 16
        messageCard.layer?.borderWidth = 1
        messageCard.layer?.borderColor = NSColor.separatorColor.withAlphaComponent(0.32).cgColor
        messageCard.layer?.backgroundColor = NSColor.controlBackgroundColor.withAlphaComponent(0.52).cgColor
        messageLabel.translatesAutoresizingMaskIntoConstraints = false
        messageCard.addSubview(messageLabel)
        NSLayoutConstraint.activate([
            messageLabel.leadingAnchor.constraint(equalTo: messageCard.leadingAnchor, constant: 16),
            messageLabel.trailingAnchor.constraint(equalTo: messageCard.trailingAnchor, constant: -16),
            messageLabel.topAnchor.constraint(equalTo: messageCard.topAnchor, constant: 16),
            messageLabel.bottomAnchor.constraint(equalTo: messageCard.bottomAnchor, constant: -16),
        ])

        let closeButton = NSButton(title: "关闭", target: self, action: #selector(closeAction(_:)))
        closeButton.bezelStyle = .rounded
        closeButton.keyEquivalent = "\r"
        closeButton.heightAnchor.constraint(equalToConstant: 36).isActive = true

        stack.addArrangedSubview(heroRow)
        stack.addArrangedSubview(messageCard)
        stack.addArrangedSubview(closeButton)

        contentView.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -24),
            stack.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 24),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: contentView.bottomAnchor, constant: -24),
        ])
    }

    @objc private func closeAction(_ sender: Any?) {
        NSApp.stop(nil)
        window?.close()
    }

    func windowWillClose(_ notification: Notification) {
        NSApp.stop(nil)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let options: LaunchOptions
    private var controller: NSWindowController?

    init(options: LaunchOptions) {
        self.options = options
    }

    private func buildMainMenu() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu()
        let appName = "Voice2Code"
        appMenu.addItem(withTitle: "关于 \(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "隐藏 \(appName)", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let hideOthers = NSMenuItem(title: "隐藏其他", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(hideOthers)
        appMenu.addItem(withTitle: "显示全部", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "退出 \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appMenuItem.submenu = appMenu

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "编辑")
        editMenu.addItem(withTitle: "撤销", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "重做", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "剪切", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "复制", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "粘贴", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "全选", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editMenuItem.submenu = editMenu

        NSApp.mainMenu = mainMenu
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMainMenu()
        switch options.mode {
        case .install, .initializeConfig, .configureNetwork, .openSettings:
            let bundledBuildInfo = loadBuildInfo(path: options.bundledBuildInfoPath)
            let installedBuildInfo = loadBuildInfo(path: options.installedBuildInfoPath)
            let initialProxyState = loadProxyState(targetConfigPath: options.targetConfigPath, bundledConfigPath: options.bundledConfigPath)
            let initialProviderState = loadProviderState(targetConfigPath: options.targetConfigPath, bundledConfigPath: options.bundledConfigPath)
            controller = InstallerWindowController(
                mode: options.mode == .openSettings ? .configureNetwork : options.mode,
                resultFile: options.resultFile,
                targetConfigPath: options.targetConfigPath,
                bundledConfigPath: options.bundledConfigPath,
                bundledBuildInfo: bundledBuildInfo,
                installedBuildInfo: installedBuildInfo,
                initialProxyState: initialProxyState,
                initialProviderState: initialProviderState
            )
        case .runRefine, .keychainProbe:
            NSApp.terminate(nil)
        case .notice:
            controller = NoticeWindowController(title: options.title, message: options.message, style: options.style)
        }
        controller?.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

let options = LaunchOptions.parse(from: Array(CommandLine.arguments.dropFirst()))
if options.mode == .runRefine {
    exit(runRefineCLI())
}
if options.mode == .keychainProbe {
    do {
        try runKeychainProbe(providerId: options.providerId)
        fputs("ok\n", stdout)
        exit(EXIT_SUCCESS)
    } catch {
        fputs("failed to complete Keychain probe: \(error.localizedDescription)\n", stderr)
        exit(EXIT_FAILURE)
    }
}
let app = NSApplication.shared
app.setActivationPolicy(.regular)
let delegate = AppDelegate(options: options)
app.delegate = delegate
app.run()
