import { createBoardSchema } from "@/lib/validation/board";
import { describe, expect, it } from "vitest";

describe("boards list/create contract", () => {
  it("accepts valid create payload", () => {
    const parsed = createBoardSchema.safeParse({ title: "My board" });
    expect(parsed.success).toBe(true);
  });

  it("rejects empty title", () => {
    const parsed = createBoardSchema.safeParse({ title: "" });
    expect(parsed.success).toBe(false);
  });
});
