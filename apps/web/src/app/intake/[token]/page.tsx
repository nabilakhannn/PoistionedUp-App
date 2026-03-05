"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { publicIntakeApi, type IntakeForm, type IntakeSubmit } from "@/lib/api/intake";

export default function PublicIntakePage() {
  const params = useParams();
  const token = params.token as string;

  const [form, setForm] = useState<IntakeForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [data, setData] = useState<Partial<IntakeSubmit>>({});

  useEffect(() => {
    if (!token) return;
    publicIntakeApi.getForm(token).then(f => {
      setForm(f);
      if (f?.submitted_at) setSubmitted(true);
      if (f) {
        setData({
          client_name: f.client_name || "",
          business_name: f.business_name || "",
          industry: f.industry || "",
          current_revenue: f.current_revenue || "",
          primary_offer: f.primary_offer || "",
          offer_price: f.offer_price || "",
          secondary_offers: f.secondary_offers || "",
          target_audience: f.target_audience || "",
          best_3_clients: f.best_3_clients || "",
          traffic_sources: f.traffic_sources || "",
          funnel_status: f.funnel_status || "",
          biggest_frustration: f.biggest_frustration || "",
          goals: f.goals || "",
          tech_stack: f.tech_stack || "",
          timeline: f.timeline || "",
          additional_notes: f.additional_notes || "",
        });
      }
      setLoading(false);
    });
  }, [token]);

  const set = (key: keyof IntakeSubmit) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => setData(prev => ({ ...prev, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data.client_name?.trim()) { setError("Please enter your name."); return; }
    setSubmitting(true);
    setError(null);
    try {
      await publicIntakeApi.submit(token, data);
      setSubmitted(true);
    } catch {
      setError("Failed to submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!form) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900 mb-2">Form not found</p>
          <p className="text-gray-500">This link may have expired or is invalid.</p>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">✓</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Thanks! You're all set.</h1>
          <p className="text-gray-500 text-sm leading-relaxed">
            Your coach will review this before your call. No further action needed from you right now.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-block bg-indigo-600 text-white text-xs font-bold px-3 py-1.5 rounded-full mb-4">
            CLIENT INTAKE FORM
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Let's get to know your business</h1>
          <p className="text-gray-500 text-sm mt-2">
            Fill this in before your call so your coach can make the most of your time together.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
              {error}
            </div>
          )}

          <Section title="About You">
            <FormField label="Your name *">
              <input type="text" value={data.client_name || ""} onChange={set("client_name")} placeholder="Your full name" />
            </FormField>
            <FormField label="Business name">
              <input type="text" value={data.business_name || ""} onChange={set("business_name")} placeholder="Your company or brand name" />
            </FormField>
            <FormField label="Industry / niche">
              <input type="text" value={data.industry || ""} onChange={set("industry")} placeholder="e.g. Testosterone optimization, Executive coaching" />
            </FormField>
          </Section>

          <Section title="Your Business">
            <FormField label="Current annual revenue (rough estimate)">
              <input type="text" value={data.current_revenue || ""} onChange={set("current_revenue")} placeholder="e.g. $200k, $1M+" />
            </FormField>
            <FormField label="Primary offer + price">
              <textarea
                value={data.primary_offer || ""}
                onChange={set("primary_offer")}
                placeholder="What do you sell, and what does it cost? e.g. 12-week coaching, $5,000"
                rows={2}
              />
            </FormField>
            <FormField label="Secondary offers (if any)">
              <textarea
                value={data.secondary_offers || ""}
                onChange={set("secondary_offers")}
                placeholder="Any other products, courses, or services..."
                rows={2}
              />
            </FormField>
          </Section>

          <Section title="Your Clients">
            <FormField label="Describe your ideal client in 1-2 sentences">
              <textarea
                value={data.target_audience || ""}
                onChange={set("target_audience")}
                placeholder="Who are you trying to reach with your content?"
                rows={2}
              />
            </FormField>
            <FormField label="Describe your 3 best clients (names optional)">
              <textarea
                value={data.best_3_clients || ""}
                onChange={set("best_3_clients")}
                placeholder="e.g. Mike, 52-year-old CEO who recovered his energy; Sarah, entrepreneur who lost 20lbs..."
                rows={3}
              />
            </FormField>
          </Section>

          <Section title="Your Marketing">
            <FormField label="Current traffic sources">
              <input type="text" value={data.traffic_sources || ""} onChange={set("traffic_sources")} placeholder="e.g. LinkedIn, referrals, paid ads, podcast" />
            </FormField>
            <FormField label="Current funnel / website status">
              <textarea
                value={data.funnel_status || ""}
                onChange={set("funnel_status")}
                placeholder="Do you have a website? Booking page? Email list? What's working and what isn't?"
                rows={2}
              />
            </FormField>
          </Section>

          <Section title="Your Goals">
            <FormField label="Biggest frustration right now">
              <textarea
                value={data.biggest_frustration || ""}
                onChange={set("biggest_frustration")}
                placeholder="What's the main problem you're trying to solve?"
                rows={2}
              />
            </FormField>
            <FormField label="Goals for working together">
              <textarea
                value={data.goals || ""}
                onChange={set("goals")}
                placeholder="What does success look like in 6 months?"
                rows={2}
              />
            </FormField>
            <FormField label="Timeline">
              <input type="text" value={data.timeline || ""} onChange={set("timeline")} placeholder="e.g. Want results within 3 months, flexible" />
            </FormField>
          </Section>

          <Section title="Technical">
            <FormField label="Tech stack (tools you use)">
              <input type="text" value={data.tech_stack || ""} onChange={set("tech_stack")} placeholder="e.g. HubSpot, Kajabi, ClickFunnels, Notion..." />
            </FormField>
            <FormField label="Anything else you want us to know">
              <textarea
                value={data.additional_notes || ""}
                onChange={set("additional_notes")}
                placeholder="Anything that would help us prepare for the call..."
                rows={3}
              />
            </FormField>
          </Section>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-4 rounded-xl text-white text-lg font-semibold disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
          >
            {submitting ? "Submitting..." : "Submit →"}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">{title}</h3>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactElement<{ className?: string }> }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      {React.cloneElement(children, {
        className:
          "w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none",
      })}
    </div>
  );
}

import React from "react";
