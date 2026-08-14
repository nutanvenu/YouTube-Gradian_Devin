package expo.modules.guardianprotection.inventory

class NewAppDetector(private val known: MutableSet<String> = linkedSetOf()) {
  @Synchronized
  fun newPackages(packages: List<String>): List<String> {
    val newPackages = packages.filter { it.isNotBlank() && known.add(it) }
    return newPackages
  }
}
