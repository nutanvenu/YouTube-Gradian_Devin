import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { validateReleaseAdmission } from "./release-admission.mjs";

const validPublicKey = Buffer.alloc(32, 7).toString("base64");
const validPrivateKey = Buffer.alloc(32, 9).toString("base64");

async function validEnvironment() {
  const directory = await mkdtemp(
    join(tmpdir(), "guardian-release-admission-"),
  );
  const storeFile = join(directory, "guardian-release.jks");
  await writeFile(storeFile, "ephemeral-validation-keystore");
  return {
    EXPO_PUBLIC_API_URL: "https://api.guardian.family",
    GUARDIAN_DOH_URL: "https://dns.guardian.family/dns-query",
    GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS: JSON.stringify({
      "guardian-prod-2026-01": validPublicKey,
    }),
    GUARDIAN_RELEASE_STORE_FILE: storeFile,
    GUARDIAN_RELEASE_STORE_PASSWORD: "validation-store-password",
    GUARDIAN_RELEASE_KEY_ALIAS: "guardian-release",
    GUARDIAN_RELEASE_KEY_PASSWORD: "validation-key-password",
    GUARDIAN_JWT_SECRET:
      "a-production-validation-secret-with-at-least-32-bytes",
    GUARDIAN_POLICY_PRIVATE_KEY: validPrivateKey,
    GUARDIAN_POLICY_KEY_ID: "guardian-prod-2026-01",
    GUARDIAN_ENVIRONMENT: "production",
  };
}

test("release admission fails closed when the required configuration is absent", () => {
  const errors = validateReleaseAdmission({});
  assert.ok(errors.some((error) => error.includes("Release API URL")));
  assert.ok(
    errors.some((error) =>
      error.includes("GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS"),
    ),
  );
  assert.ok(
    errors.some((error) => error.includes("GUARDIAN_RELEASE_STORE_FILE")),
  );
  assert.ok(errors.some((error) => error.includes("GUARDIAN_JWT_SECRET")));
});

test("release admission rejects debug signing and fixture mode", async () => {
  const environment = await validEnvironment();
  const errors = validateReleaseAdmission({
    ...environment,
    GUARDIAN_RELEASE_STORE_FILE: "android/app/debug.keystore",
    GUARDIAN_RELEASE_KEY_ALIAS: "androiddebugkey",
    GUARDIAN_ENABLE_TEST_FIXTURES: "true",
  });
  assert.ok(errors.some((error) => error.includes("debug signing")));
  assert.ok(errors.some((error) => error.includes("fixture")));
});

test("release admission rejects empty trust anchors and placeholder endpoints", async () => {
  const environment = await validEnvironment();
  const errors = validateReleaseAdmission({
    ...environment,
    EXPO_PUBLIC_API_URL: "https://api.guardian.example",
    GUARDIAN_DOH_URL: "http://localhost:8053/dns-query",
    GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS: "{}",
  });
  assert.ok(errors.some((error) => error.includes("API URL")));
  assert.ok(errors.some((error) => error.includes("DoH URL")));
  assert.ok(errors.some((error) => error.includes("trust-anchor")));
});

test("release admission accepts a complete non-debug validation configuration", async () => {
  const errors = validateReleaseAdmission(await validEnvironment());
  assert.deepEqual(errors, []);
});

test("Android release sources declare SDK 36, no debug signing, and fail-closed admission", async () => {
  const buildFile = await readFile(
    new URL("../android/app/build.gradle", import.meta.url),
    "utf8",
  );
  const moduleBuildFile = await readFile(
    new URL(
      "../modules/guardian-protection/android/build.gradle",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(buildFile, /compileSdk 36/);
  assert.match(buildFile, /targetSdkVersion 36/);
  assert.match(buildFile, /signingConfig signingConfigs\.release/);
  assert.match(buildFile, /verifyGuardianReleaseAdmission/);
  assert.match(moduleBuildFile, /GUARDIAN_NON_RELEASE_FIXTURES_ENABLED/);
});

test("release manifest is private by default and declares transparent monitoring only", async () => {
  const manifest = await readFile(
    new URL("../android/app/src/main/AndroidManifest.xml", import.meta.url),
    "utf8",
  );
  const networkSecurity = await readFile(
    new URL(
      "../android/app/src/main/res/xml/network_security_config.xml",
      import.meta.url,
    ),
    "utf8",
  );
  const accessibility = await readFile(
    new URL(
      "../modules/guardian-protection/android/src/main/res/xml/guardian_accessibility_service.xml",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(manifest, /android:allowBackup="false"/);
  assert.match(manifest, /android:usesCleartextTraffic="false"/);
  assert.match(
    manifest,
    /android:networkSecurityConfig="@xml\/network_security_config"/,
  );
  assert.match(manifest, /com\.guardian\.family\.CHILD_MONITORING_DISCLOSURE/);
  assert.match(manifest, /com\.guardian\.family\.ACCESSIBILITY_DECLARATION/);
  assert.match(manifest, /com\.guardian\.family\.VPN_DECLARATION/);
  assert.match(networkSecurity, /cleartextTrafficPermitted="false"/);
  assert.match(accessibility, /android:canRetrieveWindowContent="false"/);
  assert.doesNotMatch(
    manifest,
    /android\.permission\.(?:ACCESS_FINE_LOCATION|ACCESS_COARSE_LOCATION|RECORD_AUDIO|READ_SMS|QUERY_ALL_PACKAGES)/,
  );
});

test("the mobile API client has no production placeholder endpoint", async () => {
  const client = await readFile(
    new URL("../src/api/client.ts", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(client, /api\.guardian\.example/);
  assert.match(client, /require an explicitly configured HTTPS API URL/);
});
