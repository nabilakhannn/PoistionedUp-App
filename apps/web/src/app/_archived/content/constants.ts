/**
 * Shared constants for content creation settings.
 * Used by both content/chat (manual mode) and content/new (automation pipeline).
 */

export const OBJECTIVES = [
  { id: "personal_branding", label: "Personal Branding", icon: "👤" },
  { id: "sales", label: "Drive Sales", icon: "💰" },
  { id: "grow_audience", label: "Grow Audience", icon: "📈" },
  { id: "educate", label: "Educate", icon: "🎓" },
  { id: "entertainment", label: "Entertain", icon: "🔥" },
] as const;

export const CONTENT_TYPES = [
  { id: "educational", label: "Educational" },
  { id: "storytelling", label: "Storytelling" },
  { id: "opinion", label: "Hot Take" },
  { id: "how_to", label: "How-To" },
  { id: "listicle", label: "Listicle" },
  { id: "contrarian", label: "Contrarian" },
  { id: "case_study", label: "Case Study" },
  { id: "behind_scenes", label: "Behind the Scenes" },
] as const;

export const PLATFORMS = [
  { id: "youtube", label: "YouTube", icon: "▶" },
  { id: "linkedin", label: "LinkedIn", icon: "in" },
  { id: "twitter", label: "Twitter/X", icon: "𝕏" },
  { id: "short_form", label: "Short-form", icon: "📱" },
] as const;

export const TONES = [
  { id: "conversational", label: "Conversational" },
  { id: "professional", label: "Professional" },
  { id: "authoritative", label: "Authoritative" },
  { id: "casual", label: "Casual" },
  { id: "bold", label: "Bold" },
  { id: "inspirational", label: "Inspirational" },
] as const;

export const LENGTHS = [
  { id: "short", label: "Short" },
  { id: "medium", label: "Medium" },
  { id: "long", label: "Long" },
  { id: "auto", label: "Auto" },
] as const;
