package expo.modules.guardianprotection.communication

import java.util.concurrent.atomic.AtomicReference

object CommunicationSafetyRuntime {
  private val listener = AtomicReference<((CommunicationRiskSignal, String) -> Unit)?>(null)

  fun setListener(value: ((CommunicationRiskSignal, String) -> Unit)?) {
    listener.set(value)
  }

  fun processNotification(packageName: String, title: String?, text: String?) {
    val signal = CommunicationRiskDetector.classify(title, text) ?: return
    listener.get()?.invoke(signal, packageName)
  }
}
