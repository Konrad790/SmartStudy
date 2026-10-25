import { snapshotSchema } from "@/lib/validation/board";
import { describe, expect, it } from "vitest";

describe("boards snapshot contract", () => {
  it("accepts valid snapshot payload", () => {
    const parsed = snapshotSchema.safeParse({ baseVersion: 0, sceneJson: {} });
    expect(parsed.success).toBe(true);
  });

  it("rejects invalid baseVersion", () => {
    const parsed = snapshotSchema.safeParse({ baseVersion: -1, sceneJson: {} });
    expect(parsed.success).toBe(false);
  });
});
