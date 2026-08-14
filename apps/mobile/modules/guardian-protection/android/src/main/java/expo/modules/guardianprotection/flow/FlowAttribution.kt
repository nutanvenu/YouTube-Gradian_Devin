package expo.modules.guardianprotection.flow

import android.content.Context
import android.net.ConnectivityManager
import android.os.Build
import java.net.InetSocketAddress

interface FlowAttribution {
  fun packageNamesForFlow(flow: String): Set<String>
}

class AndroidFlowAttribution(private val context: Context) : FlowAttribution {
  private val connectivity by lazy { context.getSystemService(ConnectivityManager::class.java) }
  private val packageManager by lazy { context.packageManager }

  override fun packageNamesForFlow(flow: String): Set<String> {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return emptySet()
    val parts = flow.split("|")
    if (parts.size != 5) return emptySet()
    val protocol = parts[0].toIntOrNull() ?: return emptySet()
    val source = endpoint(parts[1]) ?: return emptySet()
    val destination = endpoint(parts[2]) ?: return emptySet()
    val uid = runCatching {
      connectivity.getConnectionOwnerUid(protocol, source, destination)
    }.getOrDefault(-1)
    if (uid < 0) return emptySet()
    return packageManager.getPackagesForUid(uid)?.toSet().orEmpty()
  }

  private fun endpoint(value: String): InetSocketAddress? {
    val separator = value.lastIndexOf(':')
    if (separator <= 0 || separator == value.lastIndex) return null
    val address = value.substring(0, separator).removePrefix("[").removeSuffix("]")
    val port = value.substring(separator + 1).toIntOrNull() ?: return null
    return InetSocketAddress(address, port)
  }
}
