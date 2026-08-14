import Foundation

public struct PolicyBundleAcknowledgement: Equatable, Sendable {
  public let version: Int
  public let accepted: Bool
  public let capabilityCeiling: String
}

public final class PolicyBundlePipeline {
  private let verifier: SignedBundleVerifier
  private let store: AtomicBundleStore

  public init(verifier: SignedBundleVerifier, store: AtomicBundleStore) {
    self.verifier = verifier
    self.store = store
  }

  public func apply(_ bundle: JSONValue) throws -> PolicyBundleAcknowledgement {
    let verified = try verifier.verify(bundle)
    guard let object = verified.objectValue,
          object["schema_version"]?.intValue == 1,
          let version = object["policy_version"]?.intValue,
          object["family_id"]?.stringValue != nil,
          object["child_profile_id"]?.stringValue != nil else {
      throw PolicyBundleError.invalidSchema
    }
    _ = try GuardianPolicyEvaluator.evaluate(
      bundle: verified,
      context: .object([
        "target": .object(["kind": .string("APP"), "ref": .string("com.guardian.health")]),
        "timestamp": .string(ISO8601DateFormatter().string(from: Date())),
        "usage": .object(["device_seconds_today": .number(0)]),
      ])
    )
    try store.apply(bundle: verified, version: version)
    return PolicyBundleAcknowledgement(version: version, accepted: true, capabilityCeiling: "LIMITED")
  }
}

public enum PolicyBundleError: Error {
  case invalidSchema
}
