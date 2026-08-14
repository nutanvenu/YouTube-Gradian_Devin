package expo.modules.guardianprotection.inventory

class NewAppDetector(
  private val known: MutableSet<String> = linkedSetOf(),
  private val pending: MutableSet<String> = linkedSetOf(),
) {
  @Synchronized
  fun newPackages(packages: List<String>): List<String> {
    packages
      .filter { it.isNotBlank() && !known.contains(it) && !pending.contains(it) }
      .forEach { pending.add(it) }
    known.addAll(packages.filter { it.isNotBlank() })
    return packages.filter { pending.contains(it) }
  }

  @Synchronized
  fun markReviewed(packageName: String) {
    pending.remove(packageName)
  }

  fun knownPackages(): Set<String> = known.toSet()

  fun pendingPackages(): Set<String> = pending.toSet()
}
