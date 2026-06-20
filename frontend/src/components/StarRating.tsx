import { useState } from "react";
import styles from "./StarRating.module.scss";

interface Props {
  value: number;
  onChange?: (next: number) => void;
  size?: "sm" | "md" | "lg";
  readonly?: boolean;
}

export function StarRating({ value, onChange, size = "md", readonly }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const display = hover ?? value;
  const interactive = !readonly && !!onChange;

  return (
    <div
      className={`${styles.row} ${styles[size]}`}
      onMouseLeave={() => setHover(null)}
      role="radiogroup"
      aria-label="Rating"
    >
      {[1, 2, 3, 4, 5].map((n) => {
        const filled = n <= display;
        const cls = `${styles.star} ${filled ? styles.filled : ""} ${interactive ? styles.interactive : ""}`;
        return (
          <button
            key={n}
            type="button"
            className={cls}
            disabled={!interactive}
            onMouseEnter={() => interactive && setHover(n)}
            onClick={() => interactive && onChange?.(n)}
            aria-label={`${n} star${n === 1 ? "" : "s"}`}
            aria-checked={value === n}
            role="radio"
          >
            ★
          </button>
        );
      })}
    </div>
  );
}
