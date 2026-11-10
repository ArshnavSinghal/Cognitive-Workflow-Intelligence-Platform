const API_BASE_URL = "http://127.0.0.1:8000";

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("cwip_token");

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail
        ? typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail)
        : `Request failed (${response.status})`
    );
  }

  return data;
}

export async function login(email, password) {
  const data = await apiRequest("/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  // Adjust this if your login endpoint returns a differently named token.
  const token = data.access_token || data.token;

  if (!token) {
    throw new Error("Login succeeded, but no access token was returned.");
  }

  localStorage.setItem("cwip_token", token);
  return data;
}

export function getSkillAnalysis(skillId) {
  return apiRequest(`/skills/${skillId}/analysis`);
}

export function getSkills() {
  return apiRequest("/skills");
}

export function getSkill(skillId) {
  return apiRequest(`/skills/${skillId}`);
}

export function getSkillProfile(skillId) {
  return apiRequest(`/skills/${skillId}/profile`);
}

export function enrollSkill(skillId) {
  return apiRequest(`/skills/${skillId}/enroll`, {
    method: "POST",
  });
}

export function getSkillRecommendations(skillId) {
  return apiRequest(`/skills/${skillId}/recommendation`);
}

export function getSkillPrerequisites(skillId) {
  return apiRequest(`/skills/${skillId}/prerequisites`);
}

export function getSkillDiagnosis(skillId) {
  return apiRequest(`/skills/${skillId}/diagnosis`);
}

export function getSkillPath(sourceId, targetId) {
  return apiRequest(`/skills/${sourceId}/path/${targetId}`);
}

export function getGraphTopological() {
  return apiRequest("/skills/graph/topological");
}

export function getLearningOutcomes(isTest) {
  const query = isTest === undefined ? "" : `?is_test=${isTest}`;
  return apiRequest(`/learning-outcomes${query}`);
}

export function getLearningEffectiveness(skillId) {
  const query = skillId ? `?skill_id=${skillId}` : "";
  return apiRequest(`/analytics/effectiveness${query}`);
}

export function logout() {
  localStorage.removeItem("cwip_token");
}

export function getActivities() {
  return apiRequest("/activities");
}

export function getFeedbackLoopAnalytics(scope = "learner") {
  return apiRequest(`/analytics/feedback-loop?scope=${scope}`);
}

export function createActivity(activity) {
  return apiRequest("/activities", {
    method: "POST",
    body: JSON.stringify(activity),
  });
}
