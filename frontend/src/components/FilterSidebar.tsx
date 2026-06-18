import { useEffect, useState } from "react";
import styles from "./FilterSidebar.module.scss";

export interface BarFilters {
  search: string;
  priceMax: number | null; // 1-4 or null for any
}

export const EMPTY_FILTERS: BarFilters = { search: "", priceMax: null };

interface Props {
  value: BarFilters;
  onChange: (next: BarFilters) => void;
  resultCount: number;
  loading: boolean;
}

const PRICE_LEVELS: Array<{ level: number; label: string }> = [
  { level: 1, label: "$" },
  { level: 2, label: "$$" },
  { level: 3, label: "$$$" },
  { level: 4, label: "$$$$" },
];

export function FilterSidebar({ value, onChange, resultCount, loading }: Props) {
  // Local search state for debouncing; sync up to parent after a pause.
  const [searchDraft, setSearchDraft] = useState(value.search);

  useEffect(() => {
    setSearchDraft(value.search);
  }, [value.search]);

  useEffect(() => {
    if (searchDraft === value.search) return;
    const t = window.setTimeout(() => {
      onChange({ ...value, search: searchDraft });
    }, 300);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDraft]);

  const setPriceMax = (level: number) => {
    onChange({ ...value, priceMax: value.priceMax === level ? null : level });
  };

  const isDirty = value.search !== "" || value.priceMax !== null;

  return (
    <aside className={styles.sidebar}>
      <div className={styles.section}>
        <label className={styles.label} htmlFor="search">
          Search
        </label>
        <input
          id="search"
          className={styles.input}
          placeholder="Name or address"
          value={searchDraft}
          onChange={(e) => setSearchDraft(e.target.value)}
        />
      </div>

      <div className={styles.section}>
        <span className={styles.label}>Max price</span>
        <div className={styles.priceRow}>
          {PRICE_LEVELS.map((p) => {
            const isActive = value.priceMax !== null && p.level <= value.priceMax;
            const isSelected = value.priceMax === p.level;
            return (
              <button
                key={p.level}
                type="button"
                className={`${styles.priceButton} ${isActive ? styles.priceActive : ""} ${isSelected ? styles.priceSelected : ""}`}
                onClick={() => setPriceMax(p.level)}
                aria-pressed={isSelected}
              >
                {p.label}
              </button>
            );
          })}
        </div>
        <p className={styles.hint}>
          Click again to clear. Picks bars at or below this level.
        </p>
      </div>

      <div className={styles.footer}>
        <span className={styles.count}>
          {loading
            ? "Loading…"
            : `${resultCount} bar${resultCount === 1 ? "" : "s"} in view`}
        </span>
        {isDirty && (
          <button
            type="button"
            className={styles.reset}
            onClick={() => onChange(EMPTY_FILTERS)}
          >
            Reset
          </button>
        )}
      </div>
    </aside>
  );
}
