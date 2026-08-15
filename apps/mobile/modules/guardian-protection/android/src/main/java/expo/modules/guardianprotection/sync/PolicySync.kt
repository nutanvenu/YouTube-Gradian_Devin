package expo.modules.guardianprotection.sync

interface PolicySync {
  suspend fun syncCurrentPolicy(): Long?
}
