import { z } from "zod";

export const createBoardSchema = z.object({
  title: z.string().min(1).max(120),
});

export const snapshotSchema = z.object({
  baseVersion: z.number().int().min(0),
  sceneJson: z.record(z.unknown()),
});
