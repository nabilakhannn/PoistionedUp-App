import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-[60vh] flex-col items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="text-6xl font-bold text-zinc-800 mb-4">404</div>
        <h1 className="text-2xl font-bold text-zinc-100 mb-2">
          Page not found
        </h1>
        <p className="text-zinc-400 text-sm mb-6">
          The page you are looking for does not exist or has been moved.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="glass-button-primary text-sm"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/brand"
            className="glass-button text-sm"
          >
            Go to Brand
          </Link>
        </div>
      </div>
    </main>
  );
}
