import axios from "axios";
import { useEffect, useState } from "react";
import Login from "./Login";
import Dashboard from "./Dashboard";

const AUTH_USER_KEY = "authUser";
axios.defaults.withCredentials = true;

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      const saved = window.localStorage.getItem(AUTH_USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [sessionChecked, setSessionChecked] = useState(false);

  useEffect(() => {
    const savedUser = window.localStorage.getItem(AUTH_USER_KEY);

    const fetchSession = async () => {
      try {
        const response = await axios.get("/me", { withCredentials: true });
        if (response.status === 200 && response.data?.user) {
          setUser(response.data.user);
          window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(response.data.user));
        } else {
          setUser(null);
          window.localStorage.removeItem(AUTH_USER_KEY);
        }
      } catch (err) {
        if (err.response?.status === 401) {
          setUser(null);
          window.localStorage.removeItem(AUTH_USER_KEY);
        } else if (savedUser) {
          setUser(JSON.parse(savedUser));
        } else {
          setUser(null);
        }
      } finally {
        setSessionChecked(true);
      }
    };

    fetchSession();
  }, []);

  useEffect(() => {
    if (user) {
      window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    } else {
      window.localStorage.removeItem(AUTH_USER_KEY);
    }
  }, [user]);

  const handleLogout = () => {
    window.localStorage.removeItem(AUTH_USER_KEY);
    setUser(null);
  };

  if (!sessionChecked) {
    return <div className="loading-screen">Checking session...</div>;
  }

  return user ? (
    <Dashboard user={user} logout={handleLogout} />
  ) : (
    <Login setUser={setUser} />
  );
}