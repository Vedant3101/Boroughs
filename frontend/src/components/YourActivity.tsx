import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  createVisit,
  deleteVisit,
  fetchVisits,
  type Visit,
} from "@/api/visits";
import {
  deleteRating,
  fetchRatings,
  upsertRating,
  type Rating,
} from "@/api/ratings";
import { useAuth } from "@/contexts/AuthContext";
import { StarRating } from "./StarRating";
import styles from "./YourActivity.module.scss";

interface Props {
  barId: number;
}

export function YourActivity({ barId }: Props) {
  const { user } = useAuth();

  const [visits, setVisits] = useState<Visit[]>([]);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [visitDate, setVisitDate] = useState(() =>
    new Date().toISOString().slice(0, 16),
  );
  const [visitNotes, setVisitNotes] = useState("");
  const [submittingVisit, setSubmittingVisit] = useState(false);

  const myRating = useMemo(
    () => ratings.find((r) => r.bar === barId) ?? null,
    [ratings, barId],
  );
  const myVisitsHere = useMemo(
    () =>
      visits
        .filter((v) => v.bar === barId)
        .sort((a, b) => b.visited_at.localeCompare(a.visited_at)),
    [visits, barId],
  );

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

  if (!user) {
    return (
      <p className={styles.muted}>
        <Link to="/login">Sign in</Link> to mark visits and rate this bar.
      </p>
    );
  }

  if (loading) {
    return <p className={styles.muted}>Loading your activity…</p>;
  }

  async function handleRate(score: number) {
    setErr(null);
    try {
      const r = await upsertRating({ bar: barId, score });
      setRatings((prev) => {
        const filtered = prev.filter((x) => x.id !== r.id && x.bar !== barId);
        return [r, ...filtered];
      });
    } catch {
      setErr("Couldn't save your rating.");
    }
  }

  async function handleRemoveRating() {
    if (!myRating) return;
    setErr(null);
    try {
      await deleteRating(myRating.id);
      setRatings((prev) => prev.filter((r) => r.id !== myRating.id));
    } catch {
      setErr("Couldn't remove your rating.");
    }
  }

  async function handleSubmitVisit(e: FormEvent) {
    e.preventDefault();
    setSubmittingVisit(true);
    setErr(null);
    try {
      const v = await createVisit({
        bar: barId,
        visited_at: new Date(visitDate).toISOString(),
        notes: visitNotes,
      });
      setVisits((prev) => [v, ...prev]);
      setVisitNotes("");
    } catch (err: unknown) {
      const msg =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (err as any)?.response?.data?.visited_at?.[0] ??
        "Couldn't save the visit.";
      setErr(msg);
    } finally {
      setSubmittingVisit(false);
    }
  }

  async function handleDeleteVisit(id: number) {
    setErr(null);
    try {
      await deleteVisit(id);
      setVisits((prev) => prev.filter((v) => v.id !== id));
    } catch {
      setErr("Couldn't delete that visit.");
    }
  }

  return (
    <div className={styles.wrapper}>
      {err && <div className={styles.error}>{err}</div>}

      {/* --- Rating --- */}
      <div className={styles.block}>
        <div className={styles.blockHeader}>
          <span className={styles.blockLabel}>Your rating</span>
          {myRating && (
            <button className={styles.linkBtn} onClick={handleRemoveRating}>
              Remove
            </button>
          )}
        </div>
        <StarRating
          value={myRating?.score ?? 0}
          onChange={handleRate}
          size="lg"
        />
        {myRating ? (
          <p className={styles.subtle}>
            Updated {new Date(myRating.updated_at).toLocaleString()}
          </p>
        ) : (
          <p className={styles.subtle}>Tap a star to rate.</p>
        )}
      </div>

      {/* --- Visit form --- */}
      <form className={styles.block} onSubmit={handleSubmitVisit}>
        <span className={styles.blockLabel}>Log a visit</span>
        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="visit-date">
            When
          </label>
          <input
            id="visit-date"
            type="datetime-local"
            className={styles.input}
            value={visitDate}
            onChange={(e) => setVisitDate(e.target.value)}
            max={new Date().toISOString().slice(0, 16)}
            required
          />
        </div>
        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="visit-notes">
            Notes (optional)
          </label>
          <textarea
            id="visit-notes"
            className={styles.textarea}
            value={visitNotes}
            onChange={(e) => setVisitNotes(e.target.value)}
            rows={2}
            placeholder="Who, what, the vibes…"
          />
        </div>
        <button
          type="submit"
          className={styles.submitBtn}
          disabled={submittingVisit}
        >
          {submittingVisit ? "Saving…" : "Mark visited"}
        </button>
      </form>

      {/* --- Recent visits to this bar --- */}
      <div className={styles.block}>
        <span className={styles.blockLabel}>
          Your visits to this bar ({myVisitsHere.length})
        </span>
        {myVisitsHere.length === 0 ? (
          <p className={styles.subtle}>No visits yet.</p>
        ) : (
          <ul className={styles.visitList}>
            {myVisitsHere.slice(0, 8).map((v) => (
              <li key={v.id} className={styles.visitItem}>
                <span className={styles.visitDate}>
                  {new Date(v.visited_at).toLocaleString(undefined, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </span>
                {v.notes && <span className={styles.visitNotes}>{v.notes}</span>}
                <button
                  className={styles.linkBtn}
                  onClick={() => handleDeleteVisit(v.id)}
                  aria-label="Delete visit"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
