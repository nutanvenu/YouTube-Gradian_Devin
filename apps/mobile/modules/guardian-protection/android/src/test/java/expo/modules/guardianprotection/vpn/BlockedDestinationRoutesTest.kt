package expo.modules.guardianprotection.vpn

import java.net.InetAddress
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BlockedDestinationRoutesTest {
  @Test
  fun expiresEntriesAndBoundsDynamicSet() {
    val routes = BlockedDestinationRoutes(maxEntries = 1)
    val first = InetAddress.getByName("192.0.2.1")
    val second = InetAddress.getByName("2001:db8::1")

    assertTrue(routes.add(first, 2_000, nowMillis = 1_000))
    assertFalse(routes.add(second, 3_000, nowMillis = 1_000))
    assertTrue(routes.contains(first, nowMillis = 1_999))
    assertFalse(routes.contains(first, nowMillis = 2_000))
    assertTrue(routes.add(second, 3_000, nowMillis = 2_000))
    assertEquals(listOf(second), routes.addresses(nowMillis = 2_000))
  }
}
