import {
  assistantDrawSchema,
  assistantGenerateSchema,
  assistantMessageSchema,
  visionSyncSchema,
} from "@/lib/validation/assistant";
import { describe, expect, it } from "vitest";

describe("assistant contracts", () => {
  it("accepts chat payload", () => {
    expect(assistantMessageSchema.safeParse({ message: "Hello" }).success).toBe(true);
  });

  it("accepts chat payload with board image", () => {
    expect(
      assistantMessageSchema.safeParse({
        message: "What is this?",
        boardImageMimeType: "image/png",
        boardImageBase64: "iVBORw0KGgo=",
      }).success
    ).toBe(true);
  });

  it("accepts chat payload with patch bbox", () => {
    expect(
      assistantMessageSchema.safeParse({
        message: "What is this equation?",
        boardImageMimeType: "image/png",
        boardImageBase64: "iVBORw0KGgo=",
        patchBbox: { minX: 100, minY: 100, maxX: 400, maxY: 300, width: 300, height: 200 },
      }).success
    ).toBe(true);
  });

  it("accepts vision sync payload", () => {
    expect(
      visionSyncSchema.safeParse({
        boardImageMimeType: "image/png",
        boardImageBase64: "iVBORw0KGgo=",
        patchBbox: { minX: 0, minY: 0, maxX: 200, maxY: 200, width: 200, height: 200 },
      }).success
    ).toBe(true);
  });

  it("rejects image without mime type", () => {
    expect(
      assistantMessageSchema.safeParse({
        message: "Hi",
        boardImageBase64: "abcd",
      }).success
    ).toBe(false);
  });

  it("accepts generate payload", () => {
    expect(assistantGenerateSchema.safeParse({ prompt: "Map idea" }).success).toBe(true);
  });

  it("accepts draw payload", () => {
    expect(
      assistantDrawSchema.safeParse({
        todraw: {
          summary: "Sketch right triangle",
          items: [{ id: "d1", kind: "shape", what: "triangle ABC" }],
        },
        visibleViewport: {
          minX: 0,
          minY: 0,
          maxX: 800,
          maxY: 600,
          zoom: 1,
          widthPx: 800,
          heightPx: 600,
        },
      }).success
    ).toBe(true);
  });
});
