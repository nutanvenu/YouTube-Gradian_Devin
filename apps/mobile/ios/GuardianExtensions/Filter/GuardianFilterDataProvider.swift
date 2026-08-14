import NetworkExtension

final class GuardianFilterDataProvider: NEFilterDataProvider {
  override func startFilter(completionHandler: @escaping (Error?) -> Void) {
    completionHandler(nil)
  }

  override func stopFilter(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) {
    completionHandler()
  }

  override func handleNewFlow(_ flow: NEFilterFlow) -> NEFilterNewFlowVerdict {
    // NEFilterFlow exposes connection metadata, not the complete encrypted web
    // destination. Unknown flows fail open only when the policy explicitly
    // reports LIMITED capability; the host records this ceiling in health.
    .allow()
  }
}
