package expo.modules.guardianprotection.dns

interface DnsPolicyPath {
  fun classify(domain: String): String?
}
