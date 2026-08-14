import {
  ConfigPlugin,
  withEntitlementsPlist,
  withInfoPlist,
  withXcodeProject,
} from "@expo/config-plugins";

const APP_GROUP = "group.com.guardian.family";
type XcodeTarget = { uuid: string };
type XcodeProject = {
  pbxTargetByName: (name: string) => XcodeTarget | undefined;
  addTarget: (name: string, type: string, subfolder: string, bundleIdentifier: string) => XcodeTarget;
  addFile: (path: string, group: unknown, options: { target: string }) => unknown;
};

const withGuardianIOS: ConfigPlugin = (config) => {
  config = withEntitlementsPlist(config, (mod) => {
    mod.modResults["com.apple.developer.family-controls"] = true;
    mod.modResults["com.apple.developer.networking.networkextension"] = [
      "content-filter-provider",
      "filter-data-provider",
      "filter-control-provider",
    ];
    mod.modResults["com.apple.security.application-groups"] = [APP_GROUP];
    return mod;
  });
  config = withInfoPlist(config, (mod) => {
    mod.modResults.NSFamilyControlsUsageDescription =
      "Guardian uses Screen Time controls to apply the family policy you authorize.";
    mod.modResults.NSUserTrackingUsageDescription =
      "Guardian does not sell or share activity data; this description is reserved for system privacy declarations.";
    return mod;
  });
  return withXcodeProject(config, (mod) => {
    const project = mod.modResults as unknown as XcodeProject;
    const targets = [
      ["GuardianShieldConfiguration", "com.guardian.family.shield-configuration", "GuardianExtensions/Shield/GuardianShieldConfigurationExtension.swift"],
      ["GuardianShieldAction", "com.guardian.family.shield-action", "GuardianExtensions/Shield/GuardianShieldActionExtension.swift"],
      ["GuardianDeviceActivity", "com.guardian.family.device-activity", "GuardianExtensions/DeviceActivity/GuardianDeviceActivityMonitor.swift"],
      ["GuardianFilterData", "com.guardian.family.filter-data", "GuardianExtensions/Filter/GuardianFilterDataProvider.swift"],
      ["GuardianFilterControl", "com.guardian.family.filter-control", "GuardianExtensions/Filter/GuardianFilterControlProvider.swift"],
    ] as const;
    for (const [name, bundleIdentifier, source] of targets) {
      const target = project.pbxTargetByName(name) ??
        project.addTarget(name, "app_extension", "extensions", bundleIdentifier);
      project.addFile(source, undefined, { target: target.uuid });
    }
    return mod;
  });
};

export default withGuardianIOS;
