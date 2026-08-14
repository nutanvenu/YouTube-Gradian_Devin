package expo.modules.guardianprotection.flow

interface FlowAttribution {
  fun packageNamesForFlow(flow: String): Set<String>
}
