import type { Category, Routine } from "@guardian/policy-schema/types";

export const ROUTINE_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const ROUTINE_CATEGORIES: Category[] = ["STREAMING_VIDEO", "SOCIAL_MEDIA", "GAMES", "MESSAGING", "EDUCATION", "PRODUCTIVITY"];

export type RoutineDraft = {
  name: string;
  kind: Routine["kind"];
  days: number[];
  start: string;
  end: string;
  blockedCategories: Category[];
  blockedApps: string[];
};

export function routineDraft(routine?: Routine): RoutineDraft {
  return {
    name: routine?.name ?? "Focus time",
    kind: routine?.kind ?? "SCHEDULED",
    days: [...(routine?.window?.days ?? [1, 2, 3, 4, 5])],
    start: routine?.window?.start ?? "18:00",
    end: routine?.window?.end ?? "19:00",
    blockedCategories: [...(routine?.blocked_categories ?? (routine ? [] : ["STREAMING_VIDEO", "SOCIAL_MEDIA", "GAMES"]))],
    blockedApps: [...(routine?.blocked_apps ?? [])],
  };
}

export function routineFromDraft(id: string, draft: RoutineDraft, existing?: Routine): Routine {
  if (!draft.name.trim()) throw new Error("Enter a routine name.");
  const routine: Routine = {
    ...existing,
    routine_id: id,
    name: draft.name.trim(),
    kind: draft.kind,
    blocked_categories: [...new Set(draft.blockedCategories)],
    blocked_apps: [...new Set(draft.blockedApps)],
  };
  if (draft.kind === "SCHEDULED") {
    if (!draft.days.length || draft.days.some((day) => !Number.isInteger(day) || day < 1 || day > 7)) {
      throw new Error("Choose at least one day.");
    }
    if (![draft.start, draft.end].every((time) => /^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/.test(time))) {
      throw new Error("Use 24-hour times, such as 18:00.");
    }
    if (draft.start === draft.end) throw new Error("Start and end times must be different.");
    routine.window = { days: [...new Set(draft.days)].sort((a, b) => a - b) as [number, ...number[]], start: draft.start, end: draft.end };
  } else {
    delete routine.window;
  }
  return routine;
}
