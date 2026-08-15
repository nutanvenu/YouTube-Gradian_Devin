package expo.modules.guardianprotection

internal object CapabilityStateComparison {
  fun changedCapabilities(
    previous: Map<String, Map<String, Any?>>?,
    current: Map<String, Map<String, Any?>>,
  ): Set<String> {
    if (previous == null) return emptySet()

    return (previous.keys + current.keys)
      .filter { meaningfulState(previous[it]) != meaningfulState(current[it]) }
      .toSet()
  }

  private fun meaningfulState(status: Map<String, Any?>?): MeaningfulState =
    MeaningfulState(
      level = status?.get("level"),
      detail = status?.get("detail"),
    )

  private data class MeaningfulState(
    val level: Any?,
    val detail: Any?,
  )
}
