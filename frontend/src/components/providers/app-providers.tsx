"use client";

import { QueryProvider } from "@/components/providers/query-provider";
import { ClerkProvider } from "@clerk/nextjs";
import { ReactNode } from "react";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ClerkProvider
      signInFallbackRedirectUrl="/boards"
      signUpFallbackRedirectUrl="/boards"
      afterSignOutUrl="/sign-in"
    >
      <QueryProvider>{children}</QueryProvider>
    </ClerkProvider>
  );
}
