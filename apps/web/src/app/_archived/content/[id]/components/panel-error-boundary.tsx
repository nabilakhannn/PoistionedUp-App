"use client";

import React, { Component, ReactNode } from "react";

interface Props {
  /** Friendly label shown in the error fallback (e.g. "Sidebar", "Editor") */
  panelName: string;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

/**
 * Error boundary scoped to a single composer panel.
 * If one panel crashes, the others keep working.
 */
export class PanelErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message || "Unknown error" };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(
      `[PanelErrorBoundary] ${this.props.panelName} crashed:`,
      error,
      info.componentStack
    );
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorMessage: "" });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-[200px] p-6 text-center">
          <div className="text-3xl mb-3">&#x26A0;&#xFE0F;</div>
          <h3 className="text-sm font-semibold text-red-400 mb-1">
            {this.props.panelName} error
          </h3>
          <p className="text-xs text-zinc-500 mb-4 max-w-xs break-words">
            {this.state.errorMessage}
          </p>
          <button
            onClick={this.handleRetry}
            className="px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
