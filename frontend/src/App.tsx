import { Routes, Route, Link } from "react-router-dom";
import styles from "./App.module.scss";

function Home() {
  return (
    <div className={styles.placeholder}>
      <h1>Boroughs</h1>
      <p>Find your next round.</p>
      <p className={styles.muted}>Map view coming Day 4.</p>
    </div>
  );
}

export default function App() {
  return (
    <div className={styles.app}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.brand}>
          Boroughs
        </Link>
      </nav>
      <main className={styles.main}>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </main>
    </div>
  );
}
