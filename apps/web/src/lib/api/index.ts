/**
 * Barrel re-export for the API client.
 *
 * All domain modules are re-exported here so existing imports like
 *   import { brandApi, WorkflowSummary } from "@/lib/api"
 * continue to work without changes.
 *
 * New code should prefer importing from specific modules:
 *   import { brandApi } from "@/lib/api/brand"
 *   import { contentApi } from "@/lib/api/content"
 */

// Core client (for advanced usage)
export { apiFetch, API_BASE } from "./client";

// Domain modules
export * from "./brand";
export * from "./knowledge";
export * from "./inspo";
export * from "./content";
export * from "./research";
export * from "./performance";
export * from "./memory";
export * from "./experiments";
export * from "./schedule";
export * from "./picker";
export * from "./oauth";
export * from "./usage";
export * from "./advisor";
export * from "./strategist";
export * from "./training";
export * from "./mission-control";
export * from "./orchestrator";
export * from "./agent-bridge";
export * from "./composer";
export * from "./gateway";