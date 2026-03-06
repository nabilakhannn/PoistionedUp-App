"use client";

import { useState } from "react";
import { FormField } from "@/lib/api/marketplace";

interface DynamicFormBuilderProps {
  fields: FormField[];
  onSubmit: (data: Record<string, string>) => void;
  loading: boolean;
  submitLabel?: string;
}

export function DynamicFormBuilder({
  fields,
  onSubmit,
  loading,
  submitLabel = "Generate",
}: DynamicFormBuilderProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const set = (name: string, value: string) => {
    setSubmitted(false);
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  const allRequiredFilled = fields
    .filter((f) => f.required)
    .every((f) => (values[f.name] || "").trim().length > 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    if (!allRequiredFilled || loading) return;
    onSubmit(values);
  };

  const isFieldInvalid = (field: FormField) =>
    submitted && field.required && !(values[field.name] || "").trim();

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {fields.map((field) => (
        <div key={field.name}>
          <label className="block text-xs font-medium text-zinc-400 mb-1.5">
            {field.label}
            {field.required && <span className="text-red-400 ml-0.5">*</span>}
          </label>

          {field.type === "textarea" ? (
            <textarea
              value={values[field.name] || ""}
              onChange={(e) => set(field.name, e.target.value)}
              placeholder={field.placeholder}
              rows={4}
              className={`w-full bg-zinc-900/50 border rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none ${
                isFieldInvalid(field) ? "border-red-500/50 ring-1 ring-red-500/30" : "border-zinc-700/50"
              }`}
            />
          ) : field.type === "select" ? (
            <select
              value={values[field.name] || ""}
              onChange={(e) => set(field.name, e.target.value)}
              className={`w-full bg-zinc-900/50 border rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-violet-500/50 ${
                isFieldInvalid(field) ? "border-red-500/50 ring-1 ring-red-500/30" : "border-zinc-700/50"
              }`}
            >
              <option value="">Select...</option>
              {(field.options || []).map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={field.type || "text"}
              value={values[field.name] || ""}
              onChange={(e) => set(field.name, e.target.value)}
              placeholder={field.placeholder}
              className={`w-full bg-zinc-900/50 border rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 ${
                isFieldInvalid(field) ? "border-red-500/50 ring-1 ring-red-500/30" : "border-zinc-700/50"
              }`}
            />
          )}
          {isFieldInvalid(field) && (
            <p className="text-[10px] text-red-400 mt-0.5">Required</p>
          )}
        </div>
      ))}

      <button
        type="submit"
        disabled={!allRequiredFilled || loading}
        className="w-full py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Generating..." : submitLabel}
      </button>
    </form>
  );
}
