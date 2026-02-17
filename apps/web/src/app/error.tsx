"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[PositionedUp] Uncaught error:", error);
  }, [error]);

  return (
    <main className="max-w-lg mx-auto py-20 px-6 text-center">
      <div className="bg-red-50 border border-red-200 rounded-xl p-8">
        <h2 className="text-lg font-bold text-red-900 mb-2">
          Something went wrong
        </h2>
        <p className="text-sm text-red-700 mb-6">
          {error.message || "An unexpected error occurred. Please try again."}
        </p>
        <button
          onClick={reset}
          className="px-5 py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
