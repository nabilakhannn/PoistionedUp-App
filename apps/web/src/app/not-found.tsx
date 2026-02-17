import Link from "next/link";

export default function NotFound() {
  return (
    <main className="max-w-lg mx-auto py-20 px-6 text-center">
      <h1 className="text-6xl font-bold text-gray-200 mb-4">404</h1>
      <h2 className="text-lg font-bold text-gray-900 mb-2">Page not found</h2>
      <p className="text-sm text-gray-500 mb-6">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        href="/brand"
        className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
      >
        Go to Dashboard
      </Link>
    </main>
  );
}
