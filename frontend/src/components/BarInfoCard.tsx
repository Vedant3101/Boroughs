import { Link } from "react-router-dom";
import type { Bar } from "@/api/bars";
import styles from "./BarInfoCard.module.scss";

export function BarInfoCard({ bar }: { bar: Bar }) {
  return (
    <div className={styles.popup}>
      <h3 className={styles.name}>{bar.name}</h3>
      <div className={styles.meta}>
        {bar.price_level_display && (
          <span className={styles.price}>{bar.price_level_display}</span>
        )}
        {bar.google_rating && (
          <span className={styles.rating}>
            ★ {bar.google_rating}
            {bar.google_rating_count
              ? ` (${bar.google_rating_count.toLocaleString()})`
              : ""}
          </span>
        )}
      </div>
      {bar.address && <p className={styles.address}>{bar.address}</p>}
      <Link to={`/bars/${bar.id}`} className={styles.detailLink}>
        View details →
      </Link>
    </div>
  );
}
