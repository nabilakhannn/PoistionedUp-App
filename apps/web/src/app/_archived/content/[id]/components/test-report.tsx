"use client";

import { WorkflowDetail } from "@/lib/api";

export function TestReportPanel({ workflow }: { workflow: WorkflowDetail }) {
  const testReport = (workflow.settings as any)?._test_report || [];

  if (testReport.length === 0) return null;

  const passed = testReport.filter((t: any) => t.passed).length;
  const failed = testReport.length - passed;

  return (
    <div className="bg-zinc-900 border border-zinc-700/50 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-zinc-300">Quality Test Report</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-lg">
            {passed} passed
          </span>
          {failed > 0 && (
            <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-lg">
              {failed} failed
            </span>
          )}
        </div>
      </div>
      <div className="space-y-2">
        {testReport.map((test: any, i: number) => (
          <div
            key={i}
            className={`flex items-start gap-2 text-sm rounded-lg p-2 ${
              test.passed ? "bg-green-500/10" : "bg-red-500/10"
            }`}
          >
            <span className={`mt-0.5 ${test.passed ? "text-green-400" : "text-red-400"}`}>
              {test.passed ? "✓" : "✗"}
            </span>
            <div className="flex-1">
              <span className="font-medium text-white">{test.type}</span>
              {test.issues && test.issues.length > 0 && (
                <ul className="mt-1 space-y-0.5">
                  {test.issues.map((issue: string, j: number) => (
                    <li key={j} className="text-xs text-red-400">
                      {issue}
                    </li>
                  ))}
                </ul>
              )}
              {test.risk_flags && test.risk_flags.length > 0 && (
                <div className="flex gap-1 mt-1 flex-wrap">
                  {test.risk_flags.map((flag: string, j: number) => (
                    <span
                      key={j}
                      className="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded-lg"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
