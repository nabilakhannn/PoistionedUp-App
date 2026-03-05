"use client";

/**
 * Outreach Queue — Slice 95
 *
 * Derived view from the leads table showing all leads with outreach_draft.
 * Grouped by channel (LinkedIn DMs / Cold Emails).
 * Copy buttons + bulk export to Instantly.ai.
 */

import { useCallback, useEffect, useState } from "react";
import { Lead, leadsApi } from "@/lib/api/leads";

interface Props {
  brandId: string;
}

export default function OutreachQueue({ brandId }: Props) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await leadsApi.list(brandId);
      // Filter to leads with at least one outreach item
      setLeads(
        data.filter(
          (l) =>
            l.outreach_draft?.linkedin_dm ||
            l.outreach_draft?.cold_email?.body
        )
      );
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => { load(); }, [load]);

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    });
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await leadsApi.exportXlsx(brandId);
    } catch { /* ignore */ }
    finally { setExporting(false); }
  };

  const linkedinLeads = leads.filter((l) => l.outreach_draft?.linkedin_dm);
  const emailLeads = leads.filter((l) => l.outreach_draft?.cold_email?.body);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="max-w-2xl">
        <div className="rounded-xl border border-dashed border-border bg-card/30 px-6 py-10 text-center">
          <div className="text-2xl mb-2">✉️</div>
          <p className="text-sm font-medium text-foreground mb-1">No outreach ready yet</p>
          <p className="text-xs text-muted-foreground">
            Go to the Leads tab, enrich your leads, then click &quot;Generate Outreach&quot; on each lead.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">✉️ Outreach Queue</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {leads.length} lead{leads.length !== 1 ? "s" : ""} ready — copy and send, or export to Instantly.ai.
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="text-xs px-3 py-1.5 border border-border rounded-lg hover:bg-muted/50 disabled:opacity-50 transition"
        >
          {exporting ? "Exporting..." : "⬇ Export to Instantly.ai (.xlsx)"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* LinkedIn DMs */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-foreground">
            💼 LinkedIn DMs ({linkedinLeads.length})
          </div>
          {linkedinLeads.length === 0 ? (
            <p className="text-[10px] text-muted-foreground/50 px-1">None yet.</p>
          ) : (
            linkedinLeads.map((lead) => (
              <div key={lead.id} className="rounded-xl border border-border bg-card/50 p-3 space-y-2">
                <div>
                  <div className="text-xs font-medium text-foreground">{lead.full_name}</div>
                  <div className="text-[10px] text-muted-foreground">{lead.company}</div>
                </div>
                {lead.icebreaker && (
                  <p className="text-[10px] text-muted-foreground italic line-clamp-2">
                    &quot;{lead.icebreaker}&quot;
                  </p>
                )}
                <p className="text-[10px] text-foreground/80 line-clamp-3">
                  {lead.outreach_draft.linkedin_dm}
                </p>
                <button
                  onClick={() => copy(lead.outreach_draft.linkedin_dm!, `linkedin-${lead.id}`)}
                  className="text-[10px] text-primary hover:underline"
                >
                  {copiedKey === `linkedin-${lead.id}` ? "✓ Copied!" : "Copy DM"}
                </button>
              </div>
            ))
          )}
        </div>

        {/* Cold Emails */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-foreground">
            📧 Cold Emails ({emailLeads.length})
          </div>
          {emailLeads.length === 0 ? (
            <p className="text-[10px] text-muted-foreground/50 px-1">None yet.</p>
          ) : (
            emailLeads.map((lead) => {
              const email = lead.outreach_draft.cold_email!;
              return (
                <div key={lead.id} className="rounded-xl border border-border bg-card/50 p-3 space-y-2">
                  <div>
                    <div className="text-xs font-medium text-foreground">{lead.full_name}</div>
                    <div className="text-[10px] text-muted-foreground">{lead.email || lead.company}</div>
                  </div>
                  <div className="text-[10px] font-medium text-foreground line-clamp-1">
                    Subject: {email.subject}
                  </div>
                  <p className="text-[10px] text-foreground/80 line-clamp-3">{email.body}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => copy(email.subject, `subj-${lead.id}`)}
                      className="text-[10px] text-primary hover:underline"
                    >
                      {copiedKey === `subj-${lead.id}` ? "✓ Copied!" : "Copy Subject"}
                    </button>
                    <button
                      onClick={() => copy(email.body, `body-${lead.id}`)}
                      className="text-[10px] text-primary hover:underline"
                    >
                      {copiedKey === `body-${lead.id}` ? "✓ Copied!" : "Copy Body"}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
