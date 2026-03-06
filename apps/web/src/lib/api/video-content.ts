import { apiFetch } from "./client";

export interface VideoCapabilities {
  script_only: boolean;
  heygen: boolean;
  veo: boolean;
}

export interface VideoScript {
  script: string;
  video_type: string;
  duration_seconds: number;
  platform: string;
  deliverable_id: string | null;
}

export interface VideoStatus {
  status: string;
  video_url?: string;
  thumbnail_url?: string;
  duration?: number;
  error?: string;
  task_id?: string;
  available?: boolean;
}

export const videoContentApi = {
  getCapabilities: (): Promise<VideoCapabilities> =>
    apiFetch("/video/capabilities"),

  createScript: (data: {
    brand_id: string;
    topic: string;
    video_type?: string;
    duration_seconds?: number;
    platform?: string;
  }): Promise<VideoScript> =>
    apiFetch("/video/script", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  generateHeygen: (data: {
    script: string;
    avatar_id?: string;
    voice_id?: string;
    emotion?: string;
    speed?: number;
    dimensions?: string;
  }): Promise<VideoStatus> =>
    apiFetch("/video/heygen/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  pollHeygen: (taskId: string): Promise<VideoStatus> =>
    apiFetch(`/video/heygen/status/${taskId}`),

  generateVeo: (data: {
    prompt: string;
    aspect_ratio?: string;
    reference_image_url?: string;
  }): Promise<VideoStatus> =>
    apiFetch("/video/veo/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  pollVeo: (taskId: string): Promise<VideoStatus> =>
    apiFetch(`/video/veo/status/${taskId}`),
};
