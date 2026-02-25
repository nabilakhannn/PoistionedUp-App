/**
 * Utility functions for the content canvas.
 */

/** Parse markdown into sections for the canvas */
export function parseContentSections(
  text: string
): { title: string; body: string }[] {
  const lines = text.split("\n");
  const sections: { title: string; body: string }[] = [];
  let currentTitle = "";
  let currentBody: string[] = [];

  for (const line of lines) {
    const headerMatch = line.match(/^#{1,3}\s+(.+)$/);
    if (headerMatch) {
      if (currentTitle || currentBody.length > 0) {
        sections.push({
          title: currentTitle,
          body: currentBody.join("\n").trim(),
        });
      }
      currentTitle = headerMatch[1];
      currentBody = [];
    } else {
      currentBody.push(line);
    }
  }
  if (currentTitle || currentBody.length > 0) {
    sections.push({
      title: currentTitle,
      body: currentBody.join("\n").trim(),
    });
  }

  return sections.filter((s) => s.body.length > 0 || s.title.length > 0);
}

/** Count words in text */
export function wordCount(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

/** Escape HTML entities to prevent XSS */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/** Simple markdown to HTML renderer (XSS-safe: escapes HTML before formatting) */
export function renderMarkdown(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(
      /^### (.*$)/gm,
      '<h3 class="text-sm font-semibold text-zinc-100 mt-3 mb-1">$1</h3>'
    )
    .replace(
      /^## (.*$)/gm,
      '<h2 class="text-base font-semibold text-zinc-100 mt-4 mb-1.5">$1</h2>'
    )
    .replace(
      /^# (.*$)/gm,
      '<h1 class="text-lg font-bold text-zinc-100 mt-4 mb-2">$1</h1>'
    )
    .replace(
      /^\d+\.\s+(.*$)/gm,
      '<div class="flex gap-2 ml-2"><span class="text-zinc-500 shrink-0">•</span><span>$1</span></div>'
    )
    .replace(
      /^-\s+(.*$)/gm,
      '<div class="flex gap-2 ml-2"><span class="text-zinc-500 shrink-0">•</span><span>$1</span></div>'
    )
    .replace(/\n\n/g, '<div class="h-3"></div>')
    .replace(/\n/g, "<br />");
}

/** Copy text to clipboard with feedback */
export async function copyToClipboard(
  text: string,
  setCopied: (v: string) => void,
  key: string
): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(""), 2000);
  } catch {
    // fallback
  }
}
