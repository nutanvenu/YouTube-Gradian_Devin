package expo.modules.guardianprotection.communication

import java.util.concurrent.atomic.AtomicReference
import java.util.concurrent.ConcurrentHashMap

object CommunicationSafetyRuntime {
  private val listener = AtomicReference<((CommunicationRiskSignal, String) -> Unit)?>(null)
  @Volatile private var enabled = false
  private val lastEmittedAt = ConcurrentHashMap<String, Long>()
  private val emittedWindow = ConcurrentHashMap<String, ArrayDeque<Long>>()
  private const val DEDUPE_WINDOW_MS = 10 * 60 * 1000L
  private const val RATE_WINDOW_MS = 15 * 60 * 1000L
  private const val RATE_LIMIT = 3

  fun setListener(value: ((CommunicationRiskSignal, String) -> Unit)?) {
    listener.set(value)
  }

  fun setEnabled(value: Boolean) {
    enabled = value
    if (!value) {
      lastEmittedAt.clear()
      emittedWindow.clear()
    }
  }

  fun processNotification(
    packageName: String,
    title: String?,
    text: String?,
    notificationCategory: String?,
    channelId: String?,
    nowMillis: Long = System.currentTimeMillis(),
  ) {
    if (!enabled) return
    val keyContext = CommunicationNotificationContext(packageName, notificationCategory, channelId)
    val signal = CommunicationRiskDetector.classify(title, text, keyContext) ?: return
    val key = "$packageName|${signal.category}|${signal.reasonCode}"
    val recent = emittedWindow.computeIfAbsent(key) { ArrayDeque() }
    synchronized(recent) {
      while (recent.isNotEmpty() && nowMillis - recent.first() > RATE_WINDOW_MS) recent.removeFirst()
      if (recent.size >= RATE_LIMIT) return
      if (lastEmittedAt[key]?.let { nowMillis - it <= DEDUPE_WINDOW_MS } == true) return
      recent.addLast(nowMillis)
      lastEmittedAt[key] = nowMillis
    }
    listener.get()?.invoke(signal, packageName)
  }
}
