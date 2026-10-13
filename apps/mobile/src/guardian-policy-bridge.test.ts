const mockApplyPolicyBundle = jest.fn<Promise<{ applied: boolean; policyVersion: number }>, [string]>(
  () => Promise.resolve({ applied: true, policyVersion: 2 }),
);

test("the native policy bridge preserves nested nulls without modifying signed fields", async () => {
  const expoModulesCore = jest.requireMock<typeof import("expo-modules-core")>("expo-modules-core");
  const requireNativeModule = expoModulesCore.requireNativeModule;
  const nativeModule = jest.spyOn(expoModulesCore, "requireNativeModule").mockImplementation(
    (name) => name === "GuardianProtection"
      ? { applyPolicyBundle: mockApplyPolicyBundle }
      : requireNativeModule(name),
  );
  const { GuardianProtection } = jest.requireActual<typeof import("../modules/guardian-protection/src")>(
    "../modules/guardian-protection/src",
  );
  const bundle = {
    policy_version: 2,
    base_policy: { current_manual_routine_id: null },
    nested: [null, { value: null }],
    signature: "unchanged-signature",
  };
  await expect(GuardianProtection.applyPolicyBundle(bundle)).resolves.toEqual({
    applied: true,
    policyVersion: 2,
  });
  expect(mockApplyPolicyBundle).toHaveBeenCalledWith(JSON.stringify(bundle));
  const serialized = mockApplyPolicyBundle.mock.calls[0]?.[0];
  expect(JSON.parse(serialized)).toEqual(bundle);
  nativeModule.mockRestore();
});
