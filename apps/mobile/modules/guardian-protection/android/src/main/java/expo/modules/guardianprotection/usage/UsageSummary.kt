package expo.modules.guardianprotection.usage

internal fun deviceTotalSeconds(byTarget: Map<String, Long>): Long = byTarget["DEVICE"] ?: 0L
