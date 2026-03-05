"use client";

import { useState, useCallback } from "react";
import { ContentAsset } from "@/lib/api";

// ── Copy-to-clipboard helper ──

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // fallback
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300 transition-colors shrink-0"
      title={`Copy ${label || "text"}`}
    >
      {copied ? "✓" : "📋"}
    </button>
  );
}

// ── Editable text block ──

function EditableText({
  value,
  onChange,
  editable,
  className,
  multiline = true,
}: {
  value: string;
  onChange?: (val: string) => void;
  editable?: boolean;
  className?: string;
  multiline?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  if (!editable || !editing) {
    return (
      <div
        className={`group relative ${className || ""} ${
          editable ? "cursor-text hover:bg-zinc-800/40 rounded transition-colors" : ""
        }`}
        onClick={() => {
          if (editable) {
            setDraft(value);
            setEditing(true);
          }
        }}
      >
        <span className="whitespace-pre-wrap">{value}</span>
        {editable && (
          <span className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-zinc-600 px-1">
            click to edit
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {multiline ? (
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="w-full bg-zinc-900 border border-blue-500/40 rounded-lg p-2 text-sm text-white placeholder-zinc-500 resize-y focus:outline-none focus:ring-1 focus:ring-blue-500/60 min-h-[60px]"
          rows={Math.max(3, draft.split("\n").length + 1)}
          autoFocus
        />
      ) : (
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="w-full bg-zinc-900 border border-blue-500/40 rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500/60"
          autoFocus
        />
      )}
      <div className="flex gap-1.5">
        <button
          onClick={() => {
            onChange?.(draft);
            setEditing(false);
          }}
          className="text-xs px-2.5 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-500 transition"
        >
          Save
        </button>
        <button
          onClick={() => setEditing(false)}
          className="text-xs px-2.5 py-1 text-zinc-500 hover:text-zinc-300 transition"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Section wrapper with copy + label ──

function SectionCard({
  label,
  badge,
  badgeColor,
  meta,
  copyText,
  children,
}: {
  label?: string;
  badge?: string;
  badgeColor?: string;
  meta?: string;
  copyText?: string;
  children: React.ReactNode;
}) {
  const colorClasses: Record<string, string> = {
    red: "bg-red-500/20 text-red-400",
    blue: "bg-blue-500/20 text-blue-400",
    purple: "bg-purple-500/20 text-purple-400",
    green: "bg-green-500/20 text-green-400",
    yellow: "bg-yellow-500/20 text-yellow-400",
  };

  return (
    <div className="bg-zinc-900 border border-zinc-700/50 rounded-xl p-5 relative group/card">
      {(badge || label || meta || copyText) && (
        <div className="flex items-center gap-2 mb-3">
          {badge && (
            <span
              className={`text-xs px-2 py-0.5 rounded-lg font-medium ${
                colorClasses[badgeColor || "blue"] || colorClasses.blue
              }`}
            >
              {badge}
            </span>
          )}
          {meta && <span className="text-sm text-zinc-500">{meta}</span>}
          {copyText && (
            <div className="ml-auto">
              <CopyButton text={copyText} label={label || badge || "section"} />
            </div>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

// ── Main content preview router ──

interface ContentPreviewProps {
  platform: string;
  contentPack: Record<string, any>;
  assets: ContentAsset[];
  editable?: boolean;
  onContentChange?: (key: string, value: any) => void;
}

export function ContentPreview({
  platform,
  contentPack,
  assets,
  editable,
  onContentChange,
}: ContentPreviewProps) {
  const platformAssets = assets.filter(
    (a) => a.platform === platform || (!a.platform && platform === "youtube")
  );

  if (platformAssets.length === 0 && Object.keys(contentPack).length === 0) {
    return (
      <div className="text-center py-12 text-zinc-500">
        <p>No content available for this platform yet.</p>
      </div>
    );
  }

  if (platform === "youtube")
    return (
      <YouTubePreview
        contentPack={contentPack}
        editable={editable}
        onContentChange={onContentChange}
      />
    );
  if (platform === "linkedin")
    return (
      <LinkedInPreview
        posts={contentPack.linkedin_posts || []}
        editable={editable}
        onContentChange={onContentChange}
      />
    );
  if (platform === "twitter") {
    return (
      <TwitterPreview
        posts={contentPack.twitter_posts || []}
        thread={contentPack.twitter_thread || null}
      />
    );
  }
  if (platform === "short_form") {
    return <ShortFormPreview scripts={contentPack.short_form_scripts || []} />;
  }

  return (
    <SectionCard copyText={JSON.stringify(contentPack, null, 2)}>
      <pre className="text-sm text-zinc-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
        {JSON.stringify(contentPack, null, 2)}
      </pre>
    </SectionCard>
  );
}

// ── YouTube Preview ──

function YouTubePreview({
  contentPack,
  editable,
  onContentChange,
}: {
  contentPack: Record<string, any>;
  editable?: boolean;
  onContentChange?: (key: string, value: any) => void;
}) {
  const longScript = contentPack.youtube_long || {};
  const shorts = contentPack.youtube_shorts || [];
  const titles = contentPack.titles || [];
  const description = contentPack.description || "";
  const tags = contentPack.tags || [];
  const thumbnails = contentPack.thumbnail_brief || [];

  // Collect all script text for full-section copy
  const fullScriptText = [
    longScript.hook || "",
    ...(longScript.sections || []).map(
      (s: any) => `[${s.timestamp || ""}] ${s.heading}\n${s.script}`
    ),
  ]
    .filter(Boolean)
    .join("\n\n");

  return (
    <div className="space-y-4">
      {/* Long Script */}
      {longScript.sections && (
        <SectionCard
          badge="Long Script"
          badgeColor="red"
          meta={`~${longScript.estimated_duration_minutes || "?"}min, ${
            longScript.word_count || "?"
          } words`}
          copyText={fullScriptText}
        >
          {longScript.hook && (
            <div className="bg-yellow-500/10 border-l-4 border-yellow-500 p-3 mb-4 rounded-r-lg">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium text-yellow-400">Hook</p>
                <CopyButton text={longScript.hook} label="hook" />
              </div>
              <EditableText
                value={longScript.hook}
                editable={editable}
                className="text-sm text-zinc-200"
                onChange={(val) => {
                  onContentChange?.("youtube_long", {
                    ...longScript,
                    hook: val,
                  });
                }}
              />
            </div>
          )}
          <div className="space-y-4">
            {(longScript.sections || []).map((section: any, i: number) => (
              <div key={i} className="border-l-2 border-zinc-700 pl-4 group/section">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-zinc-600 font-mono">
                    {section.timestamp || ""}
                  </span>
                  <span className="text-sm font-medium text-white">
                    {section.heading}
                  </span>
                  <div className="ml-auto opacity-0 group-hover/section:opacity-100 transition-opacity">
                    <CopyButton text={section.script} label={section.heading} />
                  </div>
                </div>
                <EditableText
                  value={section.script}
                  editable={editable}
                  className="text-sm text-zinc-300"
                  onChange={(val) => {
                    const newSections = [...longScript.sections];
                    newSections[i] = { ...section, script: val };
                    onContentChange?.("youtube_long", {
                      ...longScript,
                      sections: newSections,
                    });
                  }}
                />
                {section.broll_suggestion && (
                  <p className="text-xs text-zinc-600 mt-1 italic">
                    B-roll: {section.broll_suggestion}
                  </p>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Shorts */}
      {shorts.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-zinc-300 mb-2">
            YouTube Shorts ({shorts.length})
          </h3>
          <div className="grid grid-cols-1 gap-3">
            {shorts.map((short: any, i: number) => (
              <SectionCard
                key={i}
                badge={`Short ${i + 1}`}
                badgeColor="purple"
                meta={`~${short.estimated_duration_seconds || "?"}s`}
                copyText={`${short.hook}\n\n${short.script}${short.cta ? `\n\nCTA: ${short.cta}` : ""}`}
              >
                <div className="bg-yellow-500/10 rounded-lg p-2 mb-2">
                  <p className="text-xs text-yellow-400 font-medium">Hook</p>
                  <EditableText
                    value={short.hook}
                    editable={editable}
                    className="text-sm text-zinc-200"
                  />
                </div>
                <EditableText
                  value={short.script}
                  editable={editable}
                  className="text-sm text-zinc-300"
                />
                {short.cta && (
                  <p className="text-xs text-blue-400 mt-2">CTA: {short.cta}</p>
                )}
              </SectionCard>
            ))}
          </div>
        </div>
      )}

      {/* Titles */}
      {titles.length > 0 && (
        <SectionCard
          badge="Titles"
          badgeColor="green"
          copyText={titles.join("\n")}
        >
          <ol className="space-y-1">
            {titles.map((title: string, i: number) => (
              <li key={i} className="text-sm text-zinc-300 flex gap-2 group/title">
                <span className="text-zinc-600 shrink-0">{i + 1}.</span>
                <span className="flex-1">{title}</span>
                <div className="opacity-0 group-hover/title:opacity-100 transition-opacity">
                  <CopyButton text={title} label={`title ${i + 1}`} />
                </div>
              </li>
            ))}
          </ol>
        </SectionCard>
      )}

      {/* Description + Tags */}
      {description && (
        <SectionCard
          badge="Description"
          badgeColor="blue"
          copyText={description}
        >
          <EditableText
            value={description}
            editable={editable}
            className="text-sm text-zinc-300"
          />
        </SectionCard>
      )}
      {tags.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex gap-1 flex-wrap flex-1">
            {tags.map((tag: string, i: number) => (
              <span
                key={i}
                className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-lg"
              >
                {tag}
              </span>
            ))}
          </div>
          <CopyButton text={tags.join(", ")} label="tags" />
        </div>
      )}

      {/* Thumbnail Briefs */}
      {thumbnails.length > 0 && (
        <SectionCard badge="Thumbnails" badgeColor="yellow">
          <div className="grid grid-cols-1 gap-3">
            {thumbnails.map((tb: any, i: number) => (
              <div key={i} className="bg-zinc-800 rounded-lg p-3 group/thumb">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-white">
                    {tb.text_overlay}
                  </p>
                  <div className="opacity-0 group-hover/thumb:opacity-100 transition-opacity">
                    <CopyButton
                      text={`${tb.text_overlay}\n${tb.concept || ""}${
                        tb.emotion ? `\nEmotion: ${tb.emotion}` : ""
                      }`}
                      label="thumbnail"
                    />
                  </div>
                </div>
                <p className="text-xs text-zinc-400 mt-1">{tb.concept}</p>
                {tb.emotion && (
                  <p className="text-xs text-zinc-500">Emotion: {tb.emotion}</p>
                )}
                {tb.color_scheme && (
                  <p className="text-xs text-zinc-500">
                    Colors: {tb.color_scheme}
                  </p>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

// ── LinkedIn Preview ──

function LinkedInPreview({
  posts,
  editable,
  onContentChange,
}: {
  posts: any[];
  editable?: boolean;
  onContentChange?: (key: string, value: any) => void;
}) {
  if (posts.length === 0) {
    return (
      <p className="text-zinc-500 text-center py-8">
        No LinkedIn posts generated.
      </p>
    );
  }

  const typeLabels: Record<string, string> = {
    story: "Story Post",
    tactical: "Tactical List",
    contrarian: "Contrarian Take",
  };

  return (
    <div className="space-y-4">
      {posts.map((post: any, i: number) => {
        const fullText = [post.hook_line, post.body, post.cta]
          .filter(Boolean)
          .join("\n\n");
        return (
          <SectionCard
            key={i}
            badge={typeLabels[post.post_type] || post.post_type}
            badgeColor="blue"
            meta={`${post.char_count || "?"} chars`}
            copyText={fullText}
          >
            {/* LinkedIn-style frame */}
            <div className="border border-zinc-700/30 rounded-lg p-4 bg-zinc-950/50">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-zinc-800">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
                  U
                </div>
                <div>
                  <p className="text-xs font-medium text-zinc-300">
                    Your Name
                  </p>
                  <p className="text-[10px] text-zinc-600">
                    Just now
                  </p>
                </div>
              </div>
              {post.hook_line && (
                <EditableText
                  value={post.hook_line}
                  editable={editable}
                  className="text-sm font-medium text-white mb-2"
                  multiline={false}
                />
              )}
              <EditableText
                value={post.body}
                editable={editable}
                className="text-sm text-zinc-300"
                onChange={(val) => {
                  const newPosts = [...posts];
                  newPosts[i] = { ...post, body: val };
                  onContentChange?.("linkedin_posts", newPosts);
                }}
              />
              {post.cta && (
                <p className="text-sm text-blue-400 mt-3 pt-3 border-t border-zinc-700/50">
                  {post.cta}
                </p>
              )}
            </div>
          </SectionCard>
        );
      })}
    </div>
  );
}

// ── Twitter/X Preview ──

function TwitterPreview({
  posts,
  thread,
}: {
  posts: any[];
  thread: any;
}) {
  return (
    <div className="space-y-6">
      {posts.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-zinc-300 mb-2">
            Standalone Tweets ({posts.length})
          </h3>
          <div className="space-y-3">
            {posts.map((tweet: any, i: number) => (
              <SectionCard
                key={i}
                copyText={tweet.tweet_text}
              >
                {/* Twitter-style frame */}
                <div className="border border-zinc-700/30 rounded-xl p-3 bg-zinc-950/50">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-7 h-7 rounded-full bg-zinc-700 flex items-center justify-center text-white text-[10px] font-bold">
                      U
                    </div>
                    <div>
                      <p className="text-xs font-medium text-zinc-300">
                        @you
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-white">{tweet.tweet_text}</p>
                  <div className="flex items-center gap-3 mt-2 pt-2 border-t border-zinc-800">
                    <span className="text-xs text-zinc-500">
                      {tweet.char_count || "?"}/280 chars
                    </span>
                    <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-lg">
                      {tweet.angle}
                    </span>
                    {(tweet.char_count || 0) > 280 && (
                      <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-lg">
                        OVER LIMIT
                      </span>
                    )}
                  </div>
                </div>
              </SectionCard>
            ))}
          </div>
        </div>
      )}

      {thread && thread.hook_tweet && (
        <div>
          <h3 className="text-sm font-medium text-zinc-300 mb-2">
            Thread (
            {thread.total_tweets || (thread.tweets || []).length + 1} tweets)
          </h3>
          <div className="border-l-2 border-blue-500/30 pl-4 space-y-3">
            <SectionCard copyText={thread.hook_tweet}>
              <p className="text-xs text-blue-400 font-medium mb-1">1/</p>
              <p className="text-sm text-white">{thread.hook_tweet}</p>
            </SectionCard>
            {(thread.tweets || []).map((tweet: string, i: number) => (
              <SectionCard key={i} copyText={tweet}>
                <p className="text-xs text-zinc-500 font-medium mb-1">
                  {i + 2}/
                </p>
                <p className="text-sm text-white">{tweet}</p>
              </SectionCard>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Short-form Preview ──

function ShortFormPreview({ scripts }: { scripts: any[] }) {
  if (scripts.length === 0) {
    return (
      <p className="text-zinc-500 text-center py-8">
        No short-form scripts generated.
      </p>
    );
  }

  const angleLabels: Record<string, string> = {
    hot_take: "Hot Take",
    tactical: "Quick Tip",
    story: "Story",
  };

  return (
    <div className="space-y-4">
      {scripts.map((script: any, i: number) => {
        const fullText = [
          `Hook: ${script.hook}`,
          script.script,
          script.punchline ? `Punchline: ${script.punchline}` : "",
          script.cta ? `CTA: ${script.cta}` : "",
        ]
          .filter(Boolean)
          .join("\n\n");

        return (
          <SectionCard
            key={i}
            badge={angleLabels[script.angle] || script.angle}
            badgeColor="purple"
            meta={`~${script.estimated_seconds || "?"}s`}
            copyText={fullText}
          >
            <div className="bg-yellow-500/10 rounded-lg p-2 mb-3">
              <p className="text-xs text-yellow-400 font-medium">
                Hook (first 2s)
              </p>
              <p className="text-sm text-zinc-200">{script.hook}</p>
            </div>
            <p className="text-sm text-zinc-300 whitespace-pre-wrap mb-3">
              {script.script}
            </p>
            {script.on_screen_text && (
              <div className="bg-zinc-800 rounded-lg p-2 mb-2">
                <p className="text-xs text-zinc-500 font-medium">
                  On-screen text
                </p>
                {Array.isArray(script.on_screen_text) ? (
                  script.on_screen_text.map((t: string, j: number) => (
                    <p key={j} className="text-xs text-zinc-300">
                      {t}
                    </p>
                  ))
                ) : (
                  <p className="text-xs text-zinc-300">
                    {script.on_screen_text}
                  </p>
                )}
              </div>
            )}
            {script.punchline && (
              <p className="text-xs text-zinc-400">
                Punchline: {script.punchline}
              </p>
            )}
            {script.cta && (
              <p className="text-xs text-blue-400 mt-1">
                CTA: {script.cta}
              </p>
            )}
            {script.visual_direction && (
              <p className="text-xs text-zinc-600 mt-2 italic">
                Visual: {script.visual_direction}
              </p>
            )}
          </SectionCard>
        );
      })}
    </div>
  );
}
