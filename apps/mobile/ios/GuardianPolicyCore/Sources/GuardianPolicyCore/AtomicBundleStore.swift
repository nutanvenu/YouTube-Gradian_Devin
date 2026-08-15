import Foundation

public final class AtomicBundleStore {
  private let directory: URL
  private let fileManager: FileManager

  public init(directory: URL, fileManager: FileManager = .default) {
    self.directory = directory
    self.fileManager = fileManager
  }

  public func apply(bundle: JSONValue, version: Int) throws {
    try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
    let pending = directory.appendingPathComponent("policy.pending")
    let active = directory.appendingPathComponent("policy.active")
    let backup = directory.appendingPathComponent("policy.previous")
    let data = try bundle.canonicalData()
    try data.write(to: pending, options: .atomic)
    if fileManager.fileExists(atPath: active.path) {
      try? fileManager.removeItem(at: backup)
      try fileManager.moveItem(at: active, to: backup)
    }
    do {
      try fileManager.moveItem(at: pending, to: active)
      try Data(String(version).utf8).write(to: directory.appendingPathComponent("applied-version"), options: .atomic)
    } catch {
      try? fileManager.removeItem(at: active)
      if fileManager.fileExists(atPath: backup.path) {
        try? fileManager.moveItem(at: backup, to: active)
      }
      throw error
    }
  }
}
