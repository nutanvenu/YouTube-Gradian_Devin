import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { validateReleaseAdmission } from "./release-admission.mjs";
import {
  verifyArtifactManifestTree,
  verifyMergedManifest,
} from "./verify-release-artifact.mjs";

const validPublicKey = Buffer.alloc(32, 7).toString("base64");

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
    GUARDIAN_POLICY_KEY_ID: "guardian-prod-2026-01",
    GUARDIAN_RELEASE_VERSION_CODE: "42",
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
  assert.ok(
    errors.some((error) => error.includes("GUARDIAN_RELEASE_VERSION_CODE")),
  );
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

test("mobile admission does not receive backend-only secrets", async () => {
  const errors = validateReleaseAdmission({
    ...(await validEnvironment()),
    GUARDIAN_JWT_SECRET: "",
    GUARDIAN_POLICY_PRIVATE_KEY: "",
    GUARDIAN_ENVIRONMENT: "",
  });
  assert.deepEqual(errors, []);
});

test("release admission requires the active strict-base64 trust anchor", async () => {
  const environment = await validEnvironment();
  const missingActive = validateReleaseAdmission({
    ...environment,
    GUARDIAN_POLICY_KEY_ID: "guardian-prod-2026-02",
  });
  assert.ok(
    missingActive.some((error) => error.includes("active trust-anchor")),
  );
  const nonCanonicalBase64 = validateReleaseAdmission({
    ...environment,
    GUARDIAN_POLICY_TRUSTED_PUBLIC_KEYS: JSON.stringify({
      "guardian-prod-2026-01": `${validPublicKey}\n`,
    }),
  });
  assert.ok(nonCanonicalBase64.some((error) => error.includes("trust-anchor")));
});

test("release admission rejects every supported fixture truthy value", async () => {
  const environment = await validEnvironment();
  for (const truthyValue of ["true", "TRUE", "1", "yes", "on"]) {
    const errors = validateReleaseAdmission({
      ...environment,
      GUARDIAN_ENABLE_TEST_FIXTURES: truthyValue,
    });
    assert.ok(
      errors.some((error) => error.includes("fixture")),
      truthyValue,
    );
  }
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
  assert.match(buildFile, /verifyGuardianReleaseArtifact/);
  assert.match(buildFile, /GUARDIAN_RELEASE_VERSION_CODE/);
  assert.match(buildFile, /output\.versionCode\.set/);
  assert.match(buildFile, /java\.security\.KeyStore\.getInstance/);
  assert.match(buildFile, /assemble\|bundle\|package\|sign/);
  assert.match(
    buildFile,
    /task\.name in \["assembleRelease", "packageRelease"\].*finalizedBy/,
  );
  assert.doesNotMatch(
    buildFile,
    /GUARDIAN_(?:JWT_SECRET|POLICY_PRIVATE_KEY|ENVIRONMENT)/,
  );
  const admission = await readFile(
    new URL("./release-admission.mjs", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(
    admission,
    /GUARDIAN_(?:JWT_SECRET|POLICY_PRIVATE_KEY|ENVIRONMENT)/,
  );
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
  assert.match(
    manifest,
    /android:name="isMonitoringTool" android:value="child_monitoring"/,
  );
  assert.match(networkSecurity, /cleartextTrafficPermitted="false"/);
  assert.match(accessibility, /android:canRetrieveWindowContent="false"/);
  assert.doesNotMatch(
    manifest,
    /android\.permission\.(?:ACCESS_FINE_LOCATION|ACCESS_COARSE_LOCATION|RECORD_AUDIO|READ_SMS|QUERY_ALL_PACKAGES)/,
  );
});

test("debug cleartext override is narrowly limited while release stays disabled", async () => {
  const debugManifest = await readFile(
    new URL("../android/app/src/debug/AndroidManifest.xml", import.meta.url),
    "utf8",
  );
  const debugNetworkSecurity = await readFile(
    new URL(
      "../android/app/src/debug/res/xml/network_security_config.xml",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(debugManifest, /android:usesCleartextTraffic="true"/);
  assert.match(
    debugManifest,
    /android:networkSecurityConfig="@xml\/network_security_config"/,
  );
  for (const host of ["localhost", "127.0.0.1", "10.0.2.2"]) {
    assert.match(debugNetworkSecurity, new RegExp(`<domain>${host}</domain>`));
  }
  assert.doesNotMatch(
    debugNetworkSecurity,
    /<base-config cleartextTrafficPermitted="true"/,
  );
});

test("merged-manifest policy verifier rejects prohibited release policy", () => {
  const invalidManifest = `
    <manifest xmlns:android="http://schemas.android.com/apk/res/android">
      <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
      <application android:allowBackup="true" android:usesCleartextTraffic="true" />
    </manifest>`;
  const errors = verifyMergedManifest(invalidManifest);
  assert.ok(errors.some((error) => error.includes("allowBackup")));
  assert.ok(errors.some((error) => error.includes("Cleartext")));
  assert.ok(errors.some((error) => error.includes("ACCESS_FINE_LOCATION")));
  assert.ok(errors.some((error) => error.includes("isMonitoringTool")));
});

test("APK manifest-tree policy verifier requires false backup and cleartext values", () => {
  const tree = `
    E: manifest
      E: application
        A: android:allowBackup(0x01010080)=(type 0x12)0xffffffff
        A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0xffffffff`;
  const errors = verifyArtifactManifestTree(tree);
  assert.ok(errors.some((error) => error.includes("allowBackup")));
  assert.ok(errors.some((error) => error.includes("usesCleartextTraffic")));
});

test("the mobile API client has no production placeholder endpoint", async () => {
  const client = await readFile(
    new URL("../src/api/client.ts", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(client, /api\.guardian\.example/);
  assert.match(client, /require an explicitly configured HTTPS API URL/);
});
