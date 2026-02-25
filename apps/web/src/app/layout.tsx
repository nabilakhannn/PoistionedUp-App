import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { NavBar } from "./nav-bar";
import { BrandProvider } from "@/lib/brand-context";
import { PostHogProvider } from "./posthog-provider";

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
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-100">
        <Suspense fallback={null}>
          <PostHogProvider />
        </Suspense>
        <BrandProvider>
          <NavBar />
          {/* Main content area: offset by sidebar width on desktop, offset by top bar on mobile */}
          <main className="md:pl-60 pt-14 md:pt-0 min-h-screen">
            {children}
          </main>
        </BrandProvider>
      </body>
    </html>
  );
}
