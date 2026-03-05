"use client";

/**
 * Sequences Tracker — Slice 95
 *
 * Per-lead 3-message sequence tracker with "Mark Sent" checkboxes.
 * Updates sent_at in sequence JSONB via PATCH /leads/{id}.
 */

import { useCallback, useEffect, useState } from "react";
import { Lead, SequenceMessage, leadsApi } from "@/lib/api/leads";

interface Props {
  brandId: string;
}

export default function SequencesTracker({ brandId }: Props) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await leadsApi.list(brandId);
      setLeads(data.filter((l) => l.sequence && l.sequence.length > 0));
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [brandId]);

  useEffect(() => { load(); }, [load]);

  const handleToggleSent = async (lead: Lead, msgIdx: number) => {
    const newSeq: SequenceMessage[] = lead.sequence.map((m, i) => {
      if (i !== msgIdx) return m;
      return { ...m, sent_at: m.sent_at ? null : new Date().toISOString() };
    });

    // Optimistic update
    setLeads((prev) =>
      prev.map((l) => (l.id === lead.id ? { ...l, sequence: newSeq } : l))
    );

    try {
      const updated = await leadsApi.update(lead.id, { sequence: newSeq });
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    } catch {
      // Revert on failure
      setLeads((prev) =>
        prev.map((l) => (l.id === lead.id ? lead : l))
      );
    }
  };

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
          <div className="text-2xl mb-2">🔄</div>
          <p className="text-sm font-medium text-foreground mb-1">No active sequences</p>
          <p className="text-xs text-muted-foreground">
            Go to the Leads tab, enrich your leads, and generate outreach to create sequences.
          </p>
        </div>
      </div>
    );
  }

  // Sort: most recently created first
  const sorted = [...leads].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  // Stats
  const totalMessages = sorted.reduce((acc, l) => acc + l.sequence.length, 0);
  const sentMessages = sorted.reduce(
    (acc, l) => acc + l.sequence.filter((m) => m.sent_at).length,
    0
  );

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">🔄 Sequences</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {sorted.length} active lead{sorted.length !== 1 ? "s" : ""} · {sentMessages}/{totalMessages} messages sent
          </p>
        </div>
        <div className="text-xs text-muted-foreground bg-muted/30 rounded-lg px-3 py-1.5">
          {sentMessages}/{totalMessages} sent
        </div>
      </div>

      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-card border-b border-border">
              <th className="p-3 text-left text-muted-foreground font-medium w-40">Lead</th>
              <th className="p-3 text-left text-muted-foreground font-medium">Msg 1 (Connect)</th>
              <th className="p-3 text-left text-muted-foreground font-medium">Msg 2 (Day 3)</th>
              <th className="p-3 text-left text-muted-foreground font-medium">Msg 3 (Day 7)</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((lead) => (
              <tr key={lead.id} className="border-b border-border/50 hover:bg-muted/10 transition">
                <td className="p-3">
                  <div className="font-medium text-foreground">{lead.full_name}</div>
                  <div className="text-[10px] text-muted-foreground">{lead.company}</div>
                </td>
                {(lead.sequence || []).slice(0, 3).map((msg, idx) => (
                  <td key={idx} className="p-3">
                    <SequenceCell
                      msg={msg}
                      onToggle={() => handleToggleSent(lead, idx)}
                    />
                  </td>
                ))}
                {/* Pad if sequence has fewer than 3 items */}
                {(lead.sequence || []).length < 3 &&
                  Array.from({ length: 3 - (lead.sequence || []).length }).map((_, i) => (
                    <td key={`empty-${i}`} className="p-3 text-muted-foreground/30 text-[10px]">—</td>
                  ))
                }
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-muted-foreground/50">
        Click the checkbox to mark a message as sent. Uncheck to mark as pending.
      </p>
    </div>
  );
}

function SequenceCell({
  msg,
  onToggle,
}: {
  msg: SequenceMessage;
  onToggle: () => void;
}) {
  const isSent = Boolean(msg.sent_at);

  return (
    <div className="flex items-start gap-2">
      <button
        onClick={onToggle}
        className={`mt-0.5 w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0 transition ${
          isSent
            ? "bg-primary border-primary text-primary-foreground"
            : "border-border hover:border-primary/50"
        }`}
        title={isSent ? "Mark as pending" : "Mark as sent"}
      >
        {isSent && <span className="text-[8px]">✓</span>}
      </button>
      <div>
        <div className={`capitalize text-[10px] font-medium ${isSent ? "text-muted-foreground/50 line-through" : "text-foreground"}`}>
          {msg.channel}
        </div>
        {isSent && msg.sent_at && (
          <div className="text-[9px] text-muted-foreground/50">
            Sent {new Date(msg.sent_at).toLocaleDateString()}
          </div>
        )}
        {msg.message && (
          <p className={`text-[10px] line-clamp-2 mt-0.5 ${isSent ? "text-muted-foreground/40" : "text-muted-foreground"}`}>
            {msg.message}
          </p>
        )}
      </div>
    </div>
  );
}
