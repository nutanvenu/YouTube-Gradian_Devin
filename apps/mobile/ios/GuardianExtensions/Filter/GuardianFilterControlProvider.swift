import NetworkExtension

final class GuardianFilterControlProvider: NEFilterControlProvider {
  override func startFilter(completionHandler: @escaping (Error?) -> Void) {
    completionHandler(nil)
  }

  override func stopFilter(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) {
    completionHandler()
  }
}
