import { GuardianApiClient } from "@/api/client";

test("API client sends parent credentials and parses structured responses", async () => {
  const fetcher = jest.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "p1", email: "parent@example.com" }), { status: 200 }));
  const client = new GuardianApiClient("https://guardian.test");
  await expect(client.me()).resolves.toEqual({ id: "p1", email: "parent@example.com" });
  expect(fetcher).toHaveBeenCalledWith("https://guardian.test/v1/auth/me", expect.objectContaining({ headers: expect.any(Headers) }));
  fetcher.mockRestore();
});
