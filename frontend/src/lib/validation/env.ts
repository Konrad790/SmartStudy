import { z } from "zod";

export const envSchema = z.object({
  DATABASE_URL: z.string().min(1),
  AUTH_SECRET: z.string().min(1),
  AI_PROVIDER: z.enum(["ollama", "hosted"]).default("ollama"),
  OLLAMA_BASE_URL: z.string().url().optional(),
  OLLAMA_MODEL: z.string().optional(),
  GEMINI_API_KEY: z.string().min(1).optional(),
  GEMINI_MODEL: z.string().min(1).optional(),
});

export type Env = z.infer<typeof envSchema>;

export const env = envSchema.parse({
  DATABASE_URL: process.env.DATABASE_URL,
  AUTH_SECRET: process.env.AUTH_SECRET,
  AI_PROVIDER: process.env.AI_PROVIDER,
  OLLAMA_BASE_URL: process.env.OLLAMA_BASE_URL,
  OLLAMA_MODEL: process.env.OLLAMA_MODEL,
  GEMINI_API_KEY: process.env.GEMINI_API_KEY?.trim() || undefined,
  GEMINI_MODEL: process.env.GEMINI_MODEL?.trim() || undefined,
});
