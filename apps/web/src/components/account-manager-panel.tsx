"use client";

import { useState } from "react";
import { accountManagerApi, type AccountManagerSession, type ActionItem, type ActionCategory } from "@/lib/api/account-manager";
import { clientDeliverablesApi } from "@/lib/api/client-deliverables";

interface Props {
  session: AccountManagerSession;
  onUpdate?: (updated: AccountManagerSession) => void;
}

const CATEGORY_ICONS: Record<ActionCategory, string> = {
  content: "✍️",
  brand_profile: "🏷",
  leads: "👥",
  knowledge: "📚",
  nurture: "📧",
  gaps: "🔍",
  deliverable: "📦",
};

const CATEGORY_LABELS: Record<ActionCategory, string> = {
  content: "Content",
  brand_profile: "Brand Profile",
  leads: "Leads",
  knowledge: "Knowledge",
  nurture: "Nurture Sequence",
  gaps: "Content Gaps",
  deliverable: "Deliverables",
};

const PRIORITY_COLORS: Record<string, string> = {
  high: "text-red-400",
  medium: "text-yellow-400",
  low: "text-slate-500",
};

export default function AccountManagerPanel({ session: initialSession, onUpdate }: Props) {
  const [session, setSession] = useState(initialSession);
  const [saving, setSaving] = useState(false);
  const [generatingDeliverable, setGeneratingDeliverable] = useState<string | null>(null);

  const categories = Array.from(new Set(session.action_plan.map(a => a.category))) as ActionCategory[];

  const updateAction = (id: string, patch: Partial<ActionItem>) => {
    const updated = session.action_plan.map(a => a.id === id ? { ...a, ...patch } : a);
    setSession(prev => ({ ...prev, action_plan: updated }));
  };

  const approveAll = () => {
    const updated = session.action_plan.map(a => ({ ...a, approved: true }));
    setSession(prev => ({ ...prev, action_plan: updated }));
  };

  const saveChanges = async () => {
    setSaving(true);
    try {
      await accountManagerApi.updateSession(session.id, session.action_plan, session.status);
      onUpdate?.(session);
    } catch (e) {
      console.error("Save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  const executeDeliverable = async (action: ActionItem) => {
    setGeneratingDeliverable(action.id);
    try {
      if (action.title.toLowerCase().includes("proposal")) {
        await clientDeliverablesApi.generateProposal(session.id, session.brand_id);
      } else if (action.title.toLowerCase().includes("landing page")) {
        await clientDeliverablesApi.generateLandingPage(session.brand_id);
      } else if (action.title.toLowerCase().includes("nurture")) {
        await clientDeliverablesApi.generateNurtureSequence(session.brand_id, action.description);
      }
      updateAction(action.id, { executed: true, result: "Generated — check Deliverables page" });
    } catch (e) {
      updateAction(action.id, { result: `Error: ${e instanceof Error ? e.message : "unknown"}` });
    } finally {
      setGeneratingDeliverable(null);
    }
  };

  const approvedCount = session.action_plan.filter(a => a.approved === true).length;
  const totalCount = session.action_plan.length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-[#0d1117] border border-white/10 rounded-2xl p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold text-indigo-400">📋 ACTION PLAN</span>
              <span className="text-xs text-slate-500">Call #{session.call_number} • {session.call_date}</span>
            </div>
            <h2 className="text-white font-bold text-lg">{session.client_name}</h2>
            <p className="text-slate-400 text-sm mt-1 leading-relaxed">&ldquo;{session.summary}&rdquo;</p>
          </div>
          <div className="text-right shrink-0">
            <div className="text-xs text-slate-500">Approved</div>
            <div className="text-2xl font-bold text-white">{approvedCount}<span className="text-slate-600">/{totalCount}</span></div>
          </div>
        </div>

        {/* Cross-call themes */}
        {session.cross_call_themes && session.cross_call_themes.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="text-xs text-slate-500 mb-2">🔁 RECURRING THEMES (across all calls)</div>
            <div className="flex flex-wrap gap-2">
              {session.cross_call_themes.map(theme => (
                <span key={theme} className="px-2.5 py-1 bg-yellow-900/30 text-yellow-400 border border-yellow-800/40 rounded-full text-xs">{theme}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Action categories */}
      {categories.map(cat => {
        const actions = session.action_plan.filter(a => a.category === cat);
        if (actions.length === 0) return null;
        return (
          <div key={cat} className="bg-[#0d1117] border border-white/10 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
              <h3 className="text-sm font-semibold text-slate-300">
                {CATEGORY_ICONS[cat]} {CATEGORY_LABELS[cat]} ({actions.length})
              </h3>
            </div>
            <div className="divide-y divide-white/5">
              {actions.map(action => (
                <ActionRow
                  key={action.id}
                  action={action}
                  onApprove={() => updateAction(action.id, { approved: !action.approved })}
                  onExecute={() => executeDeliverable(action)}
                  executing={generatingDeliverable === action.id}
                />
              ))}
            </div>
          </div>
        );
      })}

      {/* Actions bar */}
      <div className="flex gap-3">
        <button
          onClick={approveAll}
          className="flex-1 py-3.5 border border-green-500/50 text-green-400 hover:bg-green-900/20 rounded-xl text-sm font-medium transition-colors"
        >
          ✅ Approve All
        </button>
        <button
          onClick={saveChanges}
          disabled={saving}
          className="flex-1 py-3.5 rounded-xl text-white font-semibold disabled:opacity-50 transition-all"
          style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
        >
          {saving ? "Saving..." : "▶ Save Changes"}
        </button>
      </div>
    </div>
  );
}

function ActionRow({
  action,
  onApprove,
  onExecute,
  executing,
}: {
  action: ActionItem;
  onApprove: () => void;
  onExecute: () => void;
  executing: boolean;
}) {
  const isDeliverable = action.category === "deliverable";

  return (
    <div className={`flex items-start gap-4 px-5 py-4 transition-colors ${action.approved ? "bg-green-900/10" : ""}`}>
      {/* Approve checkbox */}
      <button
        onClick={onApprove}
        className={`mt-0.5 w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
          action.approved
            ? "bg-green-500 border-green-500 text-white"
            : "border-slate-600 hover:border-slate-400"
        }`}
      >
        {action.approved && <span className="text-xs">✓</span>}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-white text-sm font-medium">{action.title}</p>
          <span className={`text-xs font-medium uppercase ${PRIORITY_COLORS[action.priority] || "text-slate-500"}`}>
            [{action.priority}]
          </span>
        </div>
        <p className="text-slate-500 text-xs mt-1 leading-relaxed">{action.description}</p>
        {action.executed && action.result && (
          <p className="text-green-400 text-xs mt-2">✓ {action.result}</p>
        )}
        <div className="mt-2 flex items-center gap-2 text-xs text-slate-600">
          <span>→ {action.agent}</span>
        </div>
      </div>

      {/* Execute button for deliverables */}
      {isDeliverable && action.approved && !action.executed && (
        <button
          onClick={onExecute}
          disabled={executing}
          className="shrink-0 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-lg disabled:opacity-50"
        >
          {executing ? "⏳" : "Generate"}
        </button>
      )}
    </div>
  );
}
