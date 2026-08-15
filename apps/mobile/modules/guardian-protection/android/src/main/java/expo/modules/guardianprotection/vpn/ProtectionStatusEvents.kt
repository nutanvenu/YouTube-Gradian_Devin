package expo.modules.guardianprotection.vpn

import java.util.concurrent.atomic.AtomicReference

internal data class ProtectionStatusChange(
  val active: Boolean,
  val details: String?,
)

internal object ProtectionStatusTransition {
  fun shouldEmit(previous: Boolean?, current: Boolean): Boolean =
    previous == null || previous != current
}

internal object ProtectionStatusEvents {
  private val listener = AtomicReference<((ProtectionStatusChange) -> Unit)?>(null)
  private val lastActive = AtomicReference(false)

  fun setListener(value: ((ProtectionStatusChange) -> Unit)?) {
    listener.set(value)
  }

  fun emit(active: Boolean, details: String? = null) {
    val previous = lastActive.getAndSet(active)
    if (!ProtectionStatusTransition.shouldEmit(previous, active)) return
    listener.get()?.invoke(ProtectionStatusChange(active, details))
  }
}
