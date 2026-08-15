package expo.modules.guardianprotection.policy

import java.lang.StringBuilder

object CanonicalJson {
  fun unsignedBytes(bundle: Map<String, Any?>): ByteArray =
    encode(bundle.filterKeys { it != "signature" }).toByteArray(Charsets.UTF_8)

  fun encode(value: Any?): String = when (value) {
    null -> "null"
    is Boolean -> value.toString()
    is Number -> {
      val long = value.toLong()
      require(value.toDouble() == long.toDouble()) { "Only integer JSON numbers are supported" }
      require(long in -(1L shl 53) + 1..(1L shl 53) - 1) { "JSON number exceeds safe integer range" }
      long.toString()
    }
    is String -> quote(value)
    is List<*> -> value.joinToString(prefix = "[", postfix = "]", separator = ",", transform = ::encode)
    is Map<*, *> -> value.entries
      .sortedWith { left, right ->
        compareUtf16(
          left.key as? String ?: error("JSON object keys must be strings"),
          right.key as? String ?: error("JSON object keys must be strings"),
        )
      }
      .joinToString(prefix = "{", postfix = "}", separator = ",") {
        quote(it.key as String) + ":" + encode(it.value)
      }
    else -> error("Unsupported JSON value: ${value::class.java.name}")
  }

  private fun quote(value: String): String {
    val out = StringBuilder("\"")
    var index = 0
    while (index < value.length) {
      val character = value[index]
      if (character.isHighSurrogate()) {
        require(index + 1 < value.length && value[index + 1].isLowSurrogate()) {
          "Lone surrogate is not valid canonical JSON"
        }
        out.append(character).append(value[index + 1])
        index += 2
        continue
      }
      require(!character.isLowSurrogate()) { "Lone surrogate is not valid canonical JSON" }
      when (character) {
        '"' -> out.append("\\\"")
        '\\' -> out.append("\\\\")
        '\b' -> out.append("\\b")
        '\u000C' -> out.append("\\f")
        '\n' -> out.append("\\n")
        '\r' -> out.append("\\r")
        '\t' -> out.append("\\t")
        else -> if (character.code < 0x20) out.append("\\u%04x".format(character.code)) else out.append(character)
      }
      index += 1
    }
    return out.append('"').toString()
  }

  private fun compareUtf16(left: String, right: String): Int {
    val leftBytes = left.toByteArray(Charsets.UTF_16BE)
    val rightBytes = right.toByteArray(Charsets.UTF_16BE)
    for (index in 0 until minOf(leftBytes.size, rightBytes.size)) {
      val comparison = (leftBytes[index].toInt() and 0xff) - (rightBytes[index].toInt() and 0xff)
      if (comparison != 0) return comparison
    }
    return leftBytes.size - rightBytes.size
  }
}
