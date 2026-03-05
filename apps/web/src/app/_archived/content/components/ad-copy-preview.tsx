"use client";

interface AdCopyPreviewProps {
  item: {
    platform: string;
    title: string;
    body: string;
    metadata: Record<string, any>;
  };
  onCopy?: () => void;
}

const FORMAT_COLORS: Record<string, string> = {
  single_image: "bg-green-500/20 text-green-300",
  carousel_ad: "bg-purple-500/20 text-purple-300",
  video_ad: "bg-orange-500/20 text-orange-300",
};

export function AdCopyPreview({ item, onCopy }: AdCopyPreviewProps) {
  // Parse ad data from body or metadata
  let adData: Record<string, any> = {};
  try {
    adData = JSON.parse(item.body);
  } catch {
    adData = item.metadata || {};
  }

  const adFormat = adData.ad_format || item.metadata?.ad_format || "single_image";
  const headline = adData.headline || item.title;
  const body = adData.body || item.body;
  const cta = adData.cta || item.metadata?.cta;
  const audienceHint = adData.audience_hint || item.metadata?.audience_hint;
  const slides = adData.slides || [];
  const hook = adData.hook;
  const script = adData.script;
  const thumbnailText = adData.thumbnail_text;

  const formatColor = FORMAT_COLORS[adFormat] || "bg-zinc-700 text-zinc-300";

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs rounded bg-blue-500/20 text-blue-300">
            {item.platform}
          </span>
          <span className={`px-2 py-0.5 text-xs rounded ${formatColor}`}>
            {adFormat.replace(/_/g, " ")}
          </span>
        </div>
        {onCopy && (
          <button
            onClick={onCopy}
            className="text-xs text-zinc-400 hover:text-white transition-colors"
          >
            Copy
          </button>
        )}
      </div>

      {/* Ad Content */}
      <div className="space-y-2">
        <h3 className="text-base font-semibold text-white">{headline}</h3>

        {/* Single image / generic body */}
        {body && adFormat !== "video_ad" && (
          <p className="text-sm text-zinc-300">{body}</p>
        )}

        {/* Video ad format */}
        {adFormat === "video_ad" && (
          <div className="space-y-2">
            {hook && (
              <div>
                <span className="text-xs text-zinc-500">Hook (3s):</span>
                <p className="text-sm text-zinc-300">{hook}</p>
              </div>
            )}
            {script && (
              <div>
                <span className="text-xs text-zinc-500">Script:</span>
                <p className="text-sm text-zinc-300">{script}</p>
              </div>
            )}
            {thumbnailText && (
              <div>
                <span className="text-xs text-zinc-500">Thumbnail:</span>
                <p className="text-sm text-zinc-400 italic">{thumbnailText}</p>
              </div>
            )}
          </div>
        )}

        {/* Carousel ad slides */}
        {slides.length > 0 && (
          <div className="space-y-1">
            <span className="text-xs text-zinc-500">Slides:</span>
            {slides.map((slide: any, i: number) => (
              <div key={i} className="pl-3 border-l border-zinc-700 text-sm">
                <span className="text-zinc-400 font-medium">
                  {slide.title}
                </span>
                {slide.body && (
                  <span className="text-zinc-500"> — {slide.body}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* CTA */}
        {cta && (
          <div className="pt-2 border-t border-zinc-800">
            <span className="text-xs text-zinc-500">CTA:</span>{" "}
            <span className="text-sm text-blue-400">{cta}</span>
          </div>
        )}
      </div>

      {/* Audience hint */}
      {audienceHint && (
        <p className="text-xs text-zinc-500 italic">
          Target: {audienceHint}
        </p>
      )}
    </div>
  );
}
