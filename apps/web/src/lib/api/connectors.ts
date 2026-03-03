import { apiFetch } from "./client";

export type ConnectorService = "linkedin" | "twitter" | "instagram" | "webhook";

export interface Connector {
  id: string;
  service: ConnectorService;
  display_name: string;
  is_active: boolean;
  last_tested_at: string | null;
  last_test_status: "ok" | "error" | "untested" | null;
  last_test_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectorTestResult {
  status: "ok" | "error";
  message: string;
}

export const connectorsApi = {
  list: () =>
    apiFetch<Connector[]>("/connectors/"),

  save: (service: ConnectorService, credentials: Record<string, string>, displayName?: string) =>
    apiFetch<{ status: string; connector: Connector }>(`/connectors/${service}`, {
      method: "POST",
      body: JSON.stringify({ credentials, display_name: displayName }),
    }),

  remove: (service: ConnectorService) =>
    apiFetch<{ status: string; service: string }>(`/connectors/${service}`, { method: "DELETE" }),

  test: (service: ConnectorService) =>
    apiFetch<ConnectorTestResult>(`/connectors/${service}/test`, { method: "POST", body: JSON.stringify({}) }),
};
