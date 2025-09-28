/**
 * Teams and players API service
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * Get all teams
 */
export const getTeams = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/teams`);
    if (!response.ok) throw new Error('Failed to fetch teams');
    return await response.json();
  } catch (error) {
    console.error('Error fetching teams:', error);
    return [];
  }
};

/**
 * Get a specific team by ID
 */
export const getTeamById = async (teamId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/teams/${teamId}`);
    if (!response.ok) throw new Error('Failed to fetch team');
    return await response.json();
  } catch (error) {
    console.error(`Error fetching team ${teamId}:`, error);
    return null;
  }
};

/**
 * Get all players for a team
 */
export const getTeamPlayers = async (teamId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/teams/${teamId}/players`);
    if (!response.ok) throw new Error('Failed to fetch team players');
    return await response.json();
  } catch (error) {
    console.error(`Error fetching players for team ${teamId}:`, error);
    return [];
  }
};

/**
 * Get predictions for a specific player
 */
export const getPlayerPredictions = async (playerId, params = {}) => {
  try {
    const queryParams = new URLSearchParams(params).toString();
    const url = `${API_BASE_URL}/players/${playerId}/predictions${queryParams ? `?${queryParams}` : ''}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch player predictions');
    return await response.json();
  } catch (error) {
    console.error(`Error fetching predictions for player ${playerId}:`, error);
    return null;
  }
};