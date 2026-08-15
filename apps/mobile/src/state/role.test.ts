import { roleStorage } from "@/state/role";
import * as SecureStore from "expo-secure-store";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
}));

test("role storage rejects values outside the supported role model", async () => {
  (SecureStore.getItemAsync as jest.Mock).mockResolvedValue("admin");
  await expect(roleStorage.get()).resolves.toBeNull();
});
