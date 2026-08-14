package expo.modules.guardianprotection.vpn

import java.net.InetAddress

internal class BlockedDestinationRoutes(
  private val maxEntries: Int = 1024,
) {
  private val entries = linkedMapOf<String, Long>()

  @Synchronized
  fun add(address: InetAddress, expiresAtMillis: Long, nowMillis: Long = System.currentTimeMillis()): Boolean {
    prune(nowMillis)
    val key = address.hostAddress ?: return false
    if (!entries.containsKey(key) && entries.size >= maxEntries) return false
    val changed = entries[key] != expiresAtMillis
    entries[key] = expiresAtMillis
    return changed
  }

  @Synchronized
  fun prune(nowMillis: Long = System.currentTimeMillis()): Boolean {
    val before = entries.size
    entries.entries.removeIf { it.value <= nowMillis }
    return before != entries.size
  }

  @Synchronized
  fun addresses(nowMillis: Long = System.currentTimeMillis()): List<InetAddress> {
    prune(nowMillis)
    return entries.keys.mapNotNull { runCatching { InetAddress.getByName(it) }.getOrNull() }
  }

  @Synchronized
  fun contains(address: InetAddress, nowMillis: Long = System.currentTimeMillis()): Boolean {
    prune(nowMillis)
    val key = address.hostAddress ?: return false
    return entries.containsKey(key)
  }

  @Synchronized
  fun clear() {
    entries.clear()
  }
}
