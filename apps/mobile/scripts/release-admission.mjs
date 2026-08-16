import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PLACEHOLDER_PATTERN =
  /(?:^|[._/-])(example|invalid|localhost|127\.0\.0\.1|0\.0\.0\.0|change[-_ ]?me|replace[-_ ]?me|placeholder|fixture|test)(?:$|[._/-])/i;
const WEAK_SECRET_PATTERN =
  /change[-_ ]?me|replace|placeholder|fixture|development|example|secret(?:$|[-_ ]?secret)/i;
const DEBUG_SIGNING_PATTERN =
  /debug\.keystore|androiddebugkey|cn\s*=\s*android debug/i;

function value(environment, name) {
  const configured = environment[name];
  return typeof configured === "string" ? configured.trim() : "";
}

function isPlaceholder(valueToCheck) {
  return !valueToCheck || PLACEHOLDER_PATTERN.test(valueToCheck);
}

function validateHttpsUrl(raw, label, errors) {
  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== "https:" || isPlaceholder(parsed.hostname)) {
      errors.push(`${label} must be a non-placeholder HTTPS URL.`);
    }
  } catch {
    errors.push(`${label} must be a non-placeholder HTTPS URL.`);
  }
}

function validateTrustedKeys(raw, errors) {
  if (!raw) {
    errors.push(
      "GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS must contain at least one trusted policy public key.",
    );
    return;
  }
  try {
    const keys = JSON.parse(raw);
    if (
      !keys ||
      Array.isArray(keys) ||
      typeof keys !== "object" ||
      Object.keys(keys).length === 0
    ) {
      throw new Error("empty object");
    }
    for (const [keyId, encodedKey] of Object.entries(keys)) {
      const decoded =
        typeof encodedKey === "string"
          ? Buffer.from(encodedKey, "base64")
          : Buffer.alloc(0);
      if (
        isPlaceholder(keyId) ||
        typeof encodedKey !== "string" ||
        isPlaceholder(encodedKey) ||
        decoded.length !== 32
      ) {
        throw new Error("invalid anchor");
      }
    }
  } catch {
    errors.push(
      "GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS must be a non-empty production Ed25519 trust-anchor JSON object.",
    );
  }
}

function validateBackendSecrets(environment, errors) {
  const jwtSecret = value(environment, "GUARDIAN_JWT_SECRET");
  if (jwtSecret.length < 32 || WEAK_SECRET_PATTERN.test(jwtSecret)) {
    errors.push(
      "GUARDIAN_JWT_SECRET must be a non-placeholder production secret of at least 32 characters.",
    );
  }
  const privateKey = value(environment, "GUARDIAN_POLICY_PRIVATE_KEY");
  const decodedPrivateKey = Buffer.from(privateKey, "base64");
  if (isPlaceholder(privateKey) || decodedPrivateKey.length !== 32) {
    errors.push(
      "GUARDIAN_POLICY_PRIVATE_KEY must be a non-placeholder base64-encoded 32-byte Ed25519 private key.",
    );
  }
  const keyId = value(environment, "GUARDIAN_POLICY_KEY_ID");
  if (isPlaceholder(keyId)) {
    errors.push(
      "GUARDIAN_POLICY_KEY_ID must identify a production policy signing key.",
    );
  }
  if (value(environment, "GUARDIAN_ENVIRONMENT") !== "production") {
    errors.push("GUARDIAN_ENVIRONMENT must be exactly production.");
  }
}

/**
 * Returns deterministic, non-secret diagnostics suitable for CI and Gradle.
 * It deliberately validates backend secrets without emitting them or making
 * them available to the application build configuration.
 */
export function validateReleaseAdmission(environment = process.env) {
  const errors = [];
  const storeFile = value(environment, "GUARDIAN_RELEASE_STORE_FILE");
  const storePassword = value(environment, "GUARDIAN_RELEASE_STORE_PASSWORD");
  const keyAlias = value(environment, "GUARDIAN_RELEASE_KEY_ALIAS");
  const keyPassword = value(environment, "GUARDIAN_RELEASE_KEY_PASSWORD");

  if (!storeFile || !existsSync(storeFile)) {
    errors.push(
      "GUARDIAN_RELEASE_STORE_FILE must name an existing non-debug signing keystore.",
    );
  }
  if (
    DEBUG_SIGNING_PATTERN.test(storeFile) ||
    DEBUG_SIGNING_PATTERN.test(keyAlias)
  ) {
    errors.push("Release builds must not use debug signing material.");
  }
  for (const [name, configured] of Object.entries({
    GUARDIAN_RELEASE_STORE_PASSWORD: storePassword,
    GUARDIAN_RELEASE_KEY_ALIAS: keyAlias,
    GUARDIAN_RELEASE_KEY_PASSWORD: keyPassword,
  })) {
    if (!configured || isPlaceholder(configured))
      errors.push(`${name} must be explicitly configured for release signing.`);
  }

  validateHttpsUrl(
    value(environment, "EXPO_PUBLIC_API_URL"),
    "Release API URL",
    errors,
  );
  validateHttpsUrl(
    value(environment, "GUARDIAN_DOH_URL"),
    "Release DoH URL",
    errors,
  );
  validateTrustedKeys(
    value(environment, "GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS"),
    errors,
  );
  validateBackendSecrets(environment, errors);
  if (
    value(environment, "GUARDIAN_ENABLE_TEST_FIXTURES").toLowerCase() === "true"
  ) {
    errors.push("Release admission forbids fixture code.");
  }
  return errors;
}

function main() {
  const errors = validateReleaseAdmission();
  if (errors.length === 0) {
    process.stdout.write("Guardian release admission passed.\n");
    return;
  }
  process.stderr.write(
    `Guardian release admission failed:\n${errors.map((error) => `- ${error}`).join("\n")}\n`,
  );
  process.exitCode = 1;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1])
  main();
