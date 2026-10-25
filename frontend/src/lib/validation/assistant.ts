import { z } from "zod";

const imageMime = z.enum(["image/png", "image/jpeg", "image/webp"]);

const visibleViewportSchema = z.object({
  minX: z.number(),
  minY: z.number(),
  maxX: z.number(),
  maxY: z.number(),
  zoom: z.number().positive(),
  widthPx: z.number().positive(),
  heightPx: z.number().positive(),
});

export const patchBboxSchema = z.object({
  minX: z.number(),
  minY: z.number(),
  maxX: z.number(),
  maxY: z.number(),
  width: z.number(),
  height: z.number(),
});

export const assistantMessageSchema = z
  .object({
    message: z.string().min(1).max(4000),
    conversationId: z.string().nullable().optional(),
    boardImageMimeType: imageMime.optional(),
    boardImageBase64: z.string().max(12_000_000).optional(),
    patchBbox: patchBboxSchema.nullable().optional(),
    visibleViewport: visibleViewportSchema.nullable().optional(),
  })
  .superRefine((val, ctx) => {
    const hasImage = Boolean(val.boardImageBase64?.trim());
    if (hasImage && !val.boardImageMimeType) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "boardImageMimeType is required when boardImageBase64 is set",
        path: ["boardImageMimeType"],
      });
    }
    if (val.boardImageMimeType && !val.boardImageBase64?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "boardImageBase64 is required when boardImageMimeType is set",
        path: ["boardImageBase64"],
      });
    }
  });

export const assistantDrawSchema = z.object({
  todraw: z.record(z.unknown()),
  visibleViewport: visibleViewportSchema.nullable().optional(),
  boardContextJson: z.record(z.unknown()).nullable().optional(),
  existingElementBboxes: z
    .array(
      z.object({
        id: z.string().optional(),
        x: z.number(),
        y: z.number(),
        width: z.number(),
        height: z.number(),
      })
    )
    .optional(),
});

export const assistantGenerateSchema = z.object({
  prompt: z.string().min(1).max(4000),
});

export const visionSyncSchema = z.object({
  boardImageMimeType: imageMime,
  boardImageBase64: z.string().min(1).max(12_000_000),
  patchBbox: patchBboxSchema.nullable().optional(),
  visibleViewport: visibleViewportSchema.nullable().optional(),
});
