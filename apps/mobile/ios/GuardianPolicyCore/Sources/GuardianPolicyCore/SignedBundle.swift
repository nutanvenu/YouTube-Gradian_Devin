import CryptoKit
import Foundation

public struct SignedBundleVerifier {
  public let trustedKeys: [String: Curve25519.Signing.PublicKey]

  public init(trustedKeys: [String: Data]) throws {
    self.trustedKeys = try trustedKeys.mapValues(Curve25519.Signing.PublicKey.init(rawRepresentation:))
  }

  public func verify(_ bundle: JSONValue) throws -> JSONValue {
    guard let object = bundle.objectValue,
          let keyID = object["key_id"]?.stringValue,
          let signatureText = object["signature"]?.stringValue,
          let signature = Data(base64Encoded: signatureText),
          let key = trustedKeys[keyID] else {
      throw BundleVerificationError.untrustedKey
    }
    var unsigned = object
    unsigned.removeValue(forKey: "signature")
    let canonical = try JSONValue.object(unsigned).canonicalData()
    guard key.isValidSignature(signature, for: canonical) else {
      throw BundleVerificationError.invalidSignature
    }
    return bundle
  }
}

public enum BundleVerificationError: Error {
  case untrustedKey
  case invalidSignature
}
