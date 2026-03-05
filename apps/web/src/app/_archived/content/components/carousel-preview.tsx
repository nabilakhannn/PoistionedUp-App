"use client";

import { useState } from "react";

interface CarouselSlide {
  slide_number: number;
  title: string;
  body: string;
  visual_cue?: string;
}

interface CarouselPreviewProps {
  item: {
    platform: string;
    title: string;
    body: string;
    metadata: Record<string, any>;
  };
  onCopy?: () => void;
}

export function CarouselPreview({ item, onCopy }: CarouselPreviewProps) {
  const [currentSlide, setCurrentSlide] = useState(0);

  // Parse slides from body or metadata
  let slides: CarouselSlide[] = [];
  try {
    const parsed = JSON.parse(item.body);
    slides = parsed.slides || [];
  } catch {
    // If body is not JSON, try metadata
    slides = item.metadata?.slides || [];
  }

  // Fallback: if no structured slides, show body as single slide
  if (slides.length === 0) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs rounded bg-purple-500/20 text-purple-300">
              {item.platform} carousel
            </span>
            <span className="text-sm font-medium text-white">{item.title}</span>
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
        <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-sans leading-relaxed">
          {item.body}
        </pre>
      </div>
    );
  }

  const slide = slides[currentSlide];
  const total = slides.length;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs rounded bg-purple-500/20 text-purple-300">
            {item.platform} carousel
          </span>
          <span className="text-sm font-medium text-white">{item.title}</span>
        </div>
        {onCopy && (
          <button
            onClick={onCopy}
            className="text-xs text-zinc-400 hover:text-white transition-colors"
          >
            Copy All
          </button>
        )}
      </div>

      {/* Slide content */}
      <div className="bg-zinc-800/50 rounded-lg p-5 min-h-[160px] flex flex-col justify-center">
        <div className="text-xs text-zinc-500 mb-2">
          Slide {currentSlide + 1} of {total}
        </div>
        <h3 className="text-lg font-semibold text-white mb-2">
          {slide?.title}
        </h3>
        <p className="text-sm text-zinc-300 leading-relaxed">{slide?.body}</p>
        {slide?.visual_cue && (
          <p className="text-xs text-zinc-500 mt-3 italic">
            Visual: {slide.visual_cue}
          </p>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setCurrentSlide((p) => Math.max(0, p - 1))}
          disabled={currentSlide === 0}
          className="px-3 py-1 text-xs rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Previous
        </button>

        {/* Dot indicators */}
        <div className="flex gap-1.5">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentSlide(i)}
              className={`w-2 h-2 rounded-full transition-colors ${
                i === currentSlide ? "bg-purple-400" : "bg-zinc-600"
              }`}
            />
          ))}
        </div>

        <button
          onClick={() =>
            setCurrentSlide((p) => Math.min(total - 1, p + 1))
          }
          disabled={currentSlide === total - 1}
          className="px-3 py-1 text-xs rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  );
}
