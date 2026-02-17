"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { oauthApi } from "@/lib/api";

function GoogleCallbackInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Connecting your Google account...");

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setStatus("error");
      setMessage("No authorization code received. Please try again.");
      return;
    }

    oauthApi
      .googleCallback(code)
      .then(() => {
        setStatus("success");
        setMessage("Google account connected. Redirecting...");
        setTimeout(() => router.push("/content"), 1500);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.message || "Failed to connect Google account.");
      });
  }, [searchParams, router]);

  return (
    <main className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        {status === "loading" && (
          <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
        )}
        {status === "success" && (
          <div className="text-green-600 text-4xl mb-4">&#10003;</div>
        )}
        {status === "error" && (
          <div className="text-red-600 text-4xl mb-4">&#10007;</div>
        )}
        <p className="text-lg text-gray-700">{message}</p>
        {status === "error" && (
          <button
            onClick={() => router.push("/content")}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Back to Content
          </button>
        )}
      </div>
    </main>
  );
}

export default function GoogleOAuthCallback() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-[60vh] items-center justify-center">
          <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
        </main>
      }
    >
      <GoogleCallbackInner />
    </Suspense>
  );
}
