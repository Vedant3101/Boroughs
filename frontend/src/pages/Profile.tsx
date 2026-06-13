import { useAuth } from "@/contexts/AuthContext";
import styles from "./Profile.module.scss";

export default function Profile() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>{user.username}</h1>
      <p className={styles.meta}>{user.email}</p>
      <p className={styles.meta}>
        Joined {new Date(user.date_joined).toLocaleDateString()}
      </p>
      <p className={styles.muted}>
        Your visits and ratings will show up here.
      </p>
    </div>
  );
}
