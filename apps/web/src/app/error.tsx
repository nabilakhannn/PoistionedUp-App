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
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <main className="flex min-h-[60vh] flex-col items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="text-5xl mb-4">⚠️</div>
        <h1 className="text-2xl font-bold text-zinc-100 mb-2">
          Something went wrong
        </h1>
        <p className="text-zinc-400 text-sm mb-6">
          An unexpected error occurred. This has been logged and we will look
          into it. You can try again or go back to the home page.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition"
          >
            Try again
          </button>
          <a
            href="/brands"
            className="px-4 py-2 border border-zinc-700 text-zinc-300 rounded-lg text-sm font-medium hover:bg-zinc-800 transition"
          >
            Go to Home
          </a>
        </div>
        <details className="mt-6 text-left">
          <summary className="text-xs text-zinc-500 cursor-pointer">
            Error details
          </summary>
          <pre className="mt-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 p-3 rounded-lg overflow-auto max-h-48">
            {error.message}
            {error.digest ? `\n\nDigest: ${error.digest}` : ""}
            {process.env.NODE_ENV === "development" ? `\n\n${error.stack}` : ""}
          </pre>
        </details>
      </div>
    </main>
  );
}
