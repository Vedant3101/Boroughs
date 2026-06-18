import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchBar, type Bar } from "@/api/bars";
import styles from "./BarDetail.module.scss";

interface BarDetail extends Bar {
  phone?: string;
  website?: string;
  avg_user_rating?: number | null;
  num_user_ratings?: number;
  num_visits?: number;
  created_at?: string;
  updated_at?: string;
}

export default function BarDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [bar, setBar] = useState<BarDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    fetchBar(parseInt(id, 10))
      .then((b) => setBar(b as BarDetail))
      .catch((err) => {
        if (err?.response?.status === 404) {
          setError("This bar doesn't exist.");
        } else {
          setError("Couldn't load this bar.");
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className={styles.message}>Loading…</div>;
  }

  if (error || !bar) {
    return (
      <div className={styles.message}>
        <p>{error ?? "Not found."}</p>
        <Link to="/" className={styles.backLink}>
          ← Back to the map
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <Link to="/" className={styles.backLink}>
        ← Back to the map
      </Link>

      <header className={styles.header}>
        <h1 className={styles.name}>{bar.name}</h1>
        <div className={styles.metaRow}>
          {bar.price_level_display && (
            <span className={`${styles.chip} ${styles.priceChip}`}>
              {bar.price_level_display}
            </span>
          )}
          {bar.borough_display && (
            <span className={styles.chip}>{bar.borough_display}</span>
          )}
        </div>
      </header>

      <section className={styles.statsRow}>
        <Stat
          label="Your community"
          value={
            bar.avg_user_rating != null
              ? `★ ${bar.avg_user_rating.toFixed(1)}`
              : "—"
          }
          sub={
            bar.num_user_ratings
              ? `${bar.num_user_ratings} rating${bar.num_user_ratings === 1 ? "" : "s"}`
              : "No ratings yet"
          }
        />
        <Stat
          label="Google"
          value={bar.google_rating ? `★ ${bar.google_rating}` : "—"}
          sub={
            bar.google_rating_count
              ? `${bar.google_rating_count.toLocaleString()} reviews`
              : "No reviews"
          }
        />
        <Stat
          label="Visits"
          value={bar.num_visits != null ? bar.num_visits.toString() : "0"}
          sub="From Boroughs users"
        />
      </section>

      <section className={styles.infoSection}>
        <h2 className={styles.sectionTitle}>About</h2>
        {bar.address && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Address</span>
            <span>{bar.address}</span>
          </div>
        )}
        {bar.phone && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Phone</span>
            <a href={`tel:${bar.phone}`}>{bar.phone}</a>
          </div>
        )}
        {bar.website && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Website</span>
            <a href={bar.website} target="_blank" rel="noopener noreferrer">
              {prettyHost(bar.website)}
            </a>
          </div>
        )}
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Coordinates</span>
          <span>
            {bar.latitude}, {bar.longitude}
          </span>
        </div>
      </section>

      <section className={styles.infoSection}>
        <h2 className={styles.sectionTitle}>Your activity</h2>
        <p className={styles.muted}>
          Mark visits and rate this bar — coming soon.
        </p>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      {sub && <span className={styles.statSub}>{sub}</span>}
    </div>
  );
}

function prettyHost(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}
