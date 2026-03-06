import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist } from "next/font/google";
import "./globals.css";
import { NavBar } from "./nav-bar";
import { BrandProvider } from "@/lib/brand-context";
import { OnboardingGuard } from "./onboarding-guard";
import { PostHogProvider } from "./posthog-provider";
import { JumboBubble } from "@/components/jumbo-bubble";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
});

export const metadata: Metadata = {
  title: "PositionedUp",
  description: "AI-powered personal branding engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${geist.variable}`}>
      <body className="min-h-screen bg-background text-foreground font-sans antialiased">
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
          <JumboBubble />
        </BrandProvider>
      </body>
    </html>
  );
}
