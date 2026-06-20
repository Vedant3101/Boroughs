import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { fetchVisits, type Visit } from "@/api/visits";
import { fetchRatings, type Rating } from "@/api/ratings";
import { StarRating } from "@/components/StarRating";
import styles from "./Profile.module.scss";

export default function Profile() {
  const { user } = useAuth();
  const [visits, setVisits] = useState<Visit[]>([]);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchVisits(), fetchRatings()])
      .then(([v, r]) => {
        if (cancelled) return;
        setVisits(v.results);
        setRatings(r.results);
      })
      .catch(() => {
        if (!cancelled) setErr("Couldn't load your activity.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (!user) return null;

  const uniqueBarsVisited = new Set(visits.map((v) => v.bar)).size;
  const avgRatingGiven =
    ratings.length === 0
      ? null
      : ratings.reduce((s, r) => s + r.score, 0) / ratings.length;

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <h1 className={styles.title}>{user.username}</h1>
        <p className={styles.meta}>{user.email}</p>
        <p className={styles.meta}>
          Joined {new Date(user.date_joined).toLocaleDateString()}
        </p>
      </header>

      <section className={styles.statsRow}>
        <Stat label="Visits" value={visits.length.toString()} />
        <Stat label="Unique bars" value={uniqueBarsVisited.toString()} />
        <Stat
          label="Avg rating given"
          value={avgRatingGiven !== null ? `★ ${avgRatingGiven.toFixed(1)}` : "—"}
        />
      </section>

      {err && <div className={styles.error}>{err}</div>}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Recent visits</h2>
        {loading ? (
          <p className={styles.muted}>Loading…</p>
        ) : visits.length === 0 ? (
          <p className={styles.muted}>
            No visits logged yet. <Link to="/">Find a bar to visit.</Link>
          </p>
        ) : (
          <ul className={styles.list}>
            {visits.slice(0, 25).map((v) => (
              <li key={v.id} className={styles.row}>
                <Link to={`/bars/${v.bar}`} className={styles.barName}>
                  {v.bar_name}
                </Link>
                <span className={styles.dateCell}>
                  {new Date(v.visited_at).toLocaleString(undefined, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </span>
                {v.notes && <span className={styles.notes}>{v.notes}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Ratings given</h2>
        {loading ? (
          <p className={styles.muted}>Loading…</p>
        ) : ratings.length === 0 ? (
          <p className={styles.muted}>No ratings yet.</p>
        ) : (
          <ul className={styles.list}>
            {ratings.slice(0, 25).map((r) => (
              <li key={r.id} className={styles.row}>
                <Link to={`/bars/${r.bar}`} className={styles.barName}>
                  {r.bar_name}
                </Link>
                <span className={styles.starsCell}>
                  <StarRating value={r.score} size="sm" readonly />
                </span>
                {r.comment && <span className={styles.notes}>{r.comment}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
    </div>
  );
}
