"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import {
  personalBrandsApi,
  type PersonalBrandSummary,
  type PersonalBrandListResponse,
} from "@/lib/api";

// ── Types ──────────────────────────────────────────────────

interface BrandContextValue {
  /** All brands for the current user */
  brands: PersonalBrandSummary[];
  /** The currently selected brand (null if none selected) */
  currentBrand: PersonalBrandSummary | null;
  /** The brand ID shortcut (null if none selected) */
  brandId: string | null;
  /** Whether brands are still loading */
  loading: boolean;
  /** Switch to a different brand by ID */
  selectBrand: (brandId: string) => void;
  /** Clear the selected brand (go back to brand list) */
  clearBrand: () => void;
  /** Refresh the brands list from the server */
  refreshBrands: () => Promise<void>;
}

const BrandContext = createContext<BrandContextValue>({
  brands: [],
  currentBrand: null,
  brandId: null,
  loading: true,
  selectBrand: () => {},
  clearBrand: () => {},
  refreshBrands: async () => {},
});

// ── Local Storage Key ───────────────────────────────────────

const STORAGE_KEY = "positionedup_current_brand_id";

function getSavedBrandId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveBrandId(id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) {
      localStorage.setItem(STORAGE_KEY, id);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // localStorage unavailable (e.g. private browsing in some browsers)
  }
}

// ── Provider Component ──────────────────────────────────────

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brands, setBrands] = useState<PersonalBrandSummary[]>([]);
  const [currentBrand, setCurrentBrand] =
    useState<PersonalBrandSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();

  // Skip brand fetching on auth pages (login/signup)
  const isAuthPage = pathname === "/login" || pathname === "/signup";

  const fetchBrands = useCallback(async () => {
    try {
      const resp: PersonalBrandListResponse =
        await personalBrandsApi.list();
      const activeBrands = resp.brands.filter((b) => b.is_active);
      setBrands(activeBrands);
      return activeBrands;
    } catch (err) {
      console.error("[BrandProvider] Failed to fetch brands:", err);
      return [] as PersonalBrandSummary[];
    }
  }, []);

  // Initial load — skip on auth pages to prevent redirect loops
  useEffect(() => {
    if (isAuthPage) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function init() {
      const fetched = await fetchBrands();
      if (cancelled) return;

      // Restore saved brand selection
      const savedId = getSavedBrandId();
      if (savedId) {
        const match = fetched.find((b) => b.id === savedId);
        if (match) {
          setCurrentBrand(match);
        } else if (fetched.length > 0) {
          // Saved brand no longer exists, pick first
          setCurrentBrand(fetched[0]);
          saveBrandId(fetched[0].id);
        }
      } else if (fetched.length === 1) {
        // Auto-select if only one brand
        setCurrentBrand(fetched[0]);
        saveBrandId(fetched[0].id);
      }

      setLoading(false);
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [fetchBrands, isAuthPage]);

  const selectBrand = useCallback(
    (brandId: string) => {
      const match = brands.find((b) => b.id === brandId);
      if (match) {
        setCurrentBrand(match);
        saveBrandId(brandId);
      }
    },
    [brands]
  );

  const clearBrand = useCallback(() => {
    setCurrentBrand(null);
    saveBrandId(null);
  }, []);

  const refreshBrands = useCallback(async () => {
    const fetched = await fetchBrands();
    // If the current brand was updated, refresh it
    if (currentBrand) {
      const updated = fetched.find((b) => b.id === currentBrand.id);
      if (updated) {
        setCurrentBrand(updated);
      } else {
        // Current brand was deleted or deactivated
        setCurrentBrand(null);
        saveBrandId(null);
      }
    }
  }, [fetchBrands, currentBrand]);

  return (
    <BrandContext.Provider
      value={{
        brands,
        currentBrand,
        brandId: currentBrand?.id ?? null,
        loading,
        selectBrand,
        clearBrand,
        refreshBrands,
      }}
    >
      {children}
    </BrandContext.Provider>
  );
}

// ── Hook ────────────────────────────────────────────────────

export function useBrand() {
  return useContext(BrandContext);
}
