import Foundation

public enum JSONValue: Equatable, Sendable {
  case null
  case bool(Bool)
  case number(Int)
  case string(String)
  case array([JSONValue])
  case object([String: JSONValue])

  public init(_ value: Any) throws {
    switch value {
    case is NSNull:
      self = .null
    case let value as Bool:
      self = .bool(value)
    case let value as NSNumber:
      guard value.doubleValue.rounded() == value.doubleValue,
            value.doubleValue <= Double(Int.max),
            value.doubleValue >= Double(Int.min) else {
        throw JSONValueError.nonInteger
      }
      self = .number(value.intValue)
    case let value as String:
      self = .string(value)
    case let value as [Any]:
      self = .array(try value.map(JSONValue.init))
    case let value as [String: Any]:
      var object: [String: JSONValue] = [:]
      for (key, item) in value {
        object[key] = try JSONValue(item)
      }
      self = .object(object)
    default:
      throw JSONValueError.unsupported
    }
  }

  public init(data: Data) throws {
    try self.init(JSONSerialization.jsonObject(with: data))
  }

  public var stringValue: String? {
    guard case let .string(value) = self else { return nil }
    return value
  }

  public var intValue: Int? {
    guard case let .number(value) = self else { return nil }
    return value
  }

  public var boolValue: Bool? {
    guard case let .bool(value) = self else { return nil }
    return value
  }

  public var objectValue: [String: JSONValue]? {
    guard case let .object(value) = self else { return nil }
    return value
  }

  public var arrayValue: [JSONValue]? {
    guard case let .array(value) = self else { return nil }
    return value
  }

  public subscript(_ key: String) -> JSONValue? {
    objectValue?[key]
  }

  public func canonicalData() throws -> Data {
    Data(canonicalString().utf8)
  }

  private func canonicalString() -> String {
    switch self {
    case .null:
      return "null"
    case let .bool(value):
      return value ? "true" : "false"
    case let .number(value):
      return String(value)
    case let .string(value):
      return Self.escape(value)
    case let .array(values):
      return "[\(values.map { $0.canonicalString() }.joined(separator: ","))]"
    case let .object(values):
      return "{\(values.keys.sorted().map { "\(Self.escape($0)):\(values[$0]!.canonicalString())" }.joined(separator: ","))}"
    }
  }

  private static func escape(_ value: String) -> String {
    let data = try! JSONSerialization.data(withJSONObject: [value])
    let encoded = String(decoding: data, as: UTF8.self)
    return String(encoded.dropFirst().dropLast())
  }
}

public enum JSONValueError: Error {
  case nonInteger
  case unsupported
}
