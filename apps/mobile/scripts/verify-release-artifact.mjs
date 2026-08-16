import { existsSync, readFileSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const PROHIBITED_PERMISSIONS = [
  "ACCESS_FINE_LOCATION",
  "ACCESS_COARSE_LOCATION",
  "RECORD_AUDIO",
  "READ_SMS",
  "QUERY_ALL_PACKAGES",
];
const REQUIRED_SERVICES = [
  "GuardianVpnService",
  "GuardianAccessibilityService",
  "GuardianNotificationListenerService",
];
const REQUIRED_METADATA = {
  isMonitoringTool: "child_monitoring",
  "com.guardian.family.CHILD_MONITORING_DISCLOSURE": undefined,
  "com.guardian.family.ACCESSIBILITY_DECLARATION": undefined,
  "com.guardian.family.VPN_DECLARATION": undefined,
};

function applicationTag(xml) {
  return xml.match(/<application\b[^>]*>/)?.[0] ?? "";
}

function metadataTag(xml, name) {
  return Array.from(xml.matchAll(/<meta-data\b[^>]*>/g)).find((tag) =>
    tag[0].includes(`android:name="${name}"`),
  )?.[0];
}

export function verifyMergedManifest(xml) {
  const errors = [];
  const application = applicationTag(xml);
  if (!/android:allowBackup="false"/.test(application)) {
    errors.push("Release merged manifest must set android:allowBackup=false.");
  }
  if (!/android:usesCleartextTraffic="false"/.test(application)) {
    errors.push(
      "Release merged manifest must set android:usesCleartextTraffic=false.",
    );
  }
  for (const [name, requiredValue] of Object.entries(REQUIRED_METADATA)) {
    const metadata = metadataTag(xml, name);
    if (
      !metadata ||
      (requiredValue && !metadata.includes(`android:value="${requiredValue}"`))
    ) {
      errors.push(
        name === "isMonitoringTool"
          ? "Release merged manifest must declare isMonitoringTool=child_monitoring."
          : `Release merged manifest is missing required metadata ${name}.`,
      );
    }
  }
  for (const service of REQUIRED_SERVICES) {
    if (!xml.includes(service))
      errors.push(`Release merged manifest is missing ${service}.`);
  }
  for (const permission of PROHIBITED_PERMISSIONS) {
    if (xml.includes(`android.permission.${permission}`)) {
      errors.push(
        `Release merged manifest contains prohibited permission ${permission}.`,
      );
    }
  }
  if (/fixture/i.test(xml))
    errors.push(
      "Release merged manifest must not contain fixture declarations.",
    );
  return errors;
}

export function verifyArtifactManifestTree(tree) {
  const errors = [];
  for (const attribute of ["allowBackup", "usesCleartextTraffic"]) {
    const line = tree
      .split("\n")
      .find((candidate) => candidate.includes(`android:${attribute}(`));
    if (
      !line ||
      !/(?:\bfalse\b|0x0+\b)/.test(line) ||
      /0xffffffff/.test(line)
    ) {
      errors.push(
        `Release APK manifest tree must set android:${attribute}=false.`,
      );
    }
  }
  for (const required of [
    "isMonitoringTool",
    "child_monitoring",
    ...REQUIRED_SERVICES,
  ]) {
    if (!tree.includes(required))
      errors.push(`Release APK manifest tree is missing ${required}.`);
  }
  for (const permission of PROHIBITED_PERMISSIONS) {
    if (tree.includes(`android.permission.${permission}`)) {
      errors.push(
        `Release APK manifest tree contains prohibited permission ${permission}.`,
      );
    }
  }
  if (/fixture/i.test(tree))
    errors.push("Release APK manifest tree contains fixture content.");
  return errors;
}

function verifyArtifactTree(apkPath, aaptPath) {
  const tree = execFileSync(
    aaptPath,
    ["dump", "xmltree", apkPath, "AndroidManifest.xml"],
    {
      encoding: "utf8",
    },
  );
  return verifyArtifactManifestTree(tree);
}

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function main() {
  const mergedManifest = argument("--merged-manifest");
  const apk = argument("--apk");
  const aapt = argument("--aapt");
  if (
    !mergedManifest ||
    !apk ||
    !aapt ||
    !existsSync(mergedManifest) ||
    !existsSync(apk) ||
    !existsSync(aapt)
  ) {
    throw new Error(
      "Usage: verify-release-artifact.mjs --merged-manifest <path> --apk <path> --aapt <path>",
    );
  }
  if (statSync(apk).size === 0) throw new Error("Release APK is empty.");
  const errors = [
    ...verifyMergedManifest(readFileSync(mergedManifest, "utf8")),
    ...verifyArtifactTree(apk, aapt),
  ];
  if (errors.length)
    throw new Error(
      `Release artifact policy failed:\n${errors.map((error) => `- ${error}`).join("\n")}`,
    );
  process.stdout.write("Guardian release artifact policy passed.\n");
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1])
  main();
