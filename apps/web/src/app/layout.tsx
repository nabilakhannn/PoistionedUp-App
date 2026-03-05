import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { NavBar } from "./nav-bar";
import { BrandProvider } from "@/lib/brand-context";
import { OnboardingGuard } from "./onboarding-guard";
import { PostHogProvider } from "./posthog-provider";
import { JumboSuggestions } from "@/components/jumbo-suggestions";

export const metadata: Metadata = {
  title: "PositionedUp",
  description: "AI content creation agent for YouTube creators",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground">
        <Suspense fallback={null}>
          <PostHogProvider />
        </Suspense>
        <BrandProvider>
          <OnboardingGuard />
          <NavBar />
          {/* Main content area: offset by sidebar width on desktop, offset by top bar on mobile */}
          <main className="md:pl-60 pt-14 md:pt-0 min-h-screen">
            {children}
          </main>
          <JumboSuggestions />
        </BrandProvider>
      </body>
    </html>
  );
}
