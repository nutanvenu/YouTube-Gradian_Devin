import ExpoModulesCore
import FamilyControls
import Foundation
import ManagedSettings
import GuardianPolicyCore

public final class GuardianProtectionModule: Module {
  private let authorization = FamilyControlsAuthorization()
  private let store = GuardianManagedSettingsStore()
  private let shared = GuardianSharedStore()

  public func definition() -> ModuleDefinition {
    Name("GuardianProtection")
    Events("onGuardianEvent")

    AsyncFunction("getCapabilities") {
      self.authorization.capabilities()
    }
    AsyncFunction("getProtectionStatus") {
      self.shared.status()
    }
    AsyncFunction("requestFamilyControlsAuthorization") { (member: String) async throws -> [String: Any] in
      try await self.authorization.request(member: member)
      return self.authorization.capabilities()
    }
    AsyncFunction("applyPolicyBundle") { (bundle: [String: Any]) throws -> [String: Any] in
      try self.store.apply(bundle: bundle)
      return [
        "policy_version": bundle["policy_version"] ?? NSNull(),
        "acknowledged": true,
        "capability": "LIMITED",
        "details": "The signed snapshot is persisted. App tokens selected through FamilyActivityPicker are required before app shields can be applied.",
      ]
    }
    AsyncFunction("getUsageSummary") { (_: [String: Any]) -> [String: Any] in
      self.shared.usageSummary()
    }
    AsyncFunction("getObservedApps") {
      self.shared.observedApps()
    }
    Function("openUsageAccessSettings") {}
    Function("openAccessibilitySettings") {}
    Function("openNotificationAccessSettings") {}
    Function("requestVpnPermission") { ["state": "UNAVAILABLE", "detail": "iOS uses Network Extension entitlement and Family Controls authorization."] }
    Function("startProtection") {}
    Function("stopProtection") {}
  }
}

private final class FamilyControlsAuthorization {
  func request(member: String) async throws {
    let selected: FamilyControlsMember = member == "child" ? .child : .individual
    try await AuthorizationCenter.shared.requestAuthorization(for: selected)
  }

  func capabilities() -> [String: Any] {
    let status = AuthorizationCenter.shared.authorizationStatus
    let authorized = status == .approved
    return [
      "family_controls": [
        "level": authorized ? "FULL" : "UNAVAILABLE",
        "detail": authorized ? NSNull() : "Guardian authorization is required in Family Sharing.",
      ],
      "managed_settings": [
        "level": authorized ? "LIMITED" : "UNAVAILABLE",
        "detail": authorized ? "App, category and selected web restrictions are available." : "Managed Settings cannot apply controls before authorization.",
      ],
      "device_activity": [
        "level": authorized ? "LIMITED" : "UNAVAILABLE",
        "detail": authorized ? "Device Activity schedules run through the extension." : "Device Activity requires Family Controls authorization.",
      ],
      "web_filtering": [
        "level": "LIMITED",
        "detail": "iOS filtering is limited to Network Extension flows and Managed Settings web domains; it cannot provide Android-style packet attribution.",
      ],
    ]
  }
}

private final class GuardianManagedSettingsStore {
  private let managed = ManagedSettingsStore()
  private let defaults = UserDefaults(suiteName: "group.com.guardian.family")!

  func apply(bundle: [String: Any]) throws {
    guard JSONSerialization.isValidJSONObject(bundle) else {
      throw NSError(domain: "GuardianProtection", code: 1, userInfo: [
        NSLocalizedDescriptionKey: "Policy bundle is not valid JSON"
      ])
    }
    let data = try JSONSerialization.data(withJSONObject: bundle, options: [])
    defaults.set(data, forKey: "policy.signedBundle")
    defaults.set(bundle["policy_version"] as? Int, forKey: "policy.appliedVersion")
    defaults.set("LIMITED", forKey: "protection.health")
    defaults.set(
      "Managed Settings app shields require authorized ApplicationToken values; raw Guardian app refs remain pending token mapping.",
      forKey: "protection.details"
    )
    // Apple docs: a filter policy can only express system web categories or
    // WebDomain tokens. Guardian preserves explicit domain rules in the signed
    // snapshot and does not silently widen them into an all-web block.
    managed.webContent.blockedByFilter = .none
  }
}

private final class GuardianSharedStore {
  private let defaults = UserDefaults(suiteName: "group.com.guardian.family")!

  func status() -> [String: Any] {
    [
      "active": defaults.bool(forKey: "protection.active"),
      "health": defaults.string(forKey: "protection.health") ?? "UNKNOWN",
      "details": defaults.string(forKey: "protection.details") ?? "No iOS capability report is available.",
    ]
  }

  func usageSummary() -> [String: Any] {
    [
      "byTarget": defaults.dictionary(forKey: "usage.byTarget") ?? [:],
      "deviceSeconds": defaults.integer(forKey: "usage.deviceSeconds"),
    ]
  }

  func observedApps() -> [[String: Any]] {
    defaults.array(forKey: "inventory.apps") as? [[String: Any]] ?? []
  }
}
