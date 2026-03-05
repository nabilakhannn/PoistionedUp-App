"use client";

import { FeedCard, PLATFORM_COLORS, PLATFORM_ICONS } from "../constants";

/* ────────────────────────────────────────────────────────
   Feed Card Component
   ──────────────────────────────────────────────────────── */

export function FeedCardComponent({ card }: { card: FeedCard }) {
  const borderColor = PLATFORM_COLORS[card.source] || PLATFORM_COLORS.web;
  const icon = PLATFORM_ICONS[card.source] || "🌐";

  return (
    <div
      className={`bg-zinc-900 border border-zinc-800 ${borderColor} border-l-4 rounded-xl p-5 hover:border-zinc-700 hover:bg-zinc-900/80 transition-all group flex flex-col justify-between h-full`}
    >
      {/* Author row */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-lg shrink-0">
            {icon}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-zinc-200 truncate">
              {card.author}
            </p>
            <p className="text-xs text-zinc-500">{card.date}</p>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-sm font-medium text-zinc-100 mb-2 line-clamp-2 leading-snug">
          {card.title}
        </h3>

        {/* Snippet */}
        <p className="text-xs text-zinc-400 line-clamp-3 leading-relaxed mb-4">
          {card.snippet}
        </p>
      </div>

      {/* Bottom metrics + view link */}
      <div className="flex items-center justify-between pt-3 border-t border-zinc-800/60">
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          {card.views && (
            <span className="flex items-center gap-1" title="Views">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {card.views}
            </span>
          )}
          {card.likes && (
            <span className="flex items-center gap-1" title="Likes">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75A2.25 2.25 0 0116.5 4.5c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H14.23c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23H5.904M14.25 9h2.25M5.904 18.75c.083.205.173.405.27.602.197.4-.078.898-.523.898h-.908c-.889 0-1.713-.518-1.972-1.368a12 12 0 01-.521-3.507c0-1.553.295-3.036.831-4.398C3.387 10.095 4.439 9.75 5.25 9.75h.054c.059 0 .118.007.176.02l.128.032c.2.05.373.19.447.38l.052.128c.056.14.137.267.238.377a1.5 1.5 0 002.408 0c.101-.11.182-.236.238-.377l.052-.128a.45.45 0 01.447-.38l.128-.032A1.34 1.34 0 019.38 9.75" />
              </svg>
              {card.likes}
            </span>
          )}
          {card.comments && (
            <span className="flex items-center gap-1" title="Comments">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" />
              </svg>
              {card.comments}
            </span>
          )}
          {card.shares && (
            <span className="flex items-center gap-1" title="Shares">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
              </svg>
              {card.shares}
            </span>
          )}
        </div>
        <a
          href={card.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-medium text-blue-400 hover:text-blue-300 transition opacity-60 group-hover:opacity-100 flex items-center gap-1"
        >
          VIEW
          <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </a>
      </div>
    </div>
  );
}
