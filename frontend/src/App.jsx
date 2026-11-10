import { useState, useEffect, useRef } from "react";
import {
  BrainCircuit, LayoutDashboard, BookOpen,
  Target, TrendingUp, TrendingDown, Bell,
  Search, ChevronDown, Activity, Menu,
  FlaskConical, GraduationCap, History, CheckCircle2, ShieldAlert,
  GitFork, AlertTriangle
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import "./App.css";
import {
  login,
  getSkillAnalysis,
  getSkills,
  getSkillProfile,
  enrollSkill,
  getLearningOutcomes,
  getLearningEffectiveness,
  getSkillRecommendations,
  getSkillDiagnosis,
  getActivities,
  createActivity
} from "./api";

function App() {
  const [active, setActive] = useState("Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [apiStatus, setApiStatus] = useState("Checking backend...");

  const [loggedIn, setLoggedIn] = useState(
    Boolean(localStorage.getItem("cwip_token"))
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);

  const [regressionData, setRegressionData] = useState(null);
  const [statisticsData, setStatisticsData] = useState(null);
  const [analyticsError, setAnalyticsError] = useState("");
  const [skillsCatalogue, setSkillsCatalogue] = useState([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [skillsError, setSkillsError] = useState("");
  const [selectedSkillProfile, setSelectedSkillProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [enrollMessage, setEnrollMessage] = useState("");
  const [enrollingSkillId, setEnrollingSkillId] = useState(null);
  const [outcomes, setOutcomes] = useState([]);
  const [realOutcomes, setRealOutcomes] = useState([]);
  const [adherenceData, setAdherenceData] = useState(null);
  const [outcomesLoading, setOutcomesLoading] = useState(false);
  const [outcomesError, setOutcomesError] = useState("");
  const [effectivenessData, setEffectivenessData] = useState(null);
  const [effectivenessLoading, setEffectivenessLoading] = useState(false);
  const [effectivenessError, setEffectivenessError] = useState("");
  const [activities, setActivities] = useState([]);
  const [activitiesError, setActivitiesError] = useState("");
  const [recommendation, setRecommendation] = useState(null);
  const [recommendationError, setRecommendationError] = useState("");
  const [loadingRecommendation, setLoadingRecommendation] = useState(false);

  const [activityForm, setActivityForm] = useState({
    duration: 30,
    difficulty: "hard",
    score: 85,
    errors: 2,
    actualAction: "",
  });
  const [submittingActivity, setSubmittingActivity] = useState(false);
  const [activityMessage, setActivityMessage] = useState("");
  const [activityError, setActivityError] = useState("");

  useEffect(() => {
    if (!loggedIn) return;

    Promise.all([
      getSkillAnalysis(1),
      getSkillAnalysis(2),
    ])
      .then(([regression, statistics]) => {
        setRegressionData(regression);
        setStatisticsData(statistics);
        setApiStatus("Connected — 2 skills loaded");
        setAnalyticsError("");
      })
      .catch((error) => {
        setApiStatus(`API request failed: ${error.message}`);
        setAnalyticsError(error.message);
      });
  }, [loggedIn]);

  useEffect(() => {
    if (!loggedIn) return;

    async function loadOutcomes() {
      setOutcomesLoading(true);
      try {
        const [testData, realData] = await Promise.all([
          getLearningOutcomes(true),
          getLearningOutcomes(false),
        ]);

        setOutcomes(testData.outcomes ?? []);
        setRealOutcomes(realData.outcomes ?? []);
        setAdherenceData({
          adherenceRate: realData.adherence_rate ?? 0,
          totalRealEvaluated: realData.total_real_evaluated ?? 0,
          recommendationsFollowed: realData.recommendations_followed ?? 0,
          recommendationsNotFollowed: realData.recommendations_not_followed ?? 0,
        });
        setOutcomesError("");
      } catch (error) {
        setOutcomesError(error.message);
      } finally {
        setOutcomesLoading(false);
      }
    }

    loadOutcomes();
  }, [loggedIn]);

  async function loadEffectiveness() {
    setEffectivenessLoading(true);
    try {
      const data = await getLearningEffectiveness();
      setEffectivenessData(data);
      setEffectivenessError("");
    } catch (error) {
      setEffectivenessError(error.message);
    } finally {
      setEffectivenessLoading(false);
    }
  }

  useEffect(() => {
    if (!loggedIn) return;

    let ignore = false;
    getLearningEffectiveness()
      .then((data) => {
        if (!ignore) {
          setEffectivenessData(data);
          setEffectivenessError("");
        }
      })
      .catch((error) => {
        if (!ignore) {
          setEffectivenessError(error.message);
        }
      })
      .finally(() => {
        if (!ignore) {
          setEffectivenessLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [loggedIn]);

  useEffect(() => {
    if (!loggedIn) return;

    let ignore = false;

    getSkills()
      .then((data) => {
        if (!ignore) {
          setSkillsCatalogue(data.skills ?? []);
          setSkillsError("");
        }
      })
      .catch((error) => {
        if (!ignore) {
          setSkillsError(error.message);
        }
      })
      .finally(() => {
        if (!ignore) {
          setSkillsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [loggedIn]);

  useEffect(() => {
    if (!loggedIn) return;

    getActivities()
      .then((data) => {
        setActivities(data.activities ?? []);
        setActivitiesError("");
      })
      .catch((error) => {
        setActivitiesError(error.message);
      });
  }, [loggedIn]);

  async function refreshSkills() {
    setSkillsLoading(true);
    try {
      const data = await getSkills();
      setSkillsCatalogue(data.skills ?? []);
      setSkillsError("");
    } catch (error) {
      setSkillsError(error.message);
    } finally {
      setSkillsLoading(false);
    }
  }

  async function handleEnroll(skillId) {
    setEnrollingSkillId(skillId);
    setEnrollMessage("");
    setSkillsError("");
    try {
      const result = await enrollSkill(skillId);
      setEnrollMessage(result.message || "Enrolled successfully!");
      await refreshSkills();
      if (selectedSkillProfile && selectedSkillProfile.skill_id === skillId) {
        const updatedProfile = await getSkillProfile(skillId);
        setSelectedSkillProfile(updatedProfile);
      }
    } catch (error) {
      setSkillsError(error.message);
    } finally {
      setEnrollingSkillId(null);
    }
  }

  async function handleViewProfile(skillId) {
    setProfileLoading(true);
    setProfileError("");
    try {
      const profile = await getSkillProfile(skillId);
      setSelectedSkillProfile(profile);
    } catch (error) {
      setProfileError(error.message);
    } finally {
      setProfileLoading(false);
    }
  }

  // Dynamic skills derived from the database catalogue
  const skillPalette = [
    "#6758e8",
    "#0891b2",
    "#10b981",
    "#f59e0b",
    "#ec4899",
    "#8b5cf6",
  ];
  const skills = skillsCatalogue.map((s, idx) => {
    const data =
      s.name === "Regression"
        ? regressionData
        : s.name === "Statistics"
        ? statisticsData
        : null;

    return {
      id: s.id,
      name: s.name,
      description: s.description,
      category: s.category,
      is_enrolled: s.is_enrolled,
      mastery:
        s.mastery != null
          ? Number((s.mastery * 100).toFixed(1))
          : data
          ? Number((data.mastery * 100).toFixed(1))
          : null,
      confidence:
        s.confidence != null ? s.confidence : data ? data.confidence : null,
      trend:
        data?.trend ??
        (s.is_enrolled
          ? s.mastery != null
            ? "stable"
            : "insufficient_data"
          : "Not enrolled"),
      data: data,
      color: skillPalette[idx % skillPalette.length],
    };
  });

  const enrolledSkills = skills.filter((skill) => skill.is_enrolled);
  const loadedSkills = enrolledSkills.filter((skill) => skill.mastery !== null);

  const overallMastery = loadedSkills.length
    ? loadedSkills.reduce((total, skill) => total + skill.mastery, 0) /
      loadedSkills.length
    : null;

  const improvingSkills = loadedSkills.filter(
    (skill) => skill.trend === "improving"
  ).length;

  // Chart data derived from real activity records
  const chartData = [...activities]
    .filter((item) => item.score != null)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    .map((item) => ({
      date: new Date(item.timestamp).toLocaleDateString(),
      skill: item.topic,
      score: item.score,
    }));

  const averageActivityScore = chartData.length
    ? chartData.reduce((sum, item) => sum + item.score, 0) / chartData.length
    : 0;

  const totalStudyMinutes = activities.reduce(
    (sum, item) => sum + (item.duration || 0),
    0
  );

  async function submitRecommendedActivity(event) {
    event.preventDefault();
    setSubmittingActivity(true);
    setActivityMessage("");
    setActivityError("");

    const sessionId =
      recommendation?.recommendation_session_id ||
      recommendation?.recommendations?.[0]?.recommendation_session_id;
    const item = recommendation?.recommendations?.[0];

    if (!sessionId || !item) {
      setActivityError("Generate a recommendation before submitting an activity.");
      setSubmittingActivity(false);
      return;
    }

    try {
      if (!activityForm.actualAction) {
        setActivityError("Please select the action you actually performed.");
        setSubmittingActivity(false);
        return;
      }

      // Explicitly distinguish target skill from remediation skill:
      // For prerequisite recommendations, the activity topic must be the remediation skill
      // (the weak foundational skill to practice) to match the recommendation session skill.
      const practiceTopic = item.remediation_skill || item.target_skill;

      const result = await createActivity({
        activity_type: activityForm.actualAction,
        subject: "Mathematics",
        topic: practiceTopic,
        duration: Number(activityForm.duration),
        difficulty: activityForm.difficulty,
        score: Number(activityForm.score),
        errors: Number(activityForm.errors),
        recommendation_session_id: sessionId,
      });

      setActivityMessage(
        result.outcome_created
          ? "Activity saved and learning outcome recorded."
          : "Activity saved successfully."
      );

      const [
        regression,
        statistics,
        testData,
        realData,
        activityData,
        effData,
        skillsData,
      ] = await Promise.all([
        getSkillAnalysis(1),
        getSkillAnalysis(2),
        getLearningOutcomes(true),
        getLearningOutcomes(false),
        getActivities(),
        getLearningEffectiveness(),
        getSkills(),
      ]);

      setRegressionData(regression);
      setStatisticsData(statistics);
      setOutcomes(testData.outcomes ?? []);
      setRealOutcomes(realData.outcomes ?? []);
      setAdherenceData({
        adherenceRate: realData.adherence_rate ?? 0,
        totalRealEvaluated: realData.total_real_evaluated ?? 0,
        recommendationsFollowed: realData.recommendations_followed ?? 0,
        recommendationsNotFollowed: realData.recommendations_not_followed ?? 0,
      });
      setActivities(activityData.activities ?? []);
      setEffectivenessData(effData);
      setSkillsCatalogue(skillsData.skills ?? []);
    } catch (error) {
      setActivityError(error.message);
    } finally {
      setSubmittingActivity(false);
    }
  }

  async function loadRecommendation(skillId) {
    const targetSkillId = skillId ?? (enrolledSkills.length > 0 ? enrolledSkills[0].id : 1);
    setLoadingRecommendation(true);
    setRecommendationError("");
    setRecommendation(null);

    try {
      const data = await getSkillRecommendations(targetSkillId);
      setRecommendation(data);
      setActive("Recommendations");
    } catch (error) {
      setRecommendationError(error.message);
    } finally {
      setLoadingRecommendation(false);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setLoginError("");
    setLoggingIn(true);

    try {
      await login(email, password);
      setLoggedIn(true);
    } catch (error) {
      setLoginError(error.message);
    } finally {
      setLoggingIn(false);
    }
  }

  if (!loggedIn) {
    return (
      <div className="login-page">
        <form className="login-card" onSubmit={handleLogin}>
          <div className="brand-icon login-logo">
            <BrainCircuit size={28} />
          </div>

          <p className="eyebrow">AI COGNITIVE WORKFLOW INTELLIGENCE</p>
          <h1>Welcome to CWIP</h1>
          <p className="subtitle">
            Sign in to explore your personalized learning insights.
          </p>

          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {loginError && (
            <p className="login-error" role="alert">{loginError}</p>
          )}

          <button className="primary-button login-submit" disabled={loggingIn}>
            {loggingIn ? "Signing in..." : "Sign in to CWIP"}
            {!loggingIn && <span>→</span>}
          </button>

          <p className="login-footer">
            Secure access to your learning workspace
          </p>
        </form>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon"><BrainCircuit size={25} /></div>
          <div><strong>CWIP</strong><small>Learning intelligence</small></div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        {[
          ["Overview",                LayoutDashboard],
          ["My Skills",               BookOpen],
          ["Recommendations",         Target],
          ["Learning Progress",       TrendingUp],
          ["Learning Outcome History", History],
        ].map(([label, Icon]) => (
          <button
            key={label}
            className={`nav-item ${active === label ? "active" : ""}`}
            onClick={() => { setActive(label); setMenuOpen(false); }}
          >
            <Icon size={19} /> {label}
          </button>
        ))}

        <div className="sidebar-bottom">
          <div className="status-dot" />
          <div><strong>Intelligence engine</strong><small>Development model</small></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            <Menu size={21} />
          </button>

          <div className="breadcrumb">Workspace <span>/</span> {active}</div>

          <div className="top-actions">
            <button className="icon-button" aria-label="Search"><Search size={19} /></button>
            <button className="icon-button" aria-label="Notifications"><Bell size={19} /></button>
            <div className="avatar">AS</div>
            <span className="profile-name">Learner</span>
            <ChevronDown size={16} />
          </div>
        </header>

        <div className="page-content">
          <p style={{ fontSize: 12, color: "#6758e8" }}>
            Backend: {apiStatus}
          </p>

          {analyticsError && (
            <p style={{ fontSize: 12, color: "#c24141" }}>
              Analytics error: {analyticsError}
            </p>
          )}

          {outcomesError && (
            <p style={{ fontSize: 12, color: "#c24141" }} role="alert">
              Outcomes error: {outcomesError}
            </p>
          )}

          <div className="welcome-row">
            <div>
              <p className="eyebrow">YOUR LEARNING WORKSPACE</p>
              <h1>{active === "Overview" ? "Learning overview" : active}</h1>
              <p className="subtitle">
                Understand your progress. Discover your next step.
              </p>
            </div>
            <div className="date-chip"><Activity size={16} /> AI-powered insights</div>
          </div>

          {active === "Learning Progress" ? (
            <LearningProgress
              chartData={chartData}
              averageActivityScore={averageActivityScore}
              totalStudyMinutes={totalStudyMinutes}
              effectivenessData={effectivenessData}
              effectivenessLoading={effectivenessLoading}
              effectivenessError={effectivenessError}
              onRefreshEffectiveness={loadEffectiveness}
            />
          ) : active === "My Skills" ? (
            <MySkills
              skills={skills}
              loading={skillsLoading}
              error={skillsError}
              enrollMessage={enrollMessage}
              enrollingSkillId={enrollingSkillId}
              onEnroll={handleEnroll}
              onViewProfile={handleViewProfile}
              onRecommend={loadRecommendation}
              onRefreshSkills={refreshSkills}
            />
          ) : active === "Recommendations" ? (
            <RecommendationsPage
              enrolledSkills={enrolledSkills}
              recommendation={recommendation}
              loading={loadingRecommendation}
              error={recommendationError}
              onGenerate={loadRecommendation}
              activityForm={activityForm}
              setActivityForm={setActivityForm}
              onSubmitActivity={submitRecommendedActivity}
              submittingActivity={submittingActivity}
              activityMessage={activityMessage}
              activityError={activityError}
              onNavigateToSkills={() => setActive("My Skills")}
            />
          ) : active === "Learning Outcome History" ? (
            <LearningOutcomeHistory
              testOutcomes={outcomes}
              realOutcomes={realOutcomes}
            />
          ) : (
            <>
              <section className="metrics-grid">
                <Metric
                  title="Overall mastery"
                  value={overallMastery === null ? "Loading..." : `${overallMastery.toFixed(1)}%`}
                  note="Across tracked skills"
                  icon={BrainCircuit}
                />
                <Metric
                  title="Skills tracked"
                  value={loadedSkills.length}
                  note="Continue building your profile"
                  icon={BookOpen}
                />
                <Metric
                  title="Improving skills"
                  value={improvingSkills}
                  note="Based on current metrics"
                  icon={TrendingUp}
                />
                <Metric
                  title="Action adherence rate"
                  value={
                    outcomesLoading
                      ? "Loading..."
                      : outcomesError
                      ? "—"
                      : adherenceData
                      ? `${adherenceData.adherenceRate.toFixed(1)}%`
                      : "Loading..."
                  }
                  details={
                    outcomesLoading
                      ? "Fetching adherence..."
                      : outcomesError
                      ? outcomesError
                      : adherenceData
                      ? `${adherenceData.recommendationsFollowed} / ${adherenceData.totalRealEvaluated} followed (${adherenceData.recommendationsNotFollowed} not followed)`
                      : "—"
                  }
                  note={
                    adherenceData && adherenceData.totalRealEvaluated === 0
                      ? "Self-reported by learner (No real outcomes yet)"
                      : "Self-reported by learner"
                  }
                  disclaimer="Adherence tracking only · Not learning effectiveness"
                  icon={CheckCircle2}
                />
                <Metric
                  title="Real learner outcomes"
                  value={outcomesLoading ? "Loading..." : realOutcomes.length}
                  note="Non-test outcome records"
                  icon={GraduationCap}
                />
                <Metric
                  title="Test outcomes"
                  value={outcomesLoading ? "Loading..." : outcomes.length}
                  note="Prototype validation records"
                  icon={FlaskConical}
                />
              </section>

              <section className="content-grid">
                <div className="panel skills-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Skill mastery</h2>
                      <p>Estimated mastery by skill</p>
                    </div>
                    <button className="text-button" onClick={() => setActive("My Skills")}>
                      View skills ↗
                    </button>
                  </div>

                  {skills.map((skill) => (
                    <div className="skill-row" key={skill.name}>
                      <div className="skill-top">
                        <span>{skill.name}</span>
                        <strong>
                          {skill.mastery === null ? "Loading..." : `${skill.mastery}%`}
                        </strong>
                      </div>
                      <div className="progress-track">
                        <div
                          className="progress-fill"
                          style={{
                            width: `${skill.mastery ?? 0}%`,
                            background: skill.color,
                          }}
                        />
                      </div>
                      <div className="skill-foot">
                        <span>{skill.trend}</span>
                        <span>Mastery estimate</span>
                      </div>
                    </div>
                  ))}

                  <p className="demo-note">
                    Regression and Statistics are live from the API.
                  </p>
                </div>

                <div className="panel recommendation-panel">
                  <div className="recommend-icon"><BrainCircuit size={23} /></div>
                  <p className="eyebrow">RECOMMENDED NEXT STEP</p>
                  <h2>Challenge your Regression skills</h2>
                  <p className="recommend-description">
                    {regressionData
                      ? `Your latest Regression mastery estimate is ${(regressionData.mastery * 100).toFixed(1)}%. Your recent average is ${regressionData.recent_average}.`
                      : "Loading your Regression analytics..."}
                  </p>

                  {recommendation?.recommendations?.map((item, index) => (
                    <div key={`${item.action_code}-${index}`}>
                      <strong>{item.action_code.replaceAll("_", " ")}</strong>
                      <p>{item.message}</p>
                      <small>{item.reason}</small>
                    </div>
                  ))}

                  {recommendationError && (
                    <p className="login-error" role="alert">
                      {recommendationError}
                    </p>
                  )}

                  <div className="recommend-meta">
                    <span>Development model</span>
                    <span>Hard practice</span>
                  </div>
                  <button
                    className="primary-button"
                    onClick={loadRecommendation}
                  >
                    {loadingRecommendation ? "Loading..." : "View recommendations"} <span>→</span>
                  </button>
                </div>
              </section>

              <section className="panel activity-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Recent learning activity</h2>
                    <p>Latest activity records from the database</p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setActive("Learning Progress")}
                  >
                    View progress ↗
                  </button>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>SKILL</th>
                        <th>ACTIVITY TYPE</th>
                        <th>SCORE</th>
                        <th>DATE &amp; TIME</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activities.map((item) => (
                        <tr key={item.id}>
                          <td><strong>{item.topic}</strong></td>
                          <td>{item.activity_type.replaceAll("_", " ")}</td>
                          <td>{item.score == null ? "—" : `${item.score}%`}</td>
                          <td>
                            {item.timestamp
                              ? new Date(item.timestamp).toLocaleString()
                              : "—"}
                          </td>
                        </tr>
                      ))}

                      {activities.length === 0 && !activitiesError && (
                        <tr>
                          <td colSpan={4}>Loading activities or no activities recorded.</td>
                        </tr>
                      )}

                      {activitiesError && (
                        <tr>
                          <td colSpan={4}>Could not load activities: {activitiesError}</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <p className="demo-note">
                  Showing latest 10 activities from the database.
                </p>
              </section>

              <footer>
                CWIP · AI Cognitive Workflow Intelligence Platform{" "}
                <span>Learning insights for better outcomes</span>
              </footer>
            </>
          )}
        </div>
      </main>

      {(selectedSkillProfile || profileLoading) && (
        <SkillProfileModal
          profile={selectedSkillProfile}
          loading={profileLoading}
          error={profileError}
          onClose={() => {
            setSelectedSkillProfile(null);
            setProfileError("");
          }}
          onEnroll={handleEnroll}
          onRecommend={(skillId) => {
            setSelectedSkillProfile(null);
            loadRecommendation(skillId);
          }}
          enrolling={enrollingSkillId === selectedSkillProfile?.skill_id}
        />
      )}
    </div>
  );
}

function RecommendationsPage({
  enrolledSkills = [],
  recommendation,
  loading,
  error,
  onGenerate,
  activityForm,
  setActivityForm,
  onSubmitActivity,
  submittingActivity,
  activityMessage,
  activityError,
  onNavigateToSkills,
}) {
  const [selectedSkillId, setSelectedSkillId] = useState("");

  const activeSkillId = selectedSkillId
    ? Number(selectedSkillId)
    : enrolledSkills.length > 0
    ? enrolledSkills[0].id
    : null;

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Personalized recommendations</h2>
          <p>Suggested next steps based on your learning analytics.</p>
        </div>
      </div>

      {error && (
        <p className="login-error" role="alert">{error}</p>
      )}

      {enrolledSkills.length === 0 ? (
        <div
          style={{
            padding: "24px",
            textAlign: "center",
            background: "#f8fafc",
            borderRadius: "8px",
            border: "1px dashed #cbd5e1",
            margin: "16px 0",
          }}
        >
          <p style={{ fontWeight: 600, color: "#475569", marginBottom: "8px" }}>
            No enrolled skills found
          </p>
          <p style={{ fontSize: 13, color: "#64748b", marginBottom: "16px" }}>
            You must be enrolled in at least one skill to generate personalized learning recommendations.
          </p>
          {onNavigateToSkills && (
            <button
              type="button"
              className="primary-button"
              onClick={onNavigateToSkills}
            >
              Browse Skill Catalogue
            </button>
          )}
        </div>
      ) : (
        <>
          {!recommendation && !loading && (
            <p>Select a skill below and generate a recommendation to see your next learning step.</p>
          )}

          {recommendation?.recommendations?.map((item, index) => {
            const isPrereq = item.action_code === "practice_prerequisite";
            return (
              <div
                key={`${item.action_code}-${index}`}
                className="recommendation-item"
                style={isPrereq ? { borderLeft: "4px solid #f59e0b", background: "#fffdfa" } : {}}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                  <h3 style={{ margin: 0 }}>{item.action_code.replaceAll("_", " ")}</h3>
                  {isPrereq && (
                    <span className="prereq-badge-bottleneck">
                      <GitFork size={13} />
                      {item.is_direct === false ? `Foundational Root (Distance ${item.distance || 2})` : "Direct Prerequisite"}
                    </span>
                  )}
                </div>

                <p style={{ marginTop: "8px" }}>
                  <strong>Practice target:</strong> {item.target_skill}
                </p>

                {item.path_names && item.path_names.length > 1 && (
                  <div style={{ marginBottom: "8px" }}>
                    <span className="prereq-chain-path">
                      Dependency chain: {item.path_names.join(" → ")}
                    </span>
                  </div>
                )}

                <p>{item.message}</p>
                <p><strong>Rationale:</strong> {item.explanation || item.reason}</p>
                <p>
                  <strong>{isPrereq ? "Prerequisite mastery:" : "Current mastery:"}</strong>{" "}
                  {typeof item.mastery === "number"
                    ? `${(item.mastery * 100).toFixed(1)}%`
                    : "—"}
                </p>
                <p>
                  <strong>{isPrereq ? "Risk score:" : "Mastery deficit:"}</strong>{" "}
                  {typeof item.risk === "number"
                    ? `${(item.risk * 100).toFixed(1)}%`
                    : "—"}
                </p>
              </div>
            );
          })}

          {recommendation?.recommendations?.length > 0 && (
            <form className="activity-form" onSubmit={onSubmitActivity}>
              <div className="panel-heading">
                <div>
                  <h2>Complete recommended activity</h2>
                  <p>Record your result to evaluate this recommendation.</p>
                </div>
              </div>

              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="actual-action">What did you actually do?</label>
                  <select
                    id="actual-action"
                    value={activityForm.actualAction}
                    onChange={(event) =>
                      setActivityForm({
                        ...activityForm,
                        actualAction: event.target.value,
                      })
                    }
                    required
                  >
                    <option value="">Select an action</option>
                    <option value="practice_current">Practice current skill</option>
                    <option value="practice_prerequisite">Practice prerequisite</option>
                    <option value="review_concept">Review concept</option>
                    <option value="easy_practice">Easy practice</option>
                    <option value="hard_practice">Hard practice</option>
                    <option value="take_assessment">Take assessment</option>
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="activity-duration">Duration (minutes)</label>
                  <input
                    id="activity-duration"
                    type="number"
                    min="1"
                    max="600"
                    required
                    value={activityForm.duration}
                    onChange={(e) =>
                      setActivityForm({ ...activityForm, duration: e.target.value })
                    }
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="activity-difficulty">Difficulty</label>
                  <select
                    id="activity-difficulty"
                    value={activityForm.difficulty}
                    onChange={(e) =>
                      setActivityForm({ ...activityForm, difficulty: e.target.value })
                    }
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>

                <div className="form-field">
                  <label htmlFor="activity-score">Score (0–100)</label>
                  <input
                    id="activity-score"
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    required
                    value={activityForm.score}
                    onChange={(e) =>
                      setActivityForm({ ...activityForm, score: e.target.value })
                    }
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="activity-errors">Errors</label>
                  <input
                    id="activity-errors"
                    type="number"
                    min="0"
                    max="1000"
                    required
                    value={activityForm.errors}
                    onChange={(e) =>
                      setActivityForm({ ...activityForm, errors: e.target.value })
                    }
                  />
                </div>
              </div>

              {activityMessage && (
                <p className="activity-success" role="status">
                  {activityMessage}
                </p>
              )}

              {activityError && (
                <p className="login-error" role="alert">
                  {activityError}
                </p>
              )}

              <button
                type="submit"
                className="primary-button"
                disabled={submittingActivity}
              >
                {submittingActivity
                  ? "Saving activity..."
                  : "Submit activity and evaluate outcome"}
                {!submittingActivity && <span>→</span>}
              </button>
            </form>
          )}

          <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid #e2e8f0", display: "flex", gap: "12px", alignItems: "flex-end", flexWrap: "wrap" }}>
            <div className="form-field" style={{ minWidth: "220px", marginBottom: 0 }}>
              <label htmlFor="target-skill-select" style={{ fontWeight: 600 }}>
                Target skill
              </label>
              <select
                id="target-skill-select"
                value={activeSkillId || ""}
                onChange={(e) => setSelectedSkillId(e.target.value)}
                disabled={loading}
              >
                {enrolledSkills.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} {s.mastery != null ? `(${s.mastery.toFixed(1)}%)` : ""}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              className="primary-button"
              onClick={() => {
                if (activeSkillId) {
                  onGenerate(activeSkillId);
                }
              }}
              disabled={loading || !activeSkillId}
            >
              {loading ? "Generating..." : "Generate recommendation"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

function MySkills({
  skills = [],
  loading = false,
  error = "",
  enrollMessage = "",
  enrollingSkillId = null,
  onEnroll,
  onViewProfile,
  onRecommend,
  onRefreshSkills,
}) {
  const enrolledSkills = skills.filter((s) => s.is_enrolled);
  const availableSkills = skills.filter((s) => !s.is_enrolled);

  return (
    <section className="my-skills-page">
      <div className="panel" style={{ marginBottom: "20px" }}>
        <div className="panel-heading">
          <div>
            <h2>Skill Catalogue & Profiles</h2>
            <p>Discover platform skills, enroll in new domains, and inspect learning progress</p>
          </div>
          {onRefreshSkills && (
            <button
              type="button"
              className="tab-toggle-btn"
              onClick={onRefreshSkills}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh catalogue"}
            </button>
          )}
        </div>

        {enrollMessage && (
          <p className="activity-success" role="status" style={{ margin: "12px 0 0" }}>
            {enrollMessage}
          </p>
        )}

        {error && (
          <p className="login-error" role="alert" style={{ margin: "12px 0 0" }}>
            {error}
          </p>
        )}
      </div>

      {loading && skills.length === 0 ? (
        <p style={{ color: "#666c85" }}>Loading skill catalogue...</p>
      ) : skills.length === 0 ? (
        <div className="panel" style={{ textAlign: "center", padding: "32px" }}>
          <p style={{ color: "#666c85", margin: 0 }}>No skills available in the catalogue.</p>
        </div>
      ) : (
        <>
          <div className="catalogue-section-heading">
            <div>
              <h2>Enrolled skills ({enrolledSkills.length})</h2>
              <p>Active skills currently tracked in your learning workflow</p>
            </div>
          </div>

          {enrolledSkills.length === 0 ? (
            <div className="panel" style={{ padding: "24px", textAlign: "center" }}>
              <p style={{ color: "#666c85", margin: 0 }}>
                You have not enrolled in any skills yet. Explore the catalogue below to start your learning path.
              </p>
            </div>
          ) : (
            <div className="metrics-grid">
              {enrolledSkills.map((skill) => {
                const data = skill.data;
                const masteryDisplay =
                  skill.mastery !== null
                    ? `${skill.mastery.toFixed(1)}%`
                    : "Not evaluated";

                return (
                  <div className="panel" key={skill.id || skill.name}>
                    <div className="panel-heading">
                      <div>
                        <h2>{skill.name}</h2>
                        <span className="skill-category-badge">{skill.category || "General"}</span>
                      </div>
                      <div className="metric-icon">
                        <BookOpen size={20} />
                      </div>
                    </div>

                    {skill.description && (
                      <p className="skill-description-text">{skill.description}</p>
                    )}

                    <div className="skill-top" style={{ marginTop: "16px" }}>
                      <span>Mastery</span>
                      <strong>{masteryDisplay}</strong>
                    </div>
                    <div className="progress-track">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${skill.mastery != null ? Math.min(skill.mastery, 100) : 0}%`,
                          background: skill.color,
                        }}
                      />
                    </div>

                    <div className="skill-details">
                      <div>
                        <span>Average score</span>
                        <strong>{data ? `${data.average_score}%` : "—"}</strong>
                      </div>
                      <div>
                        <span>Recent average</span>
                        <strong>{data ? `${data.recent_average}%` : "—"}</strong>
                      </div>
                      <div>
                        <span>Confidence</span>
                        <strong>
                          {skill.confidence != null
                            ? `${(skill.confidence * 100).toFixed(0)}%`
                            : "—"}
                        </strong>
                      </div>
                      <div>
                        <span>Activities analyzed</span>
                        <strong>{data ? data.activities_analyzed : "—"}</strong>
                      </div>
                      <div>
                        <span>Trend</span>
                        <strong className="trend-value">
                          {skill.trend}
                        </strong>
                      </div>
                    </div>

                    <div className="skill-action-row">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => onViewProfile(skill.id)}
                      >
                        View profile
                      </button>
                      <button
                        type="button"
                        className="primary-button"
                        style={{ marginTop: 0 }}
                        onClick={() => onRecommend(skill.id)}
                      >
                        Get recommendation <span>→</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {availableSkills.length > 0 && (
            <>
              <div className="catalogue-section-heading">
                <div>
                  <h2>Available skills catalogue ({availableSkills.length})</h2>
                  <p>Discover and enroll in new skills to begin tracking adaptive progress</p>
                </div>
              </div>

              <div className="metrics-grid">
                {availableSkills.map((skill) => (
                  <div className="panel skill-card-unenrolled" key={skill.id || skill.name}>
                    <div className="panel-heading">
                      <div>
                        <h2>{skill.name}</h2>
                        <span className="skill-category-badge">{skill.category || "General"}</span>
                      </div>
                      <div className="metric-icon">
                        <GraduationCap size={20} />
                      </div>
                    </div>

                    <p className="skill-description-text">
                      {skill.description || "Comprehensive skill unit ready for study and evaluation."}
                    </p>

                    <div className="skill-action-row" style={{ marginTop: "24px" }}>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => onViewProfile(skill.id)}
                      >
                        View details
                      </button>
                      <button
                        type="button"
                        className="primary-button"
                        style={{ marginTop: 0 }}
                        onClick={() => onEnroll(skill.id)}
                        disabled={enrollingSkillId === skill.id}
                      >
                        {enrollingSkillId === skill.id ? "Enrolling..." : "Enroll in skill"} <span>+</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}

function SkillProfileModal({
  profile,
  loading = false,
  error = "",
  onClose,
  onEnroll,
  onRecommend,
  enrolling = false,
}) {
  const modalRef = useRef(null);
  const closeButtonRef = useRef(null);
  const [diagnosis, setDiagnosis] = useState(null);
  const [loadingDiagnosis, setLoadingDiagnosis] = useState(Boolean(profile?.skill_id));
  const [diagnosisError, setDiagnosisError] = useState("");

  useEffect(() => {
    closeButtonRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!profile?.skill_id) return;
    let ignore = false;
    getSkillDiagnosis(profile.skill_id)
      .then((data) => {
        if (!ignore) {
          setDiagnosis(data);
          setDiagnosisError("");
          setLoadingDiagnosis(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setDiagnosisError(err.message || "Failed to load prerequisite intelligence");
          setLoadingDiagnosis(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [profile?.skill_id]);

  const formatChange = (val) => {
    if (val == null) return "—";
    const pp = val * 100;
    const sign = pp > 0 ? "+" : "";
    return `${sign}${pp.toFixed(1)} pp`;
  };

  const formatAction = (action) => (action ? action.replaceAll("_", " ") : "—");

  return (
    <div
      className="outcome-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="skill-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="outcome-modal" ref={modalRef} style={{ maxWidth: "780px" }}>
        <div className="panel-heading" style={{ marginBottom: "20px" }}>
          <div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <h2 id="skill-modal-title" style={{ margin: 0 }}>
                {profile?.name || "Skill profile"}
              </h2>
              {profile?.category && (
                <span className="skill-category-badge">{profile.category}</span>
              )}
            </div>
            <p style={{ margin: "4px 0 0" }}>
              {profile?.description || "Skill overview and empirical performance profile"}
            </p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="secondary-button"
            onClick={onClose}
            aria-label="Close skill profile modal"
            style={{ padding: "6px 12px", minWidth: "auto" }}
          >
            ✕
          </button>
        </div>

        {loading ? (
          <p style={{ color: "#666c85" }}>Loading skill profile...</p>
        ) : error ? (
          <div className="login-error" role="alert">{error}</div>
        ) : profile ? (
          <>
            <div className="skill-profile-grid">
              <div className="metric-card">
                <p>Enrollment status</p>
                <h2 style={{ fontSize: "16px", marginTop: "4px" }}>
                  {profile.is_enrolled ? "Enrolled" : "Not enrolled"}
                </h2>
                <span style={{ fontSize: "11px", color: "#8a8ea4" }}>
                  {profile.enrolled_at
                    ? `Since ${new Date(profile.enrolled_at).toLocaleDateString()}`
                    : "Not enrolled"}
                </span>
              </div>
              <div className="metric-card">
                <p>Mastery score</p>
                <h2>
                  {profile.mastery != null
                    ? `${(profile.mastery * 100).toFixed(1)}%`
                    : "—"}
                </h2>
                <span style={{ fontSize: "11px", color: "#8a8ea4" }}>
                  Confidence: {profile.confidence != null ? `${(profile.confidence * 100).toFixed(0)}%` : "—"}
                </span>
              </div>
              <div className="metric-card">
                <p>Skill trend</p>
                <h2 style={{ fontSize: "18px", textTransform: "capitalize", color: profile.trend === "improving" ? "#16b881" : "#4b3ba8" }}>
                  {profile.trend}
                </h2>
                <span style={{ fontSize: "11px", color: "#8a8ea4" }}>
                  {profile.total_activities} logged activities
                </span>
              </div>
            </div>

            <div className="panel" style={{ background: "#fafafc", padding: "16px", marginBottom: "16px", border: "1px solid #e9eaf2" }}>
              <h3 style={{ margin: "0 0 8px", fontSize: "13px", fontWeight: 700, color: "#475569" }}>
                Recent activity
              </h3>
              {profile.recent_activity ? (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                  <div>
                    <strong style={{ textTransform: "capitalize", fontSize: "14px" }}>
                      {formatAction(profile.recent_activity.activity_type)}
                    </strong>
                    <span style={{ fontSize: "12px", color: "#77819a", marginLeft: "10px" }}>
                      Difficulty: {profile.recent_activity.difficulty} · Duration: {profile.recent_activity.duration}m
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: "16px", fontWeight: 700, color: "#6758e8" }}>
                      Score: {profile.recent_activity.score ?? "—"}%
                    </span>
                  </div>
                </div>
              ) : (
                <p style={{ margin: 0, fontSize: "12px", color: "#77819a" }}>
                  No activities recorded yet for this skill.
                </p>
              )}
            </div>

            <div className="panel" style={{ background: "#fafafc", padding: "16px", marginBottom: "20px", border: "1px solid #e9eaf2" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: "13px", fontWeight: 700, color: "#475569" }}>
                Outcome evaluation & adherence ({profile.total_real_evaluated} evaluated real outcomes)
              </h3>
              <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", marginBottom: "12px" }}>
                <span className="badge badge-success">{profile.positive_outcomes} positive</span>
                <span className="badge badge-neutral">{profile.neutral_outcomes} neutral</span>
                <span className="badge badge-danger">{profile.negative_outcomes} negative</span>
                <span style={{ fontSize: "12px", color: "#666c85", marginLeft: "auto" }}>
                  Average Δ mastery: <strong>{formatChange(profile.average_mastery_change)}</strong>
                </span>
              </div>
              {profile.adherence ? (
                <div style={{ fontSize: "12px", color: "#555b72", borderTop: "1px solid #eeeef4", paddingTop: "8px" }}>
                  Adherence rate: <strong>{profile.adherence.adherence_rate}%</strong> (
                  {profile.adherence.recommendations_followed} followed, {profile.adherence.recommendations_not_followed} not followed)
                </div>
              ) : (
                <div style={{ fontSize: "11px", color: "#8a8ea4" }}>
                  No evaluated outcome records available to calculate adherence yet.
                </div>
              )}
            </div>

            <div className="prereq-panel" style={{ marginBottom: "20px" }}>
              <div className="prereq-heading">
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <GitFork size={16} color="#6758e8" />
                  <h3>Prerequisite & Dependency Intelligence</h3>
                </div>
                {diagnosis?.prerequisites?.length > 0 && (
                  <span style={{ fontSize: "12px", color: "#64748b" }}>
                    {diagnosis.prerequisites.length} prerequisite{diagnosis.prerequisites.length > 1 ? "s" : ""} across graph
                  </span>
                )}
              </div>

              {loadingDiagnosis ? (
                <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
                  Analyzing prerequisite graph dependencies...
                </p>
              ) : diagnosisError ? (
                <p style={{ fontSize: "12px", color: "#ef4444", margin: 0 }}>
                  Prerequisite analysis error: {diagnosisError}
                </p>
              ) : diagnosis ? (
                <>
                  {diagnosis.primary_gap ? (
                    <div className="prereq-insight-box gap-detected">
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <AlertTriangle size={15} color="#ef4444" />
                          <div className="prereq-insight-title" style={{ margin: 0 }}>
                            Primary Bottleneck: {diagnosis.primary_gap.name} ({diagnosis.primary_gap.is_direct ? "Direct" : `Foundational, Level ${diagnosis.primary_gap.distance}`})
                          </div>
                        </div>
                        <button
                          type="button"
                          className="secondary-button"
                          style={{ fontSize: "11px", padding: "3px 8px" }}
                          onClick={() => onRecommend(diagnosis.primary_gap.skill_id)}
                        >
                          Target bottleneck →
                        </button>
                      </div>
                      <p className="prereq-insight-text" style={{ marginTop: "6px" }}>
                        {diagnosis.primary_gap.explanation}
                      </p>
                      {diagnosis.primary_gap.chain_path && (
                        <div className="prereq-chain-path" style={{ marginTop: "6px" }}>
                          Dependency chain: {diagnosis.primary_gap.chain_path}
                        </div>
                      )}
                    </div>
                  ) : diagnosis.has_prerequisites ? (
                    <div className="prereq-insight-box healthy">
                      <div className="prereq-insight-title">
                        All Prerequisite Foundations Healthy
                      </div>
                      <p className="prereq-insight-text">
                        {diagnosis.diagnosis_summary}
                      </p>
                    </div>
                  ) : (
                    <div className="prereq-insight-box">
                      <div className="prereq-insight-title">
                        Foundational Skill
                      </div>
                      <p className="prereq-insight-text">
                        {diagnosis.diagnosis_summary}
                      </p>
                    </div>
                  )}

                  {diagnosis.prerequisites && diagnosis.prerequisites.length > 0 && (
                    <div className="prereq-chain-list" style={{ marginTop: "12px" }}>
                      {diagnosis.prerequisites.map((p) => {
                        const isBottleneck = diagnosis.primary_gap?.skill_id === p.skill_id;
                        return (
                          <div
                            key={p.skill_id}
                            className={`prereq-node-card ${isBottleneck ? "bottleneck" : p.potential_gap ? "gap" : "healthy"}`}
                          >
                            <div className="prereq-node-header">
                              <div className="prereq-node-title">
                                <strong>{p.name}</strong>
                                <span className={`prereq-distance-badge ${p.distance > 1 ? "foundational" : ""}`}>
                                  {p.is_direct ? "Direct prerequisite" : `Foundational (hop ${p.distance})`}
                                </span>
                                {isBottleneck ? (
                                  <span className="prereq-badge-bottleneck">Primary Bottleneck</span>
                                ) : p.potential_gap ? (
                                  <span className="prereq-badge-gap">Mastery Gap</span>
                                ) : (
                                  <span className="prereq-badge-healthy">Healthy</span>
                                )}
                              </div>
                              <div className="prereq-metrics-row">
                                <span>
                                  Mastery: <strong>{(p.mastery * 100).toFixed(1)}%</strong>
                                </span>
                                <span>
                                  Confidence: <strong>{(p.confidence * 100).toFixed(0)}%</strong>
                                </span>
                                <span>
                                  Risk: <strong>{p.risk}</strong>
                                </span>
                              </div>
                            </div>
                            {p.path_names && p.path_names.length > 1 && (
                              <div className="prereq-chain-path" style={{ marginTop: "6px" }}>
                                Path: {p.path_names.join(" → ")}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              ) : null}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              {profile.is_enrolled ? (
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => onRecommend(profile.skill_id)}
                >
                  Get recommendation <span>→</span>
                </button>
              ) : (
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => onEnroll(profile.skill_id)}
                  disabled={enrolling}
                >
                  {enrolling ? "Enrolling..." : "Enroll in skill"} <span>+</span>
                </button>
              )}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function LearningProgress({
  chartData = [],
  averageActivityScore = 0,
  totalStudyMinutes = 0,
  effectivenessData = null,
  effectivenessLoading = false,
  effectivenessError = "",
  onRefreshEffectiveness = null,
}) {
  const [actionTab, setActionTab] = useState("actual");

  const formatAction = (action) => (action ? action.replaceAll("_", " ") : "—");
  const formatChange = (val) => {
    if (val == null) return "—";
    const pp = val * 100;
    const sign = pp > 0 ? "+" : "";
    return `${sign}${pp.toFixed(1)} pp`;
  };

  const followed = effectivenessData?.comparison_by_adherence?.followed;
  const notFollowed = effectivenessData?.comparison_by_adherence?.not_followed;
  const avgChange = effectivenessData?.average_mastery_change;
  const totalEvaluated = effectivenessData?.total_real_evaluated ?? 0;

  return (
    <div className="learning-progress-page">
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Learning progress</h2>
            <p>Performance across your recent activities</p>
          </div>
        </div>

        <div className="metrics-grid">
          <div className="metric-card">
            <p>Average activity score</p>
            <h2>{chartData.length ? `${averageActivityScore.toFixed(1)}%` : "—"}</h2>
          </div>
          <div className="metric-card">
            <p>Recent study time</p>
            <h2>{totalStudyMinutes} min</h2>
          </div>
          <div className="metric-card">
            <p>Activities analyzed</p>
            <h2>{chartData.length}</h2>
          </div>
        </div>

        <h2>Score trend</h2>

        {chartData.length > 0 ? (
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#6758e8"
                  strokeWidth={3}
                  dot
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p>No scored activities are available yet.</p>
        )}
      </div>

      <div className="panel effectiveness-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow" style={{ color: "#6758e8", fontWeight: 700, fontSize: "11px", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "4px" }}>
              Outcome Evaluation
            </p>
            <h2>Learning effectiveness analytics</h2>
            <p>Measuring actual knowledge improvement (Δ mastery) across evaluated real-world outcomes</p>
          </div>
          {onRefreshEffectiveness && (
            <button
              type="button"
              className="tab-toggle-btn"
              onClick={onRefreshEffectiveness}
              disabled={effectivenessLoading}
            >
              {effectivenessLoading ? "Refreshing..." : "Refresh analytics"}
            </button>
          )}
        </div>

        <div className="effectiveness-disclaimer-card" role="note">
          <ShieldAlert size={20} color="#6758e8" style={{ flexShrink: 0 }} />
          <div>
            <strong>Observational Notice: </strong>
            Learning effectiveness measures empirical mastery change (Δ mastery) following real activities.
            Observational correlation does not establish causation, and self-reported action adherence (compliance) does not guarantee educational improvement.
          </div>
        </div>

        {effectivenessLoading && !effectivenessData ? (
          <p style={{ marginTop: "16px", color: "#666c85" }}>Loading learning effectiveness analytics...</p>
        ) : effectivenessError ? (
          <div className="login-error" style={{ marginTop: "16px" }} role="alert">
            {effectivenessError}
          </div>
        ) : totalEvaluated === 0 ? (
          <div style={{ marginTop: "16px", padding: "24px", textAlign: "center", background: "#fafafc", borderRadius: "12px", border: "1px dashed #d1d5db" }}>
            <p style={{ color: "#666c85", margin: 0 }}>
              No evaluated real learning outcomes recorded yet. Complete activities and evaluate learning outcomes to see empirical effectiveness analytics.
            </p>
          </div>
        ) : (
          <>
            <div className="metrics-grid" style={{ marginTop: "16px" }}>
              <Metric
                title="Average mastery change"
                value={formatChange(avgChange)}
                note={`Across ${totalEvaluated} real evaluated outcome${totalEvaluated === 1 ? "" : "s"}`}
                icon={avgChange != null && avgChange >= 0 ? TrendingUp : TrendingDown}
              />
              <Metric
                title="Positive outcomes"
                value={effectivenessData.positive_outcomes}
                note="Mastery increase recorded"
                icon={TrendingUp}
              />
              <Metric
                title="Neutral outcomes"
                value={effectivenessData.neutral_outcomes}
                note="Mastery remained steady"
                icon={Target}
              />
              <Metric
                title="Negative outcomes"
                value={effectivenessData.negative_outcomes}
                note="Mastery decrease observed"
                icon={TrendingDown}
              />
            </div>

            <h2 style={{ marginTop: "24px", marginBottom: "12px", fontSize: "16px" }}>
              Recommendation adherence comparison
            </h2>
            <div className="effectiveness-comparison-grid">
              <div className="comparison-card followed">
                <h3>Recommendations Followed</h3>
                <p className="sample-subtitle">
                  {followed?.sample_count ?? 0} evaluated outcome{followed?.sample_count === 1 ? "" : "s"}
                </p>
                <div className="comparison-stats-row">
                  <span>Average Δ Mastery</span>
                  <strong style={{ color: (followed?.average_mastery_change ?? 0) >= 0 ? "#16b881" : "#ef4444" }}>
                    {formatChange(followed?.average_mastery_change)}
                  </strong>
                </div>
                <div className="comparison-pill-row">
                  <span className="badge badge-success">{followed?.positive_count ?? 0} positive</span>
                  <span className="badge badge-neutral">{followed?.neutral_count ?? 0} neutral</span>
                  <span className="badge badge-danger">{followed?.negative_count ?? 0} negative</span>
                </div>
              </div>

              <div className="comparison-card not-followed">
                <h3>Alternative / Divergent Actions</h3>
                <p className="sample-subtitle">
                  {notFollowed?.sample_count ?? 0} evaluated outcome{notFollowed?.sample_count === 1 ? "" : "s"}
                </p>
                <div className="comparison-stats-row">
                  <span>Average Δ Mastery</span>
                  <strong style={{ color: (notFollowed?.average_mastery_change ?? 0) >= 0 ? "#16b881" : "#ef4444" }}>
                    {formatChange(notFollowed?.average_mastery_change)}
                  </strong>
                </div>
                <div className="comparison-pill-row">
                  <span className="badge badge-success">{notFollowed?.positive_count ?? 0} positive</span>
                  <span className="badge badge-neutral">{notFollowed?.neutral_count ?? 0} neutral</span>
                  <span className="badge badge-danger">{notFollowed?.negative_count ?? 0} negative</span>
                </div>
              </div>
            </div>

            <h2 style={{ marginTop: "24px", marginBottom: "12px", fontSize: "16px" }}>
              Effectiveness by skill
            </h2>
            {effectivenessData.by_skill && effectivenessData.by_skill.length > 0 ? (
              <div className="history-table-wrap" style={{ marginBottom: "24px" }}>
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Skill</th>
                      <th>Sample count</th>
                      <th>Average Δ mastery</th>
                      <th>Positive</th>
                      <th>Neutral</th>
                      <th>Negative</th>
                    </tr>
                  </thead>
                  <tbody>
                    {effectivenessData.by_skill.map((row) => (
                      <tr key={row.skill_id}>
                        <td><strong>{row.skill_name || `Skill ${row.skill_id}`}</strong></td>
                        <td>{row.sample_count}</td>
                        <td style={{ fontWeight: 600, color: (row.average_mastery_change ?? 0) >= 0 ? "#16b881" : "#ef4444" }}>
                          {formatChange(row.average_mastery_change)}
                        </td>
                        <td><span className="badge badge-success">{row.positive_count}</span></td>
                        <td><span className="badge badge-neutral">{row.neutral_count}</span></td>
                        <td><span className="badge badge-danger">{row.negative_count}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: "#666c85" }}>No skill-specific outcomes available.</p>
            )}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "24px", marginBottom: "12px" }}>
              <h2 style={{ margin: 0, fontSize: "16px" }}>
                Effectiveness by action
              </h2>
              <div className="tab-toggle-group">
                <button
                  type="button"
                  className={`tab-toggle-btn ${actionTab === "actual" ? "active" : ""}`}
                  onClick={() => setActionTab("actual")}
                >
                  Actual action taken
                </button>
                <button
                  type="button"
                  className={`tab-toggle-btn ${actionTab === "recommended" ? "active" : ""}`}
                  onClick={() => setActionTab("recommended")}
                >
                  Recommended action
                </button>
              </div>
            </div>

            {(() => {
              const actionList =
                actionTab === "actual"
                  ? effectivenessData.by_actual_action
                  : effectivenessData.by_recommended_action;

              if (!actionList || actionList.length === 0) {
                return <p style={{ color: "#666c85" }}>No action outcome data available.</p>;
              }

              return (
                <div className="history-table-wrap">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>{actionTab === "actual" ? "Actual action taken" : "Recommended action"}</th>
                        <th>Sample count</th>
                        <th>Average Δ mastery</th>
                        <th>Positive</th>
                        <th>Neutral</th>
                        <th>Negative</th>
                      </tr>
                    </thead>
                    <tbody>
                      {actionList.map((row) => (
                        <tr key={row.action}>
                          <td style={{ textTransform: "capitalize" }}><strong>{formatAction(row.action)}</strong></td>
                          <td>{row.sample_count}</td>
                          <td style={{ fontWeight: 600, color: (row.average_mastery_change ?? 0) >= 0 ? "#16b881" : "#ef4444" }}>
                            {formatChange(row.average_mastery_change)}
                          </td>
                          <td><span className="badge badge-success">{row.positive_count}</span></td>
                          <td><span className="badge badge-neutral">{row.neutral_count}</span></td>
                          <td><span className="badge badge-danger">{row.negative_count}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })()}
          </>
        )}
      </div>
    </div>
  );
}

function LearningOutcomeHistory({ testOutcomes = [], realOutcomes = [] }) {
  const [recordType, setRecordType] = useState("all");
  const [skillFilter, setSkillFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortOrder, setSortOrder] = useState("newest");
  const [selectedOutcome, setSelectedOutcome] = useState(null);
  const modalRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    if (!selectedOutcome) return;

    const previousFocus = document.activeElement;

    closeButtonRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setSelectedOutcome(null);
      }

      if (event.key === "Tab") {
        const focusable = modalRef.current?.querySelectorAll(
          'button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'
        );

        if (!focusable?.length) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus?.();
    };
  }, [selectedOutcome]);

  const allOutcomes = [
    ...testOutcomes.map((item) => ({ ...item, is_test: true })),
    ...realOutcomes.map((item) => ({ ...item, is_test: false })),
  ].sort((a, b) => b.outcome_id - a.outcome_id);

  const filteredOutcomes = allOutcomes
    .filter((item) => {
      const matchesType =
        recordType === "all" ||
        (recordType === "test" && item.is_test) ||
        (recordType === "real" && !item.is_test);

      const matchesSkill =
        skillFilter === "all" || String(item.skill_id) === skillFilter;

      const searchableText = [
        item.recommended_action,
        item.actual_action,
        item.outcome,
        item.recommendation_session_id,
        item.skill_id === 1 ? "Regression" : "Statistics",
      ]
        .join(" ")
        .toLowerCase();

      const matchesSearch = searchableText.includes(
        searchTerm.trim().toLowerCase()
      );

      return matchesType && matchesSkill && matchesSearch;
    })
    .sort((a, b) => {
      if (sortOrder === "change-high")
        return (b.mastery_change ?? 0) - (a.mastery_change ?? 0);
      if (sortOrder === "change-low")
        return (a.mastery_change ?? 0) - (b.mastery_change ?? 0);
      return sortOrder === "oldest"
        ? a.outcome_id - b.outcome_id
        : b.outcome_id - a.outcome_id;
    });

  const formatAction = (action) =>
    action ? action.replaceAll("_", " ") : "—";

  const formatMastery = (value) =>
    value == null ? "—" : `${(value * 100).toFixed(1)}%`;

  const formatChange = (value) => {
    if (value == null) return "—";
    const pp = value * 100;
    const sign = pp > 0 ? "+" : "";
    return `${sign}${pp.toFixed(1)} pp`;
  };

  const positiveCount = filteredOutcomes.filter(
    (item) => item.outcome === "positive"
  ).length;

  const neutralCount = filteredOutcomes.filter(
    (item) => item.outcome === "neutral"
  ).length;

  const negativeCount = filteredOutcomes.filter(
    (item) => item.outcome === "negative"
  ).length;

  const validChanges = filteredOutcomes
    .filter((item) => item.mastery_change != null)
    .map((item) => item.mastery_change);

  const averageMasteryChange = validChanges.length
    ? (validChanges.reduce((sum, value) => sum + value, 0) /
        validChanges.length) *
      100
    : null;

  return (
    <div className="history-page">
      <section className="metrics-grid history-metrics">
        <Metric title="All outcomes"  value={allOutcomes.length}   note="Test and real records"        icon={Target}        />
        <Metric title="Test outcomes" value={testOutcomes.length}  note="Prototype validation records"  icon={FlaskConical}  />
        <Metric title="Real outcomes" value={realOutcomes.length}  note="Non-test records"              icon={GraduationCap} />
      </section>

      <section className="history-summary-grid">
        <Metric
          title="Positive outcomes"
          value={positiveCount}
          note="Recorded positive results"
          icon={TrendingUp}
        />
        <Metric
          title="Neutral outcomes"
          value={neutralCount}
          note="Within the neutral threshold"
          icon={Target}
        />
        <Metric
          title="Negative outcomes"
          value={negativeCount}
          note="Recorded negative results"
          icon={TrendingDown}
        />
        <Metric
          title="Average mastery change"
          value={
            averageMasteryChange === null
              ? "—"
              : `${averageMasteryChange > 0 ? "+" : ""}${averageMasteryChange.toFixed(2)} pp`
          }
          note="Across filtered records"
          icon={BrainCircuit}
        />
      </section>

      <section className="panel history-panel">
        <div className="panel-heading">
          <div>
            <h2>Outcome records</h2>
            <p>
              {filteredOutcomes.length} record
              {filteredOutcomes.length === 1 ? "" : "s"} displayed
            </p>
          </div>
        </div>

        <div className="history-filters">
          <label>
            Search outcomes
            <input
              type="search"
              placeholder="Search skill, action, session..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </label>

          <label>
            Record type
            <select value={recordType} onChange={(e) => setRecordType(e.target.value)}>
              <option value="all">All records</option>
              <option value="test">Test outcomes</option>
              <option value="real">Real outcomes</option>
            </select>
          </label>

          <label>
            Skill
            <select value={skillFilter} onChange={(e) => setSkillFilter(e.target.value)}>
              <option value="all">All skills</option>
              <option value="1">Regression</option>
              <option value="2">Statistics</option>
            </select>
          </label>

          <label>
            Sort by
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="change-high">Largest mastery gain</option>
              <option value="change-low">Smallest mastery change</option>
            </select>
          </label>
        </div>

        <div className="table-wrap history-table-wrap">
          <table>
            <thead>
              <tr>
                <th>SKILL</th>
                <th>RECOMMENDED ACTION</th>
                <th>ACTUAL ACTION</th>
                <th>MASTERY BEFORE</th>
                <th>MASTERY AFTER</th>
                <th>CHANGE</th>
                <th>OUTCOME</th>
                <th>RECORD TYPE</th>
              </tr>
            </thead>
            <tbody>
              {filteredOutcomes.map((item) => {
                const handleSelect = () => setSelectedOutcome(item);
                return (
                <tr
                  key={item.outcome_id}
                  className="history-clickable-row"
                  title="Click to view outcome details"
                >
                  <td onClick={handleSelect}>
                    <strong>
                      {item.skill_id === 1
                        ? "Regression"
                        : item.skill_id === 2
                        ? "Statistics"
                        : `Skill ${item.skill_id}`}
                    </strong>
                    <small className="history-session">
                      Session: {item.recommendation_session_id ?? "Not linked"}
                    </small>
                  </td>
                  <td onClick={handleSelect}>{formatAction(item.recommended_action)}</td>
                  <td onClick={handleSelect}>{formatAction(item.actual_action)}</td>
                  <td onClick={handleSelect}>{formatMastery(item.before_mastery)}</td>
                  <td onClick={handleSelect}>{formatMastery(item.after_mastery)}</td>
                  <td onClick={handleSelect}>
                    <span
                      className={
                        item.mastery_change > 0
                          ? "change-positive"
                          : item.mastery_change < 0
                          ? "change-negative"
                          : "change-neutral"
                      }
                    >
                      {formatChange(item.mastery_change)}
                    </span>
                  </td>
                  <td onClick={handleSelect}>
                    <span className={`outcome-label outcome-${item.outcome}`}>
                      {item.outcome ?? "Unknown"}
                    </span>
                  </td>
                  <td onClick={handleSelect}>
                    <span className={item.is_test ? "record-test" : "record-real"}>
                      {item.is_test ? "Test" : "Real"}
                    </span>
                  </td>
                </tr>
                );
              })}

              {filteredOutcomes.length === 0 && (
                <tr>
                  <td colSpan={8} className="history-empty">
                    No outcomes match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <p className="demo-note">
          Mastery change is displayed in percentage points. Test records
          are kept separate from real learner outcomes.
         </p>
      </section>

      {selectedOutcome && (
        <div
          className="outcome-modal-overlay"
          onClick={() => setSelectedOutcome(null)}
          onKeyDown={(e) => e.key === "Escape" && setSelectedOutcome(null)}
        >
          <section
            ref={modalRef}
            className="outcome-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="outcome-modal-title"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(e) => e.key === "Escape" && setSelectedOutcome(null)}
          >
            <div className="panel-heading">
              <div>
                <p className="eyebrow">OUTCOME DETAILS</p>
                <h2 id="outcome-modal-title">
                  Outcome #{selectedOutcome.outcome_id}
                </h2>
                <p>
                  {selectedOutcome.is_test
                    ? "Prototype test record"
                    : "Real learner record"}
                </p>
              </div>
              <button
                ref={closeButtonRef}
                className="text-button"
                onClick={() => setSelectedOutcome(null)}
                aria-label="Close outcome details"
              >
                Close ✕
              </button>
            </div>

            <div className="outcome-detail-grid">
              <div>
                <span>Skill</span>
                <strong>
                  {selectedOutcome.skill_id === 1
                    ? "Regression"
                    : selectedOutcome.skill_id === 2
                    ? "Statistics"
                    : `Skill ${selectedOutcome.skill_id}`}
                </strong>
              </div>
              <div>
                <span>Recommendation session</span>
                <strong>
                  {selectedOutcome.recommendation_session_id ?? "Not linked"}
                </strong>
              </div>
              <div>
                <span>Recommended action</span>
                <strong>
                  {selectedOutcome.recommended_action?.replaceAll("_", " ") ?? "—"}
                </strong>
              </div>
              <div>
                <span>Actual action</span>
                <strong>
                  {selectedOutcome.actual_action?.replaceAll("_", " ") ?? "—"}
                </strong>
              </div>
              <div>
                <span>Mastery before</span>
                <strong>
                  {selectedOutcome.before_mastery == null
                    ? "—"
                    : `${(selectedOutcome.before_mastery * 100).toFixed(1)}%`}
                </strong>
              </div>
              <div>
                <span>Mastery after</span>
                <strong>
                  {selectedOutcome.after_mastery == null
                    ? "—"
                    : `${(selectedOutcome.after_mastery * 100).toFixed(1)}%`}
                </strong>
              </div>
              <div>
                <span>Mastery change</span>
                <strong>
                  {selectedOutcome.mastery_change == null
                    ? "—"
                    : `${selectedOutcome.mastery_change > 0 ? "+" : ""}${(
                        selectedOutcome.mastery_change * 100
                      ).toFixed(2)} percentage points`}
                </strong>
              </div>
              <div>
                <span>Outcome classification</span>
                <strong>{selectedOutcome.outcome ?? "Unknown"}</strong>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function Metric({ title, value, note, icon: Icon, details, disclaimer }) {
  return (
    <div className="metric-card">
      <div className="metric-icon"><Icon size={20} /></div>
      <p>{title}</p>
      <h2>{value}</h2>
      {details && <div className="metric-details">{details}</div>}
      <span>{note}</span>
      {disclaimer && <small className="metric-disclaimer">{disclaimer}</small>}
    </div>
  );
}

export default App;
