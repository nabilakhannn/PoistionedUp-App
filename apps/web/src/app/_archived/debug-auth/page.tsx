"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function DebugAuthPage() {
  const [session, setSession] = useState<any>(null);
  const [cookies, setCookies] = useState("");
  const [localStorage, setLocalStorage] = useState("");

  useEffect(() => {
    const supabase = createClient();

    // Check session
    supabase.auth.getSession().then(({ data, error }: { data: any; error: any }) => {
      setSession(data.session || { error: error?.message || "No session" });
    });

    // Check cookies
    setCookies(document.cookie || "No cookies");

    // Check localStorage
    const keys = Object.keys(window.localStorage);
    const supabaseKeys = keys.filter(k => k.includes("supabase"));
    setLocalStorage(supabaseKeys.length > 0 ? JSON.stringify(supabaseKeys) : "No Supabase keys");
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Auth Debug</h1>

      <div className="space-y-4">
        <div>
          <h2 className="font-semibold">Session from getSession():</h2>
          <pre className="bg-muted p-2 rounded text-xs overflow-auto">
            {JSON.stringify(session, null, 2)}
          </pre>
        </div>

        <div>
          <h2 className="font-semibold">document.cookie:</h2>
          <pre className="bg-muted p-2 rounded text-xs overflow-auto">
            {cookies}
          </pre>
        </div>

        <div>
          <h2 className="font-semibold">localStorage (Supabase keys):</h2>
          <pre className="bg-muted p-2 rounded text-xs overflow-auto">
            {localStorage}
          </pre>
        </div>
      </div>
    </main>
  );
}
