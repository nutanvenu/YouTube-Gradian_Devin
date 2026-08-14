import ManagedSettings
import ManagedSettingsUI
import UIKit

final class GuardianShieldConfigurationExtension: ShieldConfigurationDataSource {
  override func configuration(shielding application: Application) -> ShieldConfiguration {
    configuration()
  }

  override func configuration(shielding application: ApplicationToken) -> ShieldConfiguration {
    configuration()
  }

  override func configuration(shielding webDomain: WebDomain) -> ShieldConfiguration {
    configuration()
  }

  private func configuration() -> ShieldConfiguration {
    ShieldConfiguration(
      backgroundBlurStyle: .systemMaterial,
      backgroundColor: .systemBackground,
      icon: UIImage(systemName: "hourglass"),
      title: "This app is unavailable right now.",
      subtitle: "Your time limit or routine applies. Ask a parent to change the limit or routine if you need more time.",
      primaryButtonLabel: "RETURN",
      primaryButtonBackgroundColor: .secondarySystemBackground,
      secondaryButtonLabel: "ASK FOR MORE TIME"
    )
  }
}
