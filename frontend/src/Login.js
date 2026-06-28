import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { FaLock, FaRocket, FaUser } from "react-icons/fa";
import ThreeBackground from "./components/ThreeBackground";
import Particles from "./components/Particles";

export default function Login({ setUser }) {
  const [authMode, setAuthMode] = useState("register");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("security");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [voiceReady, setVoiceReady] = useState(false);

  const speak = useCallback((text, force = false) => {
    if (!window.speechSynthesis || (!voiceReady && !force)) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }, [voiceReady]);

  useEffect(() => {
    const welcomeText =
      "Welcome to the secure access control system. Please register first or login if you already have an account.";

    const enableVoice = () => {
      setVoiceReady(true);
      speak(welcomeText, true);
    };

    window.addEventListener("click", enableVoice, { once: true });
    return () => window.removeEventListener("click", enableVoice);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleVoiceGuide = () => {
    const pageText = authMode === "register"
      ? "You are on the registration page. Enter your username, select a role, and create a secure password."
      : "You are on the login page. Enter your username, password, and select your role before signing in.";
    setVoiceReady(true);
    speak(pageText, true);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please enter username and password");
      return;
    }

    setError("");
    setMessage("");
    setLoading(true);

    try {
      const response = await axios.post(
        "/login",
        { username: username.trim(), password, role },
        { headers: { "Content-Type": "application/json" }, withCredentials: true }
      );

      const resolvedRole = response.data.role || role;
      setUser({ username: username.trim(), role: resolvedRole });
      speak(`Welcome ${resolvedRole === "admin" ? "administrator" : "security officer"}. You are being redirected to your dashboard.`);
    } catch (err) {
      const message = err.response?.data?.error || "Login failed. Check credentials.";
      setError(message);
      setPassword("");
      speak(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim() || !confirmPassword.trim()) {
      setError("Please fill in all fields");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setError("");
    setMessage("");
    setLoading(true);

    try {
      await axios.post(
        "/signup",
        { username: username.trim(), password, role },
        { headers: { "Content-Type": "application/json" } }
      );

      setMessage("Account created! Switching to login...");
      speak("Account created successfully. Please login with your new credentials.");
      setTimeout(() => {
        setUsername("");
        setPassword("");
        setConfirmPassword("");
        setError("");
        setMessage("");
        setAuthMode("login");
      }, 1500);
    } catch (err) {
      setError(err.response?.data?.error || "Signup failed. Try a different username.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <ThreeBackground />
      <Particles />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="login-container"
      >
        <div className="login-header">
          <div className="login-badge">
            <FaLock />
          </div>
          <h1>🔐 Secure Access</h1>
          <p className="subtitle">Unauthorized Detection System</p>
        </div>

        {authMode === "register" ? (
          <form onSubmit={handleSignup} className="auth-form">
            <h2>Create Account</h2>
            <p className="form-subtitle">Register as Security or Admin</p>

            <div className="form-group">
              <label>Username</label>
              <div className="input-wrapper">
                <FaUser />
                <input
                  type="text"
                  placeholder="Enter username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Role</label>
              <div className="auth-role-row">
                <button
                  type="button"
                  className={`auth-role-button ${role === "security" ? "active" : ""}`}
                  onClick={() => setRole("security")}
                  disabled={loading}
                >
                  Security Officer
                </button>
                <button
                  type="button"
                  className={`auth-role-button ${role === "admin" ? "active" : ""}`}
                  onClick={() => setRole("admin")}
                  disabled={loading}
                >
                  Administrator
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>Password</label>
              <div className="input-wrapper">
                <FaLock />
                <input
                  type="password"
                  placeholder="Create password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Confirm Password</label>
              <div className="input-wrapper">
                <FaLock />
                <input
                  type="password"
                  placeholder="Confirm password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {error && <p className="error-message">{error}</p>}
            {message && <p className="success-message">{message}</p>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? "Creating account..." : "Register"}
            </button>

            <p className="auth-link">
              Already have an account?{" "}
              <span onClick={() => { setAuthMode("login"); setError(""); setMessage(""); }} style={{ cursor: "pointer", color: "#00ffff" }}>
                Login here
              </span>
            </p>
          </form>
        ) : (
          <form onSubmit={handleLogin} className="auth-form">
            <h2>Login</h2>
            <p className="form-subtitle">Access your dashboard</p>

            <div className="form-group">
              <label>Username</label>
              <div className="input-wrapper">
                <FaUser />
                <input
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                  autoFocus
                />
              </div>
            </div>

            <div className="form-group">
              <label>Login Role</label>
              <div className="auth-role-row">
                <button
                  type="button"
                  className={`auth-role-button ${role === "security" ? "active" : ""}`}
                  onClick={() => setRole("security")}
                  disabled={loading}
                >
                  Security Officer
                </button>
                <button
                  type="button"
                  className={`auth-role-button ${role === "admin" ? "active" : ""}`}
                  onClick={() => setRole("admin")}
                  disabled={loading}
                >
                  Administrator
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>Password</label>
              <div className="input-wrapper">
                <FaLock />
                <input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {error && <p className="error-message">{error}</p>}
            {message && <p className="success-message">{message}</p>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? "Logging in..." : "Login"}
            </button>

            <p className="auth-link">
              Don&apos;t have an account?{" "}
              <span onClick={() => { setAuthMode("register"); setError(""); setMessage(""); }} style={{ cursor: "pointer", color: "#00ffff" }}>
                Register here
              </span>
            </p>
          </form>
        )}

        <div className="login-action-row">
          <button type="button" className="small-button voice-button" onClick={handleVoiceGuide}>
            🔊 Voice Guide
          </button>
        </div>
        <p className="footer-text">
          <FaRocket /> Secured by advanced authentication
        </p>
        {!voiceReady && (
          <p className="voice-prompt">Click anywhere on the screen or press the voice button to enable guidance.</p>
        )}
      </motion.div>
    </div>
  );
}
