import { NextResponse } from "next/server";

export function apiError(message: string, status = 400, code?: string) {
  return NextResponse.json({ message, code }, { status });
}
