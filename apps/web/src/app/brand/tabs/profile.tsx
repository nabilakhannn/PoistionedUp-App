"use client";

import { useEffect, useState } from "react";
import BrandIntelligenceReport from "@/components/brand-intelligence-report";
import { clientResearchApi, type ClientDossier, type ClientReport } from "@/lib/api/client-research";

export function BrandProfileTab({ brandId }: { brandId: string }) {
  const [dossier, setDossier] = useState<ClientDossier | null>(null);
  const [brandName, setBrandName] = useState("Brand");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const report = await clientResearchApi.getReport(brandId).catch(() => null);
        if (report?.profile) setDossier(report.profile as ClientDossier);
        if (report?.name) setBrandName(report.name);
      } finally {
        setLoading(false);
      }
    })();
  }, [brandId]);

  if (loading) {
    return <div className="glass-card py-8 text-center text-xs text-zinc-500">Loading brand profile...</div>;
  }

  if (!dossier) {
    return (
      <div className="glass-card text-center py-10">
        <p className="text-sm text-zinc-400 mb-2">No research dossier yet.</p>
        <p className="text-xs text-zinc-500">Run Brand Research first to generate your intelligence report.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BrandIntelligenceReport brandId={brandId} dossier={dossier} clientName={brandName} />
    </div>
  );
}
