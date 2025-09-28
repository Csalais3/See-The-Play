// Simple API client for SeeThePlay frontend
const DEV_BACKEND_FALLBACK = 'http://localhost:8000';
const BASE_URL = process.env.REACT_APP_API_BASE || ((typeof window !== 'undefined' && window.location.hostname === 'localhost' && window.location.port === '3000') ? DEV_BACKEND_FALLBACK : window.location.origin);

export const API_BASE_URL = BASE_URL;

async function fetchJSON(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  console.debug('[API] fetching', url);
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      const text = await res.text();
      console.error(`API error ${res.status} ${url}:`, text);
      throw new Error(`API error ${res.status}: ${text}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`Network/API fetch failed for ${url}:`, err);
    throw err;
  }
}

// Team predictions
export async function getTeamPredictions(teamId, limit = 10) {
  return await fetchJSON(`/api/predictions/team/${teamId}/players?limit=${limit}`);
}

export async function getPlayerPrediction(playerId, teamId, includeExplanation = true) {
  return await fetchJSON(`/api/predictions/player/${playerId}?team_id=${encodeURIComponent(teamId)}&include_explanation=${includeExplanation}`);
}

// Teams and Players API (v1)
export async function getTeams() {
  return await fetchJSON(`/api/v1/teams`);
}

export async function getTeamDetails(teamId) {
  return await fetchJSON(`/api/v1/teams/${teamId}`);
}

export async function getTeamPlayers(teamId) {
  return await fetchJSON(`/api/v1/teams/${teamId}/players`);
}

export async function getPlayerDetails(playerId) {
  return await fetchJSON(`/api/v1/players/${playerId}`);
}

export async function getPlayerPredictions(playerId, params = {}) {
  const queryParams = new URLSearchParams(params).toString();
  return await fetchJSON(`/api/v1/players/${playerId}/predictions${queryParams ? `?${queryParams}` : ''}`);
}

export async function getTeamStats(teamId) {
  return await fetchJSON(`/api/v1/teams/${teamId}/stats`);
}

export async function getPlayerStats(playerId) {
  return await fetchJSON(`/api/v1/players/${playerId}/stats`);
}

export async function evaluateLineup(lineup) {
  // Expecting lineup to be { teamId, positions: { QB: playerId, RB: playerId, ... } }
  try {
    return await fetchJSON(`/api/v1/lineup/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lineup)
    });
  } catch (err) {
    // If backend doesn't support lineup evaluation yet, rethrow to let frontend fallback
    throw err;
  }
}

export default {
  getTeamPredictions,
  getPlayerPrediction,
  getTeams,
  getTeamDetails
};
