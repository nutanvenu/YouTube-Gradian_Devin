package expo.modules.guardianprotection.vpn

internal data class ProtectionStatusChange(
  val active: Boolean,
  val details: String?,
)

internal class ProtectionStatusReplay {
  private var current: ProtectionStatusChange? = null
  private var listener: ((ProtectionStatusChange) -> Unit)? = null

  @Synchronized
  fun setListener(value: ((ProtectionStatusChange) -> Unit)?) {
    listener = value
    if (value != null) current?.let(value)
  }

  @Synchronized
  fun emit(change: ProtectionStatusChange) {
    if (!ProtectionStatusTransition.shouldEmit(current?.active, change.active)) return
    current = change
    listener?.invoke(change)
  }
}

internal object ProtectionStatusTransition {
  fun shouldEmit(previous: Boolean?, current: Boolean): Boolean =
    previous == null || previous != current
}

internal object ProtectionStatusEvents {
  private val replay = ProtectionStatusReplay()

  fun setListener(value: ((ProtectionStatusChange) -> Unit)?) {
    replay.setListener(value)
  }

  fun emit(active: Boolean, details: String? = null) {
    replay.emit(ProtectionStatusChange(active, details))
  }
}
