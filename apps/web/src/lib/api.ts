/**
 * API client barrel re-export.
 *
 * This file exists for backward compatibility. The actual API modules
 * live in lib/api/ directory, organized by domain:
 *
 *   lib/api/client.ts      - Core apiFetch utility
 *   lib/api/brand.ts       - Brand profile, chat, personal brands
 *   lib/api/content.ts     - Workflows, content chat
 *   lib/api/knowledge.ts   - Collections, resources, channel import
 *   lib/api/inspo.ts       - Inspo boards and items
 *   lib/api/research.ts    - Multi-platform research
 *   lib/api/performance.ts - Analytics, voice analysis, drift
 *   lib/api/memory.ts      - Agent memory
 *   lib/api/experiments.ts - A/B testing
 *   lib/api/schedule.ts    - Content calendar
 *   lib/api/picker.ts      - Unified resource picker
 *   lib/api/oauth.ts       - Google/Notion OAuth
 *   lib/api/usage.ts       - Token/cost tracking
 *   lib/api/advisor.ts     - AI advisor suggestions
 *
 * New code should import from specific modules:
 *   import { brandApi } from "@/lib/api/brand"
 *   import { contentApi } from "@/lib/api/content"
 */

export * from "./api/index";
