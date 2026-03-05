"use client";

import { useState, useRef, useEffect } from "react";
import { renderMarkdown } from "./canvas-utils";

interface CanvasSectionProps {
  title: string;
  body: string;
  index: number;
  onEdit: (index: number, newBody: string) => void;
  copiedKey: string;
  onCopy: (text: string, key: string) => void;
}

export function CanvasSection({
  title,
  body,
  index,
  onEdit,
  copiedKey,
  onCopy,
}: CanvasSectionProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(body);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        textareaRef.current.scrollHeight + "px";
    }
  }, [editing]);

  const sectionKey = `section-${index}`;

  return (
    <div className="group relative bg-zinc-900/50 rounded-lg border border-zinc-800/50 hover:border-zinc-700 transition">
      {/* Section header */}
      {title && (
        <div className="flex items-center justify-between px-4 pt-3 pb-1">
          <h3 className="text-sm font-semibold text-zinc-200">{title}</h3>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
            <button
              onClick={() => onCopy(title + "\n\n" + body, sectionKey)}
              className="p-1 text-zinc-500 hover:text-zinc-300 transition"
              title="Copy section"
            >
              {copiedKey === sectionKey ? (
                <svg
                  className="w-3.5 h-3.5 text-green-400"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4.5 12.75l6 6 9-13.5"
                  />
                </svg>
              ) : (
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
                  />
                </svg>
              )}
            </button>
            <button
              onClick={() => {
                setEditValue(body);
                setEditing(!editing);
              }}
              className="p-1 text-zinc-500 hover:text-zinc-300 transition"
              title="Edit section"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Section body */}
      <div className="px-4 pb-3">
        {editing ? (
          <div className="space-y-2">
            <textarea
              ref={textareaRef}
              value={editValue}
              onChange={(e) => {
                setEditValue(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = e.target.scrollHeight + "px";
              }}
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setEditing(false)}
                className="px-2.5 py-1 text-xs text-zinc-500 hover:text-zinc-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onEdit(index, editValue);
                  setEditing(false);
                }}
                className="px-2.5 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <div
            className="text-sm text-zinc-300 leading-relaxed cursor-text"
            onClick={() => {
              setEditValue(body);
              setEditing(true);
            }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
          />
        )}
      </div>
    </div>
  );
}
