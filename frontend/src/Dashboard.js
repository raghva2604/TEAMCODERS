import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { FaCamera, FaBell, FaSignOutAlt, FaShieldAlt, FaChartLine } from "react-icons/fa";

export default function Dashboard({ user, logout }) {
  const [logs, setLogs] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [stats, setStats] = useState({ authorized: 0, unauthorized: 0, alumni: 0, applicants: 0 });
  const [liveSrc, setLiveSrc] = useState(`/snapshot?ts=${Date.now()}`);
  const [telegram, setTelegram] = useState(true);
  const [voice, setVoice] = useState(true);
  const [connected, setConnected] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [cameraStatus, setCameraStatus] = useState("Monitoring");
  const [aiObservation, setAiObservation] = useState(null);
  const [videoFailed, setVideoFailed] = useState(false);
  const cacheHeaders = useMemo(() => ({ "Cache-Control": "no-cache", Pragma: "no-cache" }), []);
  const [verifyRoll, setVerifyRoll] = useState("");
  const [verifyResult, setVerifyResult] = useState("");
  const [studentForm, setStudentForm] = useState({ roll: "", name: "", status: "PRESENT" });
  const [studentPhoto, setStudentPhoto] = useState(null);
  const [studentPhotoPreview, setStudentPhotoPreview] = useState("");
  const [captureMode, setCaptureMode] = useState("camera");
  const [capturedImage, setCapturedImage] = useState("");
  const [cameraStreamError, setCameraStreamError] = useState("");
  const [pauseLiveFeed, setPauseLiveFeed] = useState(false);
  const [liveFeedResumed, setLiveFeedResumed] = useState(false);
  const [registrationPreviewSrc, setRegistrationPreviewSrc] = useState(`/snapshot?ts=${Date.now()}`);
  const [unauthorizedImages, setUnauthorizedImages] = useState([]);
  const [adminMessage, setAdminMessage] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [registeredStudent, setRegisteredStudent] = useState(null);
  const [recognitionReady, setRecognitionReady] = useState(false);
  const isAdmin = user?.role === "admin";

  const loadAlertSettings = async () => {
    try {
      const response = await axios.get("/settings/alerts");
      setTelegram(response.data.telegram);
    } catch (error) {
      console.warn("Could not load alert settings", error);
    }
  };

  const handleToggleTelegram = async () => {
    const nextValue = !telegram;
    try {
      await axios.post(
        "/settings/alerts",
        { telegram: nextValue },
        { headers: { "Content-Type": "application/json" } }
      );
      setTelegram(nextValue);
    } catch (error) {
      console.warn("Unable to update Telegram alert setting", error);
      setTelegram(nextValue);
    }
  };

  const handleTestTelegram = async () => {
    try {
      const response = await axios.post("/test/telegram");
      setAdminMessage(response.data.message || "Test alert sent!");
    } catch (error) {
      setAdminMessage(error.response?.data?.error || "Failed to send test alert");
    }
  };

  const handleResetDemo = async () => {
    try {
      const response = await axios.post("/reset_demo");
      setAdminMessage(response.data?.message || "Reset complete.");
      refreshDashboard();
      loadUnauthorizedGallery();
      setVideoFailed(false);
      setLiveSrc(`/snapshot?ts=${Date.now()}`);
    } catch (error) {
      setAdminMessage(error.response?.data?.error || "Reset failed.");
    }
  };

  const currentStatus = cameraStatus;
  const prevStatusRef = useRef("");

  const speak = useCallback((text) => {
    if (!window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }, []);

  useEffect(() => {
    if (!prevStatusRef.current) {
      prevStatusRef.current = currentStatus;
      return;
    }
    if (currentStatus !== prevStatusRef.current) {
      speak(`Camera status update: ${currentStatus}`);
      prevStatusRef.current = currentStatus;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStatus]);

  const refreshDashboard = useCallback(async () => {
    try {
      const timestamp = Date.now();
      const [logsResponse, trendResponse, statusResponse] = await Promise.all([
        axios.get(`/logs?ts=${timestamp}`, { headers: cacheHeaders }),
        axios.get(`/trend?ts=${timestamp}`, { headers: cacheHeaders }),
        axios.get(`/status?ts=${timestamp}`, { headers: cacheHeaders }),
      ]);

      const logLines = logsResponse.data || [];
      const authorized = logLines.filter((line) => line.includes(" - Authorized")).length;
      const unauthorized = logLines.filter((line) => line.includes(" - Unauthorized")).length;
      const alumni = logLines.filter((line) => line.includes(" - Alumni")).length;
      const applicants = logLines.filter((line) => line.includes(" - Applicant")).length;

      setLogs(logLines.slice(0, 30));
      setTrendData(trendResponse.data || []);
      setStats({ authorized, unauthorized, alumni, applicants });
      setCameraStatus(statusResponse.data?.status || "Monitoring");
      setAiObservation(statusResponse.data?.ai_observation || null);
      setLastRefreshed(new Date());
      setConnected(true);
    } catch (error) {
      setConnected(false);
    }
  }, [cacheHeaders]);

  const handleVerify = async () => {
    if (!verifyRoll.trim()) {
      setVerifyResult("Enter a roll number to verify.");
      return;
    }

    try {
      const response = await axios.post(
        "/verify",
        { roll: verifyRoll.trim() },
        { headers: { "Content-Type": "application/json" } }
      );
      setVerifyResult(response.data || "Verification complete.");
    } catch (error) {
      setVerifyResult(error.response?.data || "Verification failed.");
    }
  };

  const fileToDataUrl = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const playSuccessTone = () => {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      const audioContext = new AudioContextClass();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = 880;
      gainNode.gain.value = 0.04;
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      oscillator.start();
      gainNode.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.25);
      oscillator.stop(audioContext.currentTime + 0.25);
      setTimeout(() => audioContext.close(), 300);
    } catch (error) {
      console.warn("Could not play success tone", error);
    }
  };

  const uploadStudentWithPhoto = async () => {
    if (!studentPhoto) {
      setAdminMessage("Select a photo to upload.");
      return;
    }

    const studentName = studentForm.name.trim();
    const studentRoll = studentForm.roll.trim();
    setIsRegistering(true);
    setRecognitionReady(false);

    try {
      const image = await fileToDataUrl(studentPhoto);
      const payload = {
        roll: studentRoll,
        name: studentName,
        status: studentForm.status,
        image,
      };

      const response = await axios.post("/add_student", payload, {
        headers: { "Content-Type": "application/json" },
      });

      setCameraStreamError("");
      setPauseLiveFeed(false);
      setRegisteredStudent({ name: studentName, roll: studentRoll });
      setRecognitionReady(true);
      setShowSuccessModal(true);
      playSuccessTone();

      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(`${studentName} registered successfully`));
      }

      window.setTimeout(() => {
        setShowSuccessModal(false);
        if (captureMode === "camera") {
          refreshRegistrationPreview();
        }
      }, 2200);

      setAdminMessage(response.data || "Student registered successfully.");
      setStudentForm({ roll: "", name: "", status: "PRESENT" });
      setCapturedImage("");
      setStudentPhoto(null);
      setStudentPhotoPreview("");
      setIsRegistering(false);
    } catch (error) {
      setPauseLiveFeed(false);
      setIsRegistering(false);
      setAdminMessage(error.response?.data || "Failed to add student.");
    }
  };

  const handleRetakeCapture = () => {
    setCapturedImage("");
    setAdminMessage("");
    setCameraStreamError("");
  };

  const handleStudentPhotoChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setStudentPhoto(file);
    setCapturedImage("");
    const previewUrl = URL.createObjectURL(file);
    setStudentPhotoPreview(previewUrl);
  };

  const refreshRegistrationPreview = useCallback(() => {
    setRegistrationPreviewSrc(`/snapshot?ts=${Date.now()}`);
  }, []);

  const handleCloseSuccessModal = () => {
    setShowSuccessModal(false);
    if (captureMode === "camera") {
      refreshRegistrationPreview();
    }
  };

  const prevPauseLiveFeedRef = useRef(false);

  useEffect(() => {
    setPauseLiveFeed(captureMode === "camera" && isRegistering);
  }, [captureMode, isRegistering]);

  useEffect(() => {
    if (!pauseLiveFeed && prevPauseLiveFeedRef.current) {
      setLiveFeedResumed(true);
      const timeout = window.setTimeout(() => setLiveFeedResumed(false), 3000);
      return () => window.clearTimeout(timeout);
    }
    prevPauseLiveFeedRef.current = pauseLiveFeed;
    return undefined;
  }, [pauseLiveFeed]);

  const captureImage = async () => {
    if (captureMode !== "camera") {
      return;
    }

    try {
      const response = await axios.get(`/snapshot?ts=${Date.now()}`, { responseType: "blob" });
      const reader = new FileReader();
      reader.onloadend = () => {
        setCapturedImage(reader.result);
        setAdminMessage("Image captured. You can retake or register the student.");
        setCameraStreamError("");
      };
      reader.readAsDataURL(response.data);
    } catch (error) {
      console.warn("Capture image error", error);
      setAdminMessage("Unable to capture image from camera. Please retry.");
    }
  };

  const handleAddStudent = async () => {
    if (!studentForm.roll.trim() || !studentForm.name.trim()) {
      setAdminMessage("Roll number and student name are required.");
      return;
    }

    if (captureMode === "upload") {
      if (studentPhoto) {
        return uploadStudentWithPhoto();
      }
      setAdminMessage("Select a photo to upload.");
      return;
    }

    if (captureMode === "camera" && !capturedImage) {
      setAdminMessage("Capture an image before registering.");
      return;
    }

    const studentName = studentForm.name.trim();
    const studentRoll = studentForm.roll.trim();
    setIsRegistering(true);
    setRecognitionReady(false);

    try {
      const payload = {
        roll: studentRoll,
        name: studentName,
        status: studentForm.status,
      };

      if (captureMode === "camera" && capturedImage) {
        payload.image = capturedImage;
      }

      const response = await axios.post("/add_student", payload, {
        headers: { "Content-Type": "application/json" },
      });

      setCameraStreamError("");
      setPauseLiveFeed(false);
      setRegisteredStudent({ name: studentName, roll: studentRoll });
      setRecognitionReady(true);
      setShowSuccessModal(true);
      playSuccessTone();

      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(`${studentName} registered successfully`));
      }

      window.setTimeout(() => {
        setShowSuccessModal(false);
        if (captureMode === "camera") {
          refreshRegistrationPreview();
        }
      }, 2200);

      setAdminMessage(response.data || "Student registered successfully.");
      setStudentForm({ roll: "", name: "", status: "PRESENT" });
      setCapturedImage("");
      setStudentPhoto(null);
      setStudentPhotoPreview("");
      setIsRegistering(false);
    } catch (error) {
      setPauseLiveFeed(false);
      setIsRegistering(false);
      setAdminMessage(error.response?.data || "Failed to add student.");
    }
  };

  const loadUnauthorizedGallery = useCallback(async () => {
    try {
      const response = await axios.get(`/unauthorized-gallery?ts=${Date.now()}`, { headers: cacheHeaders });
      setUnauthorizedImages(response.data || []);
    } catch (error) {
      console.warn("Unable to load unauthorized gallery", error);
    }
  }, [cacheHeaders]);

  const speakPageGuide = () => {
    if (!window.speechSynthesis) return;
    const message = isAdmin
      ? "Admin Control Center. Add students, upload face images, review unauthorized alerts, and manage the access system."
      : "Security Command Center. Monitor live camera feed, incident logs, and unauthorized access alerts in real time.";
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  useEffect(() => {
    refreshDashboard();
    loadAlertSettings();
    loadUnauthorizedGallery();
    const interval = setInterval(() => {
      refreshDashboard();
      loadUnauthorizedGallery();
    }, 1500);
    return () => clearInterval(interval);
  }, [refreshDashboard, loadUnauthorizedGallery]);

  useEffect(() => {
    if (pauseLiveFeed) {
      return undefined;
    }

    const interval = setInterval(() => {
      const newSrc = `/snapshot?ts=${Date.now()}`;
      setLiveSrc(newSrc);
      if (!videoFailed) {
        setVideoFailed(false);
      }
    }, 800);
    return () => clearInterval(interval);
  }, [videoFailed, pauseLiveFeed]);

  const handleLogout = async () => {
    try {
      await axios.get("/logout");
    } catch (err) {
      console.warn("Logout failed", err);
    }
    logout();
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="dashboard-title"
          >
            {isAdmin ? "🚀 Admin Control Center" : "🚀 Security Command Center"}
          </motion.h1>
          <p className="dashboard-subtitle">
            {isAdmin
              ? "Admin dashboard with student verification and high-level control panels."
              : "Real-time access monitoring, alerts, and unauthorized incident tracking."}
          </p>
          <p className="dashboard-welcome">
            Welcome back, {user?.username || "operator"}.<span className="role-pill">{user?.role?.toUpperCase()}</span>
          </p>
        </div>

        <div className="dashboard-actions">
          <span className={`status-pill ${connected ? "status-online" : "status-offline"}`}>
            {connected ? "Connected" : "Offline"}
          </span>
          <span className="refresh-timestamp">Last refreshed: {lastRefreshed ? lastRefreshed.toLocaleTimeString() : "Pending"}</span>
          <button className="neon-button small-button" type="button" onClick={speakPageGuide}>
            🔊 Voice Guide
          </button>
          <button className="neon-button small-button" type="button" onClick={() => {
            refreshDashboard();
            loadUnauthorizedGallery();
          }}>
            ♻️ Refresh Everything
          </button>
          <button className="neon-button small-button" type="button" onClick={handleResetDemo}>
            🧹 Reset Demo
          </button>
          <button className="neon-button logout-btn" type="button" onClick={handleLogout}>
            <FaSignOutAlt /> Logout
          </button>
        </div>
      </div>

      <div className="dashboard-toggle-row">
        <Toggle label="Telegram Alerts" active={telegram} onToggle={handleToggleTelegram} />
        <Toggle label="Voice Alerts" active={voice} onToggle={() => setVoice((prev) => !prev)} />
        <button className="neon-button small-button" onClick={handleTestTelegram}>
          📱 Test Telegram
        </button>
      </div>

      <div className="dashboard-grid">
        <motion.section whileHover={{ y: -8, scale: 1.02 }} transition={{ type: "spring", stiffness: 140, damping: 16 }} className="glass-card status-card">
          <div className="card-title">
            <FaShieldAlt /> Authorized
          </div>
          <div className="status-number">{stats.authorized}</div>
        </motion.section>

        <motion.section whileHover={{ y: -8, scale: 1.02 }} transition={{ type: "spring", stiffness: 140, damping: 16 }} className="glass-card status-card status-danger">
          <div className="card-title">
            <FaBell /> Unauthorized
          </div>
          <div className="status-number">{stats.unauthorized}</div>
        </motion.section>

        <motion.section whileHover={{ y: -8, scale: 1.02 }} transition={{ type: "spring", stiffness: 140, damping: 16 }} className="glass-card status-card status-warm">
          <div className="card-title">
            <FaCamera /> Alumni
          </div>
          <div className="status-number">{stats.alumni}</div>
        </motion.section>

        <motion.section whileHover={{ y: -8, scale: 1.02 }} transition={{ type: "spring", stiffness: 140, damping: 16 }} className="glass-card status-card status-gold">
          <div className="card-title">
            <FaChartLine /> Applicants
          </div>
          <div className="status-number">{stats.applicants}</div>
        </motion.section>
      </div>

      <div className="dashboard-grid dashboard-main-grid role-panels">
        <section className="glass-card verify-panel">
          <div className="panel-header">
            <h2>Student Verification</h2>
            <span>Confirm roll access</span>
          </div>
          <div className="panel-form-group">
            <input
              value={verifyRoll}
              onChange={(e) => setVerifyRoll(e.target.value)}
              placeholder="Enter roll number to verify"
            />
            <button className="small-button" type="button" onClick={handleVerify}>
              Verify Access
            </button>
          </div>
          {verifyResult && <p className="panel-response">{verifyResult}</p>}
        </section>

        <section className="glass-card ai-panel">
          <div className="panel-header">
            <h2>AI Observation</h2>
            <span>Scene analysis for unauthorized activity</span>
          </div>
          {aiObservation ? (
            <div className="ai-observation-card">
              <p><strong>Person:</strong> {aiObservation.people > 0 ? "Unknown" : "None"}</p>
              <p><strong>Objects:</strong> {aiObservation.objects?.join(", ") || "None"}</p>
              <p><strong>Environment:</strong> {aiObservation.environment || "Indoor"}</p>
              <p><strong>Lighting:</strong> {aiObservation.lighting || "Normal"}</p>
              <p><strong>Risk:</strong> {aiObservation.risk || "LOW"}</p>
              <p className="ai-summary">{aiObservation.summary}</p>
            </div>
          ) : (
            <p className="panel-response">No AI observation yet. Unauthorized detections will appear here.</p>
          )}
        </section>

        {isAdmin ? (
          <section className="glass-card admin-panel">
            <div className="panel-header">
              <h2>Admin Panel</h2>
              <span>Add or update students</span>
            </div>
            <div className="panel-form-group">
              <label>Roll Number</label>
              <input
                value={studentForm.roll}
                onChange={(e) => setStudentForm({ ...studentForm, roll: e.target.value })}
                placeholder="Roll Number"
              />
              <label>Student Name</label>
              <input
                value={studentForm.name}
                onChange={(e) => setStudentForm({ ...studentForm, name: e.target.value })}
                placeholder="Student Name"
              />
              <label>Status</label>
              <select
                value={studentForm.status}
                onChange={(e) => setStudentForm({ ...studentForm, status: e.target.value })}
              >
                <option value="PRESENT">Present Student</option>
                <option value="PAST">Alumni</option>
                <option value="ADMISSION">Applicant</option>
              </select>

              <label>Choose Method</label>
              <div className="capture-method-row">
                <label>
                  <input
                    type="radio"
                    name="captureMode"
                    value="camera"
                    checked={captureMode === "camera"}
                    onChange={() => {
                      setCaptureMode("camera");
                      setStudentPhoto(null);
                      setStudentPhotoPreview("");
                    }}
                  />
                  Capture from Camera
                </label>
                <label>
                  <input
                    type="radio"
                    name="captureMode"
                    value="upload"
                    checked={captureMode === "upload"}
                    onChange={() => {
                      setCaptureMode("upload");
                      setCapturedImage("");
                      setCameraStreamError("");
                    }}
                  />
                  Upload Image
                </label>
              </div>

              {captureMode === "camera" ? (
                <div className="camera-capture-group">
                  <img
                    src={registrationPreviewSrc}
                    alt="Registration camera preview"
                    className="capture-video"
                    onError={() => setCameraStreamError("Unable to load camera preview. Please refresh the preview.")}
                  />
                  <div className="capture-actions">
                    <button className="small-button" type="button" onClick={refreshRegistrationPreview}>
                      🔄 Refresh Preview
                    </button>
                    <button className="small-button" type="button" onClick={captureImage}>
                      📸 Capture
                    </button>
                    {capturedImage && (
                      <button className="small-button" type="button" onClick={handleRetakeCapture}>
                        🔄 Retake
                      </button>
                    )}
                  </div>
                  {!capturedImage && cameraStreamError && (
                    <p className="panel-response">{cameraStreamError}</p>
                  )}
                  {!capturedImage && !cameraStreamError && (
                    <p className="panel-response">Registration preview is loaded from the camera snapshot. Use Capture to grab a frame.</p>
                  )}
                </div>
              ) : (
                <>
                  <label>Student Photo</label>
                  <input type="file" accept="image/*" onChange={handleStudentPhotoChange} />
                </>
              )}

              {(capturedImage || studentPhotoPreview) && (
                <div className="preview-block">
                  <label>{capturedImage ? "Captured Image Preview" : "Selected Image Preview"}</label>
                  <img
                    src={capturedImage || studentPhotoPreview}
                    alt="Student preview"
                    className="photo-preview"
                  />
                </div>
              )}

              <button
                className="small-button"
                type="button"
                onClick={handleAddStudent}
                disabled={isRegistering || (captureMode === "camera" && !capturedImage)}
              >
                {isRegistering ? "Registering..." : "💾 Register Student"}
              </button>
              {recognitionReady && <span className="recognition-badge">Ready for Recognition</span>}
              {adminMessage && <p className="panel-response">{adminMessage}</p>}
            </div>
          </section>
        ) : (
          <section className="glass-card security-panel">
            <div className="panel-header">
              <h2>Security Controls</h2>
              <span>Live incident response</span>
            </div>
            <div className="panel-form-group">
              <p className="security-note">
                Use your mobile alert tools and live camera details to monitor access quickly.
              </p>
              <button className="small-button" type="button" onClick={() => {
                refreshDashboard();
                loadUnauthorizedGallery();
              }}>
                ♻️ Refresh Everything
              </button>
              <p className="panel-response">
                Security users can view logs, camera feed, and unauthorized alerts here.
              </p>
            </div>
          </section>
        )}
      </div>

      <div className="dashboard-grid dashboard-main-grid">
        <section className="glass-card live-panel">
          <div className="panel-header">
            <h2>Live Camera</h2>
            <span>Realtime feed</span>
          </div>
          <div className={`live-preview ${pauseLiveFeed ? "feed-paused" : ""} ${currentStatus === "Unauthorized" ? "unauth-feed" : "auth-feed"}`}>
            <div className={`camera-status ${currentStatus === "Unauthorized" ? "unauth-status" : "auth-status"}`}>
              {currentStatus}
            </div>
            <img
              src={liveSrc}
              alt="Live security feed"
              className="video-frame"
              onError={(event) => {
                const img = event.currentTarget;
                img.src = `/snapshot?ts=${Date.now()}`;
              }}
            />
          </div>
          {pauseLiveFeed ? (
            <p className="panel-response">Live feed paused for admin registration. It will resume once registration ends.</p>
          ) : liveFeedResumed ? (
            <p className="panel-response">Registration complete. Live feed has resumed.</p>
          ) : (
            <p className="panel-note">Stream updates every second. For the full camera stream, open the video endpoint in a browser.</p>
          )}
        </section>

        <section className="glass-card log-panel">
          <div className="panel-header">
            <h2>Access Logs</h2>
            <span>{logs.length} recent entries</span>
          </div>
          <div className="log-list">
            {logs.length === 0 ? (
              <p className="empty-state">No logs available yet.</p>
            ) : (
              logs.map((line, index) => (
                <motion.p key={index} whileHover={{ x: 4 }}>
                  {line}
                </motion.p>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="dashboard-grid dashboard-main-grid">
        <section className="glass-card chart-panel">
          <div className="panel-header">
            <h2>Activity Analytics</h2>
            <span>Unauthorized trend</span>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="time" tick={{ fill: "#a2f1ff" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#a2f1ff" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "rgba(6, 18, 42, 0.95)", border: "1px solid rgba(0,255,255,0.2)", color: "#eafcff" }} />
              <Area type="monotone" dataKey="count" stroke="#00f6ff" fill="rgba(0,246,255,0.16)" strokeWidth={3} />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section className="glass-card gallery-panel">
          <div className="panel-header">
            <h2>Unauthorized Gallery</h2>
            <span>Recent flagged events</span>
          </div>
          <div className="gallery-grid">
            {unauthorizedImages.length === 0 ? (
              <div className="empty-state">No unauthorized events yet.</div>
            ) : (
              unauthorizedImages.map((item) => (
                <motion.div key={item.filename} whileHover={{ scale: 1.02 }} className="gallery-card">
                  <img src={item.url} alt={item.filename} className="gallery-image" />
                  <p>{item.timestamp}</p>
                </motion.div>
              ))
            )}
          </div>
        </section>
      </div>

      {showSuccessModal && (
        <div className="success-modal">
          <div className="success-card">
            <h2>✅ Student Registered Successfully</h2>
            <p>
              <strong>Name:</strong> {registeredStudent?.name}
            </p>
            <p>
              <strong>Roll:</strong> {registeredStudent?.roll}
            </p>
            <p>Status: Ready for Recognition</p>
            <button className="small-button" type="button" onClick={handleCloseSuccessModal}>
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Toggle({ label, active, onToggle }) {
  return (
    <div className="toggle-card" onClick={onToggle}>
      <div>
        <p>{label}</p>
        <span>{active ? "Enabled" : "Disabled"}</span>
      </div>
      <div className={`toggle-switch ${active ? "active" : ""}`}>
        <div className="toggle-thumb" />
      </div>
    </div>
  );
}