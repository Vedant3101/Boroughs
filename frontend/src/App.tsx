import { Link, Route, Routes } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import MapPage from "@/pages/Map";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Profile from "@/pages/Profile";
import styles from "./App.module.scss";

function Nav() {
  const { user, logout, isLoading } = useAuth();

  return (
    <nav className={styles.nav}>
      <Link to="/" className={styles.brand}>
        Boroughs
      </Link>
      <div className={styles.navRight}>
        {isLoading ? null : user ? (
          <>
            <Link to="/profile" className={styles.navLink}>
              {user.username}
            </Link>
            <button className={styles.linkButton} onClick={logout}>
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className={styles.navLink}>
              Sign in
            </Link>
            <Link to="/register" className={styles.navLink}>
              Sign up
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <div className={styles.app}>
      <Nav />
      <main className={styles.main}>
        <Routes>
          <Route path="/" element={<MapPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
