import { createHash, X509Certificate } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const PROHIBITED_PERMISSIONS = [
  "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION", "RECORD_AUDIO", "READ_SMS", "QUERY_ALL_PACKAGES",
];
const REQUIRED_SERVICES = [
  "GuardianVpnService", "GuardianAccessibilityService", "GuardianNotificationListenerService",
];
const REQUIRED_METADATA = {
  isMonitoringTool: "child_monitoring",
  "com.guardian.family.CHILD_MONITORING_DISCLOSURE": undefined,
  "com.guardian.family.ACCESSIBILITY_DECLARATION": undefined,
  "com.guardian.family.VPN_DECLARATION": undefined,
};
const FIXTURE_MARKER = /fixture/i;

function applicationTag(xml) { return xml.match(/<application\b[^>]*>/)?.[0] ?? ""; }
function metadataTag(xml, name) {
  return Array.from(xml.matchAll(/<meta-data\b[^>]*>/g)).find((tag) => tag[0].includes(`android:name="${name}"`))?.[0];
}

export function verifyMergedManifest(xml) {
  const errors = [];
  const application = applicationTag(xml);
  if (!/android:allowBackup="false"/.test(application)) errors.push("Release merged manifest must set android:allowBackup=false.");
  if (!/android:usesCleartextTraffic="false"/.test(application)) errors.push("Release merged manifest must set android:usesCleartextTraffic=false.");
  for (const [name, requiredValue] of Object.entries(REQUIRED_METADATA)) {
    const metadata = metadataTag(xml, name);
    if (!metadata || (requiredValue && !metadata.includes(`android:value="${requiredValue}"`))) {
      errors.push(name === "isMonitoringTool" ? "Release merged manifest must declare isMonitoringTool=child_monitoring." : `Release merged manifest is missing required metadata ${name}.`);
    }
  }
  for (const service of REQUIRED_SERVICES) if (!xml.includes(service)) errors.push(`Release merged manifest is missing ${service}.`);
  for (const permission of PROHIBITED_PERMISSIONS) if (xml.includes(`android.permission.${permission}`)) errors.push(`Release merged manifest contains prohibited permission ${permission}.`);
  if (FIXTURE_MARKER.test(xml)) errors.push("Release merged manifest must not contain fixture declarations.");
  return errors;
}

export function verifyArtifactManifestTree(tree) {
  const errors = [];
  for (const attribute of ["allowBackup", "usesCleartextTraffic"]) {
    const line = tree.split("\n").find((candidate) => candidate.includes(`android:${attribute}(`));
    if (!line || !/(?:\bfalse\b|0x0+\b)/.test(line) || /0xffffffff/.test(line)) errors.push(`Release APK manifest tree must set android:${attribute}=false.`);
  }
  for (const required of ["isMonitoringTool", "child_monitoring", ...REQUIRED_SERVICES]) if (!tree.includes(required)) errors.push(`Release APK manifest tree is missing ${required}.`);
  for (const permission of PROHIBITED_PERMISSIONS) if (tree.includes(`android.permission.${permission}`)) errors.push(`Release APK manifest tree contains prohibited permission ${permission}.`);
  if (FIXTURE_MARKER.test(tree)) errors.push("Release APK manifest tree contains fixture content.");
  return errors;
}

export function fixtureMarkerErrors(entries, contents) {
  const errors = [];
  for (const entry of entries) if (FIXTURE_MARKER.test(entry)) errors.push(`Release archive contains fixture entry ${entry}.`);
  for (const content of contents) if (FIXTURE_MARKER.test(Buffer.from(content).toString("utf8"))) errors.push("Release archive contains fixture bytes.");
  return errors;
}

function output(command, args) { return execFileSync(command, args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }); }
function archiveEntries(artifact) { return output("unzip", ["-Z1", artifact]).split("\n").filter(Boolean); }
function archiveFixtureErrors(artifact) {
  const entries = archiveEntries(artifact);
  const inspected = entries.filter((entry) => /(^|\/)(assets\/|.*\.dex$|.*\.(?:jsbundle|bundle|json)$)/i.test(entry));
  return fixtureMarkerErrors(entries, inspected.map((entry) => execFileSync("unzip", ["-p", artifact, entry], { maxBuffer: 64 * 1024 * 1024 })));
}
function normalizedDigest(value) { return value.replaceAll(":", "").toLowerCase(); }
function expectedDigest() {
  const value = normalizedDigest(process.env.GUARDIAN_RELEASE_CERT_SHA256 ?? "");
  if (!/^[a-f0-9]{64}$/.test(value)) throw new Error("GUARDIAN_RELEASE_CERT_SHA256 is required for final artifact verification.");
  return value;
}
function verifyApkCertificate(apk, apksigner) {
  const details = output(apksigner, ["verify", "--verbose", "--print-certs", apk]);
  const digest = details.match(/certificate SHA-256 digest:\s*([0-9A-F:]+)/i)?.[1];
  const subject = details.match(/certificate DN:\s*(.+)/i)?.[1] ?? "";
  if (!digest || normalizedDigest(digest) !== expectedDigest()) return ["Release APK signer does not match GUARDIAN_RELEASE_CERT_SHA256."];
  if (/cn\s*=\s*android debug/i.test(subject)) return ["Release APK is signed with an Android debug certificate."];
  return [];
}
function verifyAabCertificate(aab, keytool, jarsigner) {
  output(jarsigner, ["-verify", "-certs", aab]);
  const pem = output(keytool, ["-printcert", "-jarfile", aab, "-rfc"]);
  const certificate = new X509Certificate(pem);
  const digest = createHash("sha256").update(certificate.raw).digest("hex");
  if (digest !== expectedDigest()) return ["Release AAB signer does not match GUARDIAN_RELEASE_CERT_SHA256."];
  if (/cn\s*=\s*android debug/i.test(certificate.subject)) return ["Release AAB is signed with an Android debug certificate."];
  return [];
}
function verifyApkVersion(apk, aapt, expected) {
  const version = output(aapt, ["dump", "badging", apk]).match(/versionCode='(\d+)'/)?.[1];
  return version === expected ? [] : [`Release APK versionCode ${version ?? "is absent"} does not equal requested ${expected}.`];
}
function verifyAabVersion(aab, apkanalyzer, expected) {
  const manifest = output(apkanalyzer, ["manifest", "print", aab]);
  const version = manifest.match(/(?:android:)?versionCode="(\d+)"/)?.[1];
  return version === expected ? [] : [`Release AAB versionCode ${version ?? "is absent"} does not equal requested ${expected}.`];
}
function argument(name) { const index = process.argv.indexOf(name); return index >= 0 ? process.argv[index + 1] : undefined; }
function requiredFile(path, label) { if (!path || !existsSync(path) || !statSync(path).isFile()) throw new Error(`${label} is required.`); return path; }

function main() {
  const mergedManifest = requiredFile(argument("--merged-manifest"), "Merged release manifest");
  const artifact = requiredFile(argument("--artifact"), "Release artifact");
  const kind = argument("--kind");
  const expectedVersion = process.env.GUARDIAN_RELEASE_VERSION_CODE;
  if (!/^[1-9]\d*$/.test(expectedVersion ?? "")) throw new Error("GUARDIAN_RELEASE_VERSION_CODE is required for final artifact verification.");
  if (statSync(artifact).size === 0) throw new Error(`Release ${kind} is empty.`);
  const errors = [...verifyMergedManifest(readFileSync(mergedManifest, "utf8")), ...archiveFixtureErrors(artifact)];
  if (kind === "apk") {
    const aapt = requiredFile(argument("--aapt"), "Android aapt");
    const apksigner = requiredFile(argument("--apksigner"), "Android apksigner");
    errors.push(...verifyArtifactManifestTree(output(aapt, ["dump", "xmltree", artifact, "AndroidManifest.xml"])), ...verifyApkCertificate(artifact, apksigner), ...verifyApkVersion(artifact, aapt, expectedVersion));
  } else if (kind === "aab") {
    const keytool = requiredFile(argument("--keytool"), "keytool");
    const jarsigner = requiredFile(argument("--jarsigner"), "jarsigner");
    const apkanalyzer = requiredFile(argument("--apkanalyzer"), "apkanalyzer");
    errors.push(...verifyAabCertificate(artifact, keytool, jarsigner), ...verifyAabVersion(artifact, apkanalyzer, expectedVersion));
  } else throw new Error("Release artifact kind must be apk or aab.");
  if (errors.length) throw new Error(`Release artifact policy failed:\n${errors.map((error) => `- ${error}`).join("\n")}`);
  process.stdout.write(`Guardian release ${kind.toUpperCase()} artifact policy passed.\n`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
