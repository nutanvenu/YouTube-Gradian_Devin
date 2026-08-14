import DeviceActivity
import Foundation

final class GuardianDeviceActivityMonitor: DeviceActivityMonitor {
  private let defaults = UserDefaults(suiteName: "group.com.guardian.family")!

  override func intervalDidStart(for activity: DeviceActivityName) {
    defaults.set(Date().timeIntervalSince1970, forKey: "routine.\(activity.rawValue).startedAt")
    defaults.set(true, forKey: "routine.\(activity.rawValue).active")
  }

  override func intervalDidEnd(for activity: DeviceActivityName) {
    defaults.set(false, forKey: "routine.\(activity.rawValue).active")
  }

  override func intervalWillStartWarning(for activity: DeviceActivityName) {}
  override func intervalWillEndWarning(for activity: DeviceActivityName) {}
}
