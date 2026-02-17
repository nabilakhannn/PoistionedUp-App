import type { Metadata } from "next";
import "./globals.css";
import { NavBar } from "./nav-bar";

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
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <NavBar />
        {children}
      </body>
    </html>
  );
}
