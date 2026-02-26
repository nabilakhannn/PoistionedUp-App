"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { oauthApi } from "@/lib/api";

function NotionCallbackInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Connecting your Notion account...");

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setStatus("error");
      setMessage("No authorization code received. Please try again.");
      return;
    }

    oauthApi
      .notionCallback(code)
      .then((result) => {
        setStatus("success");
        const ws = result.workspace_name ? ` (${result.workspace_name})` : "";
        setMessage(`Notion account connected${ws}. Redirecting...`);
        setTimeout(() => router.push("/content"), 1500);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.message || "Failed to connect Notion account.");
      });
  }, [searchParams, router]);

  return (
    <main className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        {status === "loading" && (
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
        )}
        {status === "success" && (
          <div className="text-green-600 text-4xl mb-4">&#10003;</div>
        )}
        {status === "error" && (
          <div className="text-destructive text-4xl mb-4">&#10007;</div>
        )}
        <p className="text-lg text-foreground">{message}</p>
        {status === "error" && (
          <button
            onClick={() => router.push("/content")}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition"
          >
            Back to Content
          </button>
        )}
      </div>
    </main>
  );
}

export default function NotionOAuthCallback() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-[60vh] items-center justify-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        </main>
      }
    >
      <NotionCallbackInner />
    </Suspense>
  );
}
