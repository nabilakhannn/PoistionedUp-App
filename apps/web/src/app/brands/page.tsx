"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { personalBrandsApi, PersonalBrandSummary } from "../../lib/api";
import { useBrand } from "@/lib/brand-context";

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function CompletenessBar({ completeness }: { completeness: Record<string, number> }) {
  const overall = completeness?.overall_percent ?? 0;

  const modules = [
    { label: "F", pct: completeness?.foundation_percent ?? 0, title: "Foundation" },
    { label: "I", pct: completeness?.ica_percent ?? 0, title: "Ideal Client" },
    { label: "O", pct: completeness?.offer_percent ?? 0, title: "Offer" },
    { label: "B", pct: completeness?.brand_percent ?? 0, title: "Brand Statement" },
    { label: "A", pct: completeness?.authority_percent ?? 0, title: "Authority" },
    { label: "M", pct: completeness?.messaging_percent ?? 0, title: "Messaging" },
    { label: "P", pct: completeness?.positioning_percent ?? 0, title: "Positioning" },
    { label: "C", pct: completeness?.competitors_percent ?? 0, title: "Competitors" },
  ];

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500">Overall</span>
        <span className="text-xs font-medium text-zinc-300">{overall}%</span>
      </div>
      <div className="w-full bg-zinc-800 rounded-full h-1.5">
        <div
          className="bg-blue-500 h-1.5 rounded-full transition-all"
          style={{ width: `${overall}%` }}
        />
      </div>
      <div className="flex gap-0.5">
        {modules.map((s) => (
          <div key={s.label} className="flex-1" title={`${s.title}: ${s.pct}%`}>
            <div className="w-full bg-zinc-800 rounded-full h-1">
              <div
                className={`h-1 rounded-full transition-all ${
                  s.pct >= 80 ? "bg-green-500" : s.pct > 0 ? "bg-yellow-400" : "bg-zinc-700"
                }`}
                style={{ width: `${s.pct}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function BrandsListPage() {
  const router = useRouter();
  const { selectBrand, refreshBrands } = useBrand();
  const [brands, setBrands] = useState<PersonalBrandSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    personalBrandsApi
      .list()
      .then((resp) => setBrands(resp.brands))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleBrandClick = (brand: PersonalBrandSummary) => {
    selectBrand(brand.id);
    router.push(`/brands/${brand.id}`);
  };

  const handleDelete = async (brandId: string, brandName: string) => {
    if (!confirm(`Deactivate "${brandName}"? You can reactivate it later.`)) return;
    try {
      await personalBrandsApi.delete(brandId);
      setBrands((prev) => prev.filter((b) => b.id !== brandId));
      refreshBrands();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-4xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Your Brands</h1>
            <p className="text-zinc-400 mt-1">
              Manage your personal brands. Each brand has its own profile, content, and audience.
            </p>
          </div>
          <Link
            href="/brands/new"
            className="px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition"
          >
            + New Brand
          </Link>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-300 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        ) : brands.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-zinc-700 rounded-xl bg-zinc-900">
            <svg
              className="mx-auto h-12 w-12 text-zinc-600 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
              />
            </svg>
            <h3 className="text-lg font-medium text-zinc-200 mb-1">No brands yet</h3>
            <p className="text-zinc-500 text-sm mb-4">
              Create your first brand to start building your personal brand profile and generating content.
            </p>
            <Link
              href="/brands/new"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition"
            >
              + Create Your First Brand
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {brands.map((brand) => (
              <div
                key={brand.id}
                className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition cursor-pointer group"
                onClick={() => handleBrandClick(brand)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-zinc-100 truncate group-hover:text-blue-400 transition">
                      {brand.name}
                    </h3>
                    {brand.description && (
                      <p className="text-sm text-zinc-500 truncate mt-0.5">
                        {brand.description}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(brand.id, brand.name);
                    }}
                    className="text-zinc-600 hover:text-red-400 transition ml-3 opacity-0 group-hover:opacity-100"
                    title="Deactivate brand"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>

                <CompletenessBar completeness={brand.completeness} />

                <div className="flex items-center justify-between mt-3 text-xs text-zinc-500">
                  <span>Updated {timeAgo(brand.updated_at)}</span>
                  <span className="text-blue-400 font-medium group-hover:underline">
                    Open brand →
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
