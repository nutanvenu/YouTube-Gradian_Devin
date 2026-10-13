import type { Routine } from "@guardian/policy-schema/types";
import { routineDraft, routineFromDraft } from "./routine-editor";

const existing: Routine = {
  routine_id: "bedtime", name: "Bedtime", kind: "SCHEDULED",
  window: { days: [1, 7], start: "21:00", end: "07:00" },
  allowed_apps: ["com.phone"], allowed_categories: ["EDUCATION"],
  blocked_apps: ["com.youtube"], blocked_categories: ["STREAMING_VIDEO"],
  web_mode: "STRICT", communication_mode: "ESSENTIAL_ONLY",
};

test("edits an overnight schedule without losing non-editor restrictions", () => {
  const draft = routineDraft(existing);
  draft.name = "  School nights  ";
  draft.days = [7, 1, 1];
  draft.start = "22:00";
  const edited = routineFromDraft(existing.routine_id, draft, existing);
  expect(edited).toEqual({ ...existing, name: "School nights", window: { days: [1, 7], start: "22:00", end: "07:00" } });
  expect(existing.window?.start).toBe("21:00");
});

test.each([
  [{ name: " " }, "routine name"],
  [{ days: [] }, "at least one day"],
  [{ days: [0, 8] }, "at least one day"],
  [{ start: "25:00" }, "24-hour"],
  [{ end: "9:15" }, "24-hour"],
  [{ end: "18:00" }, "different"],
])("rejects invalid draft %j", (changes, expected) => {
  expect(() => routineFromDraft("id", { ...routineDraft(), ...changes })).toThrow(expected);
});

test("manual routines remove old schedules and do not require a time window", () => {
  const manual = routineFromDraft(existing.routine_id, { ...routineDraft(existing), kind: "MANUAL", days: [], start: "" }, existing);
  expect(manual.kind).toBe("MANUAL");
  expect(manual.window).toBeUndefined();
  expect(manual.allowed_apps).toEqual(existing.allowed_apps);
});

test("draft arrays do not mutate source policy arrays", () => {
  const draft = routineDraft(existing);
  draft.days.push(2);
  draft.blockedCategories.push("GAMES");
  expect(existing.window?.days).toEqual([1, 7]);
  expect(existing.blocked_categories).toEqual(["STREAMING_VIDEO"]);
});
