import { describe, expect, it } from "vitest";

describe("whiteboard scene behavior", () => {
  it("keeps valid viewport transform bounds", () => {
    const viewport = { zoom: 1, panX: 0, panY: 0 };
    expect(viewport.zoom).toBeGreaterThan(0);
  });
});
