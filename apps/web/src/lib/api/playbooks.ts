import { apiFetch } from "./client";

export interface Playbook {
  id: string;
  agent_id: string;
  agent_name: string;
  playbook_md: string;
  version: number;
  is_active: boolean;
  pending_edit_md: string | null;
  pending_edit_requested_at: string | null;
  updated_at: string;
}

export const playbooksApi = {
  list: () =>
    apiFetch<Playbook[]>("/playbooks/"),

  get: (agentId: string) =>
    apiFetch<Playbook>(`/playbooks/${agentId}`),

  seed: () =>
    apiFetch<{ seeded: number; message: string }>("/playbooks/seed", { method: "POST", body: JSON.stringify({}) }),

  proposeEdit: (agentId: string, newMd: string) =>
    apiFetch<{ status: string; agent_id: string; playbook: Playbook }>(
      `/playbooks/${agentId}/propose`,
      { method: "PATCH", body: JSON.stringify({ new_md: newMd }) }
    ),

  applyEdit: (agentId: string) =>
    apiFetch<{ status: string; agent_id: string; version: number; playbook: Playbook }>(
      `/playbooks/${agentId}/apply`,
      { method: "POST", body: JSON.stringify({}) }
    ),
};
