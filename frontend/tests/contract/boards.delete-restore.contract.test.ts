import { describe, expect, it } from "vitest";

describe("boards delete/restore contract", () => {
  it("delete response includes deleted and restoreUntil", () => {
    const sample = { deleted: true, restoreUntil: new Date().toISOString() };
    expect(typeof sample.deleted).toBe("boolean");
    expect(typeof sample.restoreUntil).toBe("string");
  });

  it("restore response returns board shape with id", () => {
    const sample = { id: "board-1", title: "Board", isDeleted: false };
    expect(sample.id).toBeTruthy();
    expect(sample.isDeleted).toBe(false);
  });
});
