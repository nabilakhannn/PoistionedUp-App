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
            href="/brands"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition"
          >
            Go to Brands
          </Link>
          <Link
            href="/mission-control"
            className="px-4 py-2 border border-zinc-700 text-zinc-300 rounded-lg text-sm font-medium hover:bg-zinc-800 transition"
          >
            Go to Today
          </Link>
        </div>
      </div>
    </main>
  );
}
