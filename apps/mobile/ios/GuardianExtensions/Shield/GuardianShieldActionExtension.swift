import ManagedSettings

final class GuardianShieldActionExtension: ShieldActionDelegate {
  override func handle(_ action: ShieldAction, for application: ApplicationToken, completionHandler: @escaping (ShieldActionResponse) -> Void) {
    complete(action, completionHandler: completionHandler)
  }

  override func handle(_ action: ShieldAction, for webDomain: WebDomain, completionHandler: @escaping (ShieldActionResponse) -> Void) {
    complete(action, completionHandler: completionHandler)
  }

  private func complete(_ action: ShieldAction, completionHandler: @escaping (ShieldActionResponse) -> Void) {
    switch action {
    case .primaryButtonPressed:
      completionHandler(.close)
    case .secondaryButtonPressed:
      // The request-more-time handoff is persisted to the App Group by the host
      // app after the shield closes; extensions do not receive bearer credentials.
      completionHandler(.defer)
    default:
      completionHandler(.none)
    }
  }
}
