// frontend/src/App.js - FINAL FIXED VERSIONs
import React, { useState, useEffect, useRef } from 'react';
import { Activity, TrendingUp, MessageCircle, Zap, Target, AlertTriangle, Info } from 'lucide-react';
import { getTeams, getTeamDetails, getTeamPlayers, getTeamStats, getPlayerStats, API_BASE_URL, getPlayerPredictions as apiGetPlayerPredictions, evaluateLineup as apiEvaluateLineup } from './services/api';

const SeeThePlayDashboard = () => {
  const [gameState, setGameState] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [scenario, setScenario] = useState(null);
  const [ws, setWs] = useState(null);
  const [predictionsMap, setPredictionsMap] = useState({});
  const [liveEvents, setLiveEvents] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [teams, setTeams] = useState([]);
  const [teamsLoading, setTeamsLoading] = useState(false);
  const [teamsError, setTeamsError] = useState(null);
  const [selectedTeamDetails, setSelectedTeamDetails] = useState(null);
  const [teamDetailsLoading, setTeamDetailsLoading] = useState(false);
  const [selectedRosterPlayer, setSelectedRosterPlayer] = useState(null);
  const [playerPredictionsMap, setPlayerPredictionsMap] = useState({});
  const [playerPredictionsLoading, setPlayerPredictionsLoading] = useState(null);
  const [playerPredictionsError, setPlayerPredictionsError] = useState(null);
  const [isAssistantThinking, setIsAssistantThinking] = useState(false);
  const [showHeaderInfo, setShowHeaderInfo] = useState(false);
  const headerInfoRef = useRef(null);
  const wsRef = useRef(null);
  const [activePage, setActivePage] = useState('simulation'); // 'simulation' | 'playground' | 'teams' | 'live'

  // Close the header info tooltip when clicking outside or pressing Escape
  useEffect(() => {
    function handleClickOutside(e) {
      if (headerInfoRef.current && !headerInfoRef.current.contains(e.target)) {
        setShowHeaderInfo(false);
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') setShowHeaderInfo(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  useEffect(() => {
    const initializeDashboard = async () => {
      // Set initial game state
      const initialGameState = {
        game_id: 'sim_game_001',
        quarter: 1,
        time_remaining: '15:00',
        home_team: 'Philadelphia Eagles',
        away_team: 'Generic Opponents',
        home_score: 0,
        away_score: 0,
        status: 'in_progress'
      };
      setGameState(initialGameState);
      
      // Connect to WebSocket for live updates
      let websocket = null;
      try {
        if (typeof WebSocket !== 'undefined') websocket = new WebSocket('ws://localhost:8000/ws');
      } catch (err) {
        console.warn('WebSocket not available', err);
        websocket = null;
      }

      if (!websocket) {
        setIsConnected(false);
        wsRef.current = null;
        setWs(null);
      } else {
        websocket.onopen = () => {
          console.log('✅ WebSocket connected');
          setIsConnected(true);
          wsRef.current = websocket;
          setWs(websocket);
        };

        websocket.onmessage = (event) => {
          let message = null;
          try {
            message = JSON.parse(event.data);
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err, event.data);
            return;
          }

          try {
            console.log('📩 WebSocket message:', message.type, message);

            if (message.type === 'tick') {
              if (message.game_state) {
                if (message.game_state.quarter === 4 && message.game_state.time_remaining === '0:00') {
                  safeSend({ type: 'game_reset', data: initialGameState });
                } else {
                  setGameState(message.game_state);
                }
              }
              return;
            }

            if (message.type === 'game_initialized') {
              setGameState(message.game_state);
              if (message.initial_predictions && message.initial_predictions.length > 0) {
                setPredictions(message.initial_predictions);
              }
            } else if (message.type === 'live_update') {
              setGameState(message.game_state);
              const newEvent = {
                id: message.event.id,
                type: message.event.type,
                description: message.event.description,
                quarter: message.event.quarter,
                timestamp: message.event.timestamp
              };
              setLiveEvents(prev => {
                const exists = prev.some(e => e.id === newEvent.id);
                if (exists) return prev;
                return [newEvent, ...prev].slice(0, 5);
              });
              if (message.updated_prediction) {
                setPredictions(prev => {
                  const playerIndex = prev.findIndex(p => p.prediction.player_id === message.updated_prediction.player_id);
                  if (playerIndex >= 0) {
                    const updated = [...prev];
                    updated[playerIndex] = { prediction: message.updated_prediction, explanation: message.explanation };
                    return updated;
                  }
                  return prev;
                });
              }
            } else if (message.type === 'scenario_update') {
              setScenario(message.scenario);
              if (message.updated_predictions) setPredictions(message.updated_predictions);
              setTimeout(() => setScenario(null), 5000);
            } else if (message.type === 'cedar_answer') {
              try {
                let playerName = message.player_name || null;
                if (!playerName && message.player_id) {
                  const found = predictions.find(p => p.prediction.player_id === message.player_id);
                  playerName = found?.prediction?.player_name || null;
                }
                const assistantMsg = { id: Date.now() + Math.floor(Math.random() * 1000), type: 'assistant', text: message.answer || 'No answer available.', playerName: playerName, playerId: message.player_id };
                setChatMessages(prev => [...prev, assistantMsg]);
                setIsAssistantThinking(false);
              } catch (err) {
                console.error('Error handling cedar_answer message:', err, message);
              }
            }
          } catch (err) {
            console.error('Error handling WebSocket message:', err, message);
          }
        };

        websocket.onclose = () => {
          setIsConnected(false);
          wsRef.current = null;
          setWs(null);
        };

        websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
        };

        wsRef.current = websocket;
        setWs(websocket);
        return () => { try { websocket.close(); } catch (_) {} };
      }
    };

    initializeDashboard();
  }, []);

  const safeSend = (payload) => {
    try {
      const socket = wsRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(payload));
    } catch (err) {
      console.warn('WebSocket send failed', err, payload);
    }
  };

  // Small helper to render a simple icon for event types
  const getEventIcon = (eventType) => {
    const icons = {
      pass_completion: '✅',
      rush_attempt: '🏃',
      reception: '📥',
      touchdown: '🏈',
      field_goal: '⚽',
      interception: '🛑',
      fumble: '📉',
      sack: '💥',
      timeout: '⏱️',
      penalty: '🚫'
    };
    return icons[eventType] || '📊';
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!currentQuestion.trim() || !ws) return;
    if (ws.readyState !== WebSocket.OPEN) return;
    const resolvedPlayerName = (() => { if (selectedPlayer) { const found = predictions.find(p => p.prediction.player_id === selectedPlayer); return found?.prediction?.player_name || null; } return predictions[0]?.prediction?.player_name || null; })();
    const userMessage = { id: Date.now(), type: 'user', text: currentQuestion, playerName: resolvedPlayerName, playerId: selectedPlayer || predictions[0]?.prediction?.player_id };
    setChatMessages(prev => [...prev, userMessage]);
    safeSend({ type: 'cedar_question', question: currentQuestion, player_id: userMessage.playerId });
    setIsAssistantThinking(true);
    setCurrentQuestion('');
  };

  const handleScenarioChange = (scenarioType) => { if (!wsRef.current) return; safeSend({ type: 'scenario_change', data: { type: scenarioType, severity: scenarioType === 'weather_change' ? 0.15 : 0.2 } }); };

  // Circular confidence indicator
  const ConfidenceCircle = ({ confidence = 0, size = 44 }) => {
    const pct = Math.max(0, Math.min(1, Number(confidence) || 0));
    const stroke = 4;
    const radius = (size - stroke) / 2;
    const circumference = 2 * Math.PI * radius;
    const dashOffset = circumference * (1 - pct);
    const color = pct >= 0.85 ? '#34D399' // green-400
                  : pct >= 0.5  ? '#F59E0B' // amber-500
                  : '#F87171';              // red-400
    const fontSize = Math.max(10, Math.floor(size * 0.32));

    return (
      <div className="flex flex-col items-center" aria-hidden={false} aria-label={`Confidence Score ${(pct*100).toFixed(0)} percent`}>
        <svg height={size} width={size} className="-rotate-90">
          <circle
            stroke="#0f172a"
            fill="transparent"
            strokeWidth={stroke}
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
          <circle
            stroke={color}
            fill="transparent"
            strokeWidth={stroke}
            strokeLinecap="round"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: dashOffset,
              transition: 'stroke-dashoffset 600ms ease, stroke 300ms ease'
            }}
          />
          <text
            x="50%"
            y="50%"
            dominantBaseline="middle"
            textAnchor="middle"
            fontSize={fontSize}
            fontWeight={700}
            fill={color}
            transform={`rotate(90 ${size/2} ${size/2})`}
          >
            {(pct * 100).toFixed(0)}%
          </text>
        </svg>
        <div className="text-[10px] text-gray-400 mt-1">Confidence Score</div>
      </div>
    );
  };

  // Small wrapper showing the confidence circle with a top-right info icon and tooltip
  const ConfidenceWithInfo = ({ confidence = 0, size = 44 }) => {
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    useEffect(() => {
      function handleClickOutside(e) {
        if (ref.current && !ref.current.contains(e.target)) {
          setOpen(false);
        }
      }
      function handleEsc(e) {
        if (e.key === 'Escape') setOpen(false);
      }
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEsc);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
        document.removeEventListener('keydown', handleEsc);
      };
    }, []);

    return (
      <div className="relative inline-block" ref={ref}>
        <ConfidenceCircle confidence={confidence} size={size} />

        {/* Top-right info button */}
        <button
          onClick={(e) => { e.stopPropagation(); setOpen(s => !s); }}
          aria-haspopup="dialog"
          aria-expanded={open}
          className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-black/60 border border-white/10 flex items-center justify-center"
          title="What is Confidence Score?"
        >
          <Info className="w-3 h-3 text-gray-300" />
        </button>

        {open && (
          <div className="absolute -top-2 right-6 w-64 bg-black/90 border border-white/10 p-3 rounded shadow-lg text-sm text-gray-200 z-50">
            <div className="font-semibold">Confidence Score</div>
            <div className="text-xs text-gray-300 mt-1">
              The model's confidence in this prediction expressed as a percentage.
              <ul className="list-disc ml-4 mt-2 text-xs text-gray-300">
                <li><span className="font-semibold">Green:</span> ≥ 85% — high confidence</li>
                <li><span className="font-semibold">Yellow:</span> 50–84% — moderate confidence</li>
                <li><span className="font-semibold">Red:</span> &lt; 50% — low confidence</li>
              </ul>
              <div className="mt-2 text-xs">Combine this score with the explanation to evaluate prediction reliability.</div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Helper to load teams (used by Refresh button and when opening Teams page)
  const loadTeams = async () => {
    setTeamsLoading(true);
    setTeamsError(null);
    try {
      const t = await getTeams();
      const list = t || [];
      // Sort teams A-Z by display name (market + name if available)
      const sorted = list.slice().sort((a, b) => {
        const aName = (a.market ? `${a.market} ${a.name}` : a.name || '').toLowerCase();
        const bName = (b.market ? `${b.market} ${b.name}` : b.name || '').toLowerCase();
        if (aName < bName) return -1;
        if (aName > bName) return 1;
        return 0;
      });
      setTeams(sorted);
    } catch (err) {
      console.error('Failed to load teams', err);
      setTeams([]);
      setTeamsError(err?.message || 'Failed to load teams from backend');
    } finally {
      setTeamsLoading(false);
    }
  };

  // Auto-load teams when user navigates to the Teams page
  useEffect(() => {
    if (activePage === 'teams') {
      loadTeams();
    }
  }, [activePage]);

  // Ensure teams are loaded so the playground dropdowns are populated
  useEffect(() => {
    if (!teams || teams.length === 0) {
      loadTeams();
    }
  }, []);

  // Toggle roster player selection and lazily fetch their predictions
  const toggleRosterPlayer = async (player) => {
    try {
      if (selectedRosterPlayer === player.id) {
        setSelectedRosterPlayer(null);
        return;
      }
      setSelectedRosterPlayer(player.id);

      // If we already have cached predictions, no need to refetch
      if (playerPredictionsMap[player.id]) return;

      setPlayerPredictionsLoading(player.id);
      setPlayerPredictionsError(null);

      const pred = await getPlayerPredictions(player.id);
      setPlayerPredictionsMap(prev => ({ ...prev, [player.id]: pred }));
    } catch (err) {
      console.error('Failed to fetch player predictions', err);
      setPlayerPredictionsError(err?.message || 'Failed to load player predictions');
    } finally {
      setPlayerPredictionsLoading(null);
    }
  };

  const getPlayerPredictions = async (playerId) => {
    setPlayerPredictionsLoading(playerId);
    setPlayerPredictionsError(null);
    try {
      const data = await apiGetPlayerPredictions(playerId);
      setPlayerPredictionsMap(prev => ({ ...prev, [playerId]: data }));
      return data;
    } catch (error) {
      console.error('Error fetching player predictions via API client:', error);
      setPlayerPredictionsError(error?.message || 'Failed to load player predictions');
      return null;
    } finally {
      setPlayerPredictionsLoading(null);
    }
  };

  const handlePlayerPredictionsFetch = (playerId) => {
    if (playerPredictionsMap[playerId]) {
      // Already have predictions, just toggle the view
      setSelectedRosterPlayer(selectedRosterPlayer === playerId ? null : playerId);
    } else {
      // Fetch predictions from server
      setPlayerPredictionsLoading(playerId);
      setPlayerPredictionsError(null);
      
      getPlayerPredictions(playerId)
        .then(pred => {
          if (pred) {
            setPlayerPredictionsMap(prev => ({ ...prev, [playerId]: pred }));
            setSelectedRosterPlayer(playerId);
          }
        })
        .catch(err => {
          console.error('Failed to fetch player predictions', err);
          setPlayerPredictionsError(err?.message || 'Failed to load player predictions');
        })
        .finally(() => {
          setPlayerPredictionsLoading(null);
        });
    }
  };

  // Playground state
  const [playHomeTeam, setPlayHomeTeam] = useState(null);
  const [playAwayTeam, setPlayAwayTeam] = useState(null);
  const PLAY_POSITIONS = ['QB', 'RB', 'WR1', 'WR2', 'TE', 'K', 'DEF'];
  const [homeLineup, setHomeLineup] = useState(() => PLAY_POSITIONS.reduce((acc, p) => ({ ...acc, [p]: null }), {}));
  const [awayLineup, setAwayLineup] = useState(() => PLAY_POSITIONS.reduce((acc, p) => ({ ...acc, [p]: null }), {}));
  const [teamPlayersCache, setTeamPlayersCache] = useState({}); // teamId -> players[]
  const [showPlayerPicker, setShowPlayerPicker] = useState({ open: false, position: null, side: 'home' });
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [evaluatingLineup, setEvaluatingLineup] = useState(false);

  // Position coordinates on the SVG field (percentages)
  const POS_COORDS = {
    QB: { x: 50, y: 55 },
    RB: { x: 50, y: 72 },
    WR1: { x: 20, y: 38 },
    WR2: { x: 20, y: 72 },
    TE: { x: 40, y: 50 },
    K: { x: 85, y: 90 },
    DEF: { x: 85, y: 50 }
  };

  // Load team players when either team is chosen for the playground
  useEffect(() => {
    const loadPlayersFor = async (teamId) => {
      if (!teamId) return;
      if (teamPlayersCache[teamId]) return;
      try {
        const players = await getTeamPlayers(teamId);
        setTeamPlayersCache(prev => ({ ...prev, [teamId]: players || [] }));
      } catch (err) {
        console.warn('Failed to load players for playground team', err);
        setTeamPlayersCache(prev => ({ ...prev, [teamId]: [] }));
      }
    };
    loadPlayersFor(playHomeTeam);
    loadPlayersFor(playAwayTeam);
  }, [playHomeTeam, playAwayTeam]);

  const openPicker = (position, side = 'home') => {
    const teamId = side === 'home' ? playHomeTeam : playAwayTeam;
    if (!teamId) return alert('Select a team first');
    setShowPlayerPicker({ open: true, position, side });
  };

  const assignPlayerToPosition = (player) => {
    if (showPlayerPicker.side === 'home') {
      setHomeLineup(prev => ({ ...prev, [showPlayerPicker.position]: player }));
    } else {
      setAwayLineup(prev => ({ ...prev, [showPlayerPicker.position]: player }));
    }
    setShowPlayerPicker({ open: false, position: null, side: 'home' });
  };

  const clearLineup = () => {
    setHomeLineup(PLAY_POSITIONS.reduce((acc, p) => ({ ...acc, [p]: null }), {}));
    setAwayLineup(PLAY_POSITIONS.reduce((acc, p) => ({ ...acc, [p]: null }), {}));
    setEvaluationResult(null);
  };

  const localEvaluateLineup = async (homeObj, awayObj) => {
    // Fallback estimator: compare aggregated player predictions
    try {
      const homeIds = Object.values(homeObj).filter(Boolean).map(p => p.id);
      const awayIds = Object.values(awayObj).filter(Boolean).map(p => p.id);
      const homePreds = await Promise.all(homeIds.map(id => apiGetPlayerPredictions(id).catch(() => null)));
      const awayPreds = await Promise.all(awayIds.map(id => apiGetPlayerPredictions(id).catch(() => null)));

      const summarize = (preds) => {
        let confidenceSum = 0, count = 0, points = 0, yards = 0;
        preds.forEach(p => {
          if (!p) return;
          count += 1;
          const c = p.overall_confidence || 0.7; confidenceSum += c;
          const td = p.predictions?.touchdowns?.predicted_value || 0;
          const passY = p.predictions?.passing_yards?.predicted_value || 0;
          const rushY = p.predictions?.rushing_yards?.predicted_value || 0;
          const recvY = p.predictions?.receiving_yards?.predicted_value || 0;
          points += td * 6 + 0.02 * (passY + rushY + recvY);
          yards += passY + rushY + recvY;
        });
        return { avgConfidence: count ? confidenceSum / count : 0.7, points, yards };
      };

      const h = summarize(homePreds);
      const a = summarize(awayPreds);
      // Compute a simple win probability via sigmoid of (home_strength - away_strength)
      const homeStrength = h.avgConfidence * 0.6 + (h.points / Math.max(1, a.points + 1)) * 0.4;
      const awayStrength = a.avgConfidence * 0.6 + (a.points / Math.max(1, h.points + 1)) * 0.4;
      const diff = homeStrength - awayStrength;
      const sigmoid = (x) => 1 / (1 + Math.exp(-6 * x)); // steeper
      const winProbability = Math.max(0.02, Math.min(0.98, sigmoid(diff)));

      return {
        winProbability: Math.round(winProbability * 1000) / 10,
        expectedPointsHome: Math.round(h.points * 10) / 10,
        expectedPointsAway: Math.round(a.points * 10) / 10,
        expectedYardsHome: Math.round(h.yards),
        expectedYardsAway: Math.round(a.yards),
        avgPlayerConfidenceHome: Math.round(h.avgConfidence * 1000) / 10,
        avgPlayerConfidenceAway: Math.round(a.avgConfidence * 1000) / 10
      };
    } catch (err) {
      console.error('Local lineup evaluation failed', err);
      return { winProbability: Math.round((0.5 + (Math.random()-0.5)*0.15)*1000)/10 };
    }
  };

  const evaluateLineup = async () => {
    setEvaluatingLineup(true);
    setEvaluationResult(null);
    const payload = {
      homeTeamId: playHomeTeam,
      awayTeamId: playAwayTeam,
      homePositions: Object.fromEntries(Object.entries(homeLineup).map(([k, v]) => [k, v ? v.id : null])),
      awayPositions: Object.fromEntries(Object.entries(awayLineup).map(([k, v]) => [k, v ? v.id : null]))
    };
    try {
      // Try backend evaluation first
      const res = await (async () => {
        try {
          const server = await apiEvaluateLineup(payload);
          return server;
        } catch (err) {
          // Backend not available or failed — fallback
          return null;
        }
      })();
      let final;
      if (res && res.winProbability != null) {
        final = res;
      } else {
        final = await localEvaluateLineup(homeLineup, awayLineup);
      }
      setEvaluationResult(final);
    } catch (err) {
      console.error('Evaluate lineup error', err);
      const fallback = await localEvaluateLineup(homeLineup, awayLineup);
      setEvaluationResult(fallback);
    } finally {
      setEvaluatingLineup(false);
    }
  };

  // Reintroduce SVG field and side-aware position pickers carefully, keeping JSX balanced (cleaned)
  const renderPlayground = () => {
    const homePlayers = playHomeTeam ? (teamPlayersCache[playHomeTeam] || []) : [];
    const awayPlayers = playAwayTeam ? (teamPlayersCache[playAwayTeam] || []) : [];
    const homeTeamObj = teams.find(t => t.id === playHomeTeam) || null;
    const awayTeamObj = teams.find(t => t.id === playAwayTeam) || null;
    const homeTeamLabel = homeTeamObj ? (homeTeamObj.market ? `${homeTeamObj.market} ${homeTeamObj.name}` : homeTeamObj.name) : 'HOME';
    const awayTeamLabel = awayTeamObj ? (awayTeamObj.market ? `${awayTeamObj.market} ${awayTeamObj.name}` : awayTeamObj.name) : 'AWAY';
    return (
      <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 mb-6 border border-white/10 text-gray-300">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Playground — Build a Lineup</h2>
          <div className="flex items-center gap-2">
            <select value={playHomeTeam || ''} onChange={(e) => { setPlayHomeTeam(e.target.value || null); }} className="bg-white/5 px-3 py-1 rounded text-sm">
              <option value="">Select Home Team...</option>
              {teams.map(t => <option key={t.id} value={t.id}>{t.market ? `${t.market} ${t.name}` : t.name}</option>)}
            </select>
            <select value={playAwayTeam || ''} onChange={(e) => { setPlayAwayTeam(e.target.value || null); }} className="bg-white/5 px-3 py-1 rounded text-sm">
              <option value="">Select Away Team...</option>
              {teams.map(t => <option key={t.id} value={t.id}>{t.market ? `${t.market} ${t.name}` : t.name}</option>)}
            </select>
            <button onClick={clearLineup} className="px-3 py-1 bg-white/5 rounded text-sm">Reset</button>
            <button onClick={evaluateLineup} disabled={evaluatingLineup || !playHomeTeam || !playAwayTeam} className="px-3 py-1 bg-cyan-500/20 hover:bg-cyan-500/30 rounded text-sm">{evaluatingLineup ? 'Evaluating…' : 'Confirm & Evaluate'}</button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {/* Home list */}
          <div>
            <div className="text-sm font-semibold mb-2">Home ({playHomeTeam ? playHomeTeam : 'No team'})</div>
            <div className="space-y-3">
              {PLAY_POSITIONS.map(pos => (
                <div key={`home-list-${pos}`} className="flex items-center gap-3">
                  <button onClick={() => openPicker(pos, 'home')} className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center text-xs font-semibold text-white">{pos}</button>
                  <div className="text-sm">
                    <div className="font-medium">{homeLineup[pos] ? `${homeLineup[pos].first_name} ${homeLineup[pos].last_name}` : <span className="text-gray-400">Select player</span>}</div>
                    <div className="text-xs text-gray-400">{homeLineup[pos]?.position || ''}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-1 flex items-center justify-center">
            <div className="w-full max-w-[520px] h-[360px] bg-green-900 rounded-xl p-4 relative overflow-hidden">
              <svg viewBox="0 0 300 160" preserveAspectRatio="none" className="absolute inset-0 w-full h-full">
                <defs>
                  <linearGradient id="fieldGrad2" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#1f7a2d" />
                    <stop offset="100%" stopColor="#0d5f20" />
                  </linearGradient>
                </defs>

                {/* Base turf */}
                <rect x="0" y="0" width="300" height="160" fill="url(#fieldGrad2)" />

                {/* Subtle alternating stripes for turf */}
                {Array.from({ length: 8 }).map((_, i) => (
                  <rect key={`stripe-${i}`} x={30} y={8 + i * 18} width={240} height={18} fill={i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0)'} />
                ))}

                {/* Sidelines and boundaries */}
                <rect x="28" y="6" width="244" height="148" fill="none" stroke="#ffffff" strokeOpacity={0.16} strokeWidth={1.5} rx="6" />

                {/* Endzones */}
                <rect x="0" y="0" width="30" height="160" fill="#0ea5e9" opacity="0.95" rx="4" />
                <rect x="270" y="0" width="30" height="160" fill="#ef4444" opacity="0.95" rx="4" />
                <text x="15" y="80" fontSize="10" fill="#ffffff" textAnchor="middle" transform="rotate(-90 15 80)" opacity="0.95" fontWeight="700">{homeTeamLabel}</text>
                <text x="285" y="80" fontSize="10" fill="#ffffff" textAnchor="middle" transform="rotate(90 285 80)" opacity="0.95" fontWeight="700">{awayTeamLabel}</text>

                {/* Yard lines and hashes (every 10 yards) */}
                {Array.from({ length: 9 }).map((_, i) => {
                  const x = 30 + (i + 1) * 24;
                  const yardNum = (10 * (i + 1));
                  return (
                    <g key={`yard-${i}`}>
                      <line x1={x} y1={12} x2={x} y2={148} stroke="#ffffff" strokeOpacity={0.12} strokeWidth={1} />
                      {/* short hash marks near sidelines */}
                      <line x1={x - 3} y1={18} x2={x + 3} y2={18} stroke="#ffffff" strokeOpacity={0.18} strokeWidth={1} />
                      <line x1={x - 3} y1={142} x2={x + 3} y2={142} stroke="#ffffff" strokeOpacity={0.18} strokeWidth={1} />
                      {/* yard number; mirror numbers on both sides */}
                      <text x={x} y={36} fontSize="9" fill="#ffffff" opacity={0.18} textAnchor="middle" fontWeight="700">{yardNum}</text>
                      <text x={x} y={124} fontSize="9" fill="#ffffff" opacity={0.18} textAnchor="middle" fontWeight="700">{yardNum}</text>
                    </g>
                  );
                })}

                {/* Center logo and midfield marker */}
                <circle cx="150" cy="80" r="20" fill="#ffffff" fillOpacity="0.06" stroke="#ffffff" strokeOpacity="0.12" />
                <text x="150" y="85" fontSize="12" fill="#ffffff" textAnchor="middle" opacity="0.9" fontWeight="700">PLAY</text>

                {/* Small goalpost stylized markers (simple) */}
                <g transform="translate(145,4)" opacity="0.9">
                  <rect x="2" y="0" width="6" height="10" fill="#ffd54d" />
                </g>
                <g transform="translate(145,146)" opacity="0.9">
                  <rect x="2" y="0" width="6" height="10" fill="#ffd54d" />
                </g>
              </svg>

              {PLAY_POSITIONS.map(pos => {
                const home = POS_COORDS[pos];
                const away = { x: 100 - home.x, y: home.y };
                const homeInitials = homeLineup[pos] ? (homeLineup[pos].first_name[0] + (homeLineup[pos].last_name?.[0] || '')) : pos;
                const awayInitials = awayLineup[pos] ? (awayLineup[pos].first_name[0] + (awayLineup[pos].last_name?.[0] || '')) : pos;
                return (
                  <div key={`pos-${pos}`}>
                    <button
                      onClick={() => openPicker(pos, 'home')}
                      style={{ left: `${home.x}%`, top: `${home.y}%` }}
                      className={`absolute transform -translate-x-1/2 -translate-y-1/2 w-14 h-14 rounded-full flex flex-col items-center justify-center text-xs font-semibold ${homeLineup[pos] ? 'bg-blue-600' : 'bg-white/10'} text-white ring-1 ring-white/10 shadow-[0_6px_18px_rgba(2,6,23,0.4)]`}
                      title={homeLineup[pos] ? `${homeLineup[pos].first_name} ${homeLineup[pos].last_name}` : `Assign ${pos}`}>
                      <span className="text-sm leading-4">{homeInitials}</span>
                      <span className="text-[10px] text-white/80 mt-0.5">{pos}</span>
                    </button>

                    <button
                      onClick={() => openPicker(pos, 'away')}
                      style={{ left: `${away.x}%`, top: `${away.y}%` }}
                      className={`absolute transform -translate-x-1/2 -translate-y-1/2 w-14 h-14 rounded-full flex flex-col items-center justify-center text-xs font-semibold ${awayLineup[pos] ? 'bg-red-700' : 'bg-white/10'} text-white ring-1 ring-white/10 shadow-[0_6px_18px_rgba(2,6,23,0.4)]`}
                      title={awayLineup[pos] ? `${awayLineup[pos].first_name} ${awayLineup[pos].last_name}` : `Assign opponent ${pos}`}>
                      <span className="text-sm leading-4">{awayInitials}</span>
                      <span className="text-[10px] text-white/80 mt-0.5">{pos}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Away list */}
          <div>
            <div className="text-sm font-semibold mb-2">Away ({playAwayTeam ? playAwayTeam : 'No team'})</div>
            <div className="space-y-3">
              {PLAY_POSITIONS.map(pos => (
                <div key={`away-list-${pos}`} className="flex items-center gap-3">
                  <button onClick={() => openPicker(pos, 'away')} className="w-12 h-12 rounded-full bg-red-600 flex items-center justify-center text-xs font-semibold text-white">{pos}</button>
                  <div className="text-sm">
                    <div className="font-medium">{awayLineup[pos] ? `${awayLineup[pos].first_name} ${awayLineup[pos].last_name}` : <span className="text-gray-400">Select player</span>}</div>
                    <div className="text-xs text-gray-400">{awayLineup[pos]?.position || ''}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {evaluationResult && (
          <div className="mt-6 bg-white/6 p-4 rounded">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-300">Estimated Win Probability</div>
                <div className="text-2xl font-bold">{evaluationResult.winProbability}%</div>
              </div>
              <div className="text-sm text-gray-300">
                <div>Expected Points (Home): <span className="font-semibold text-white">{evaluationResult.expectedPointsHome}</span></div>
                <div>Expected Points (Away): <span className="font-semibold text-white">{evaluationResult.expectedPointsAway}</span></div>
              </div>
            </div>
          </div>
        )}

        {showPlayerPicker.open && (() => {
          const side = showPlayerPicker.side || 'home';
          const teamId = side === 'home' ? playHomeTeam : playAwayTeam;
          const playersForTeam = teamPlayersCache[teamId] || [];
          return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
              <div className="bg-slate-900 rounded-lg w-2/3 max-w-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="text-lg font-bold">Select player for {showPlayerPicker.position} ({side})</div>
                  <button onClick={() => setShowPlayerPicker({ open: false, position: null, side: 'home' })} className="text-sm text-gray-400">Close</button>
                </div>
                <div className="grid grid-cols-2 gap-3 max-h-72 overflow-y-auto">
                  {playersForTeam.length === 0 && (<div className="text-gray-400">No players for this team.</div>)}
                  {playersForTeam.map(pl => (
                    <button key={pl.id} onClick={() => assignPlayerToPosition(pl)} className="text-left p-2 rounded hover:bg-white/5">
                      <div className="font-medium">{pl.first_name} {pl.last_name}</div>
                      <div className="text-xs text-gray-400">{pl.position}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                SeeThePlay
              </h1>
              <p className="text-sm text-gray-400">You don't just get numbers, you see them.</p>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
              <span className="text-sm">{isConnected ? 'Live' : 'Disconnected'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Page Navigation */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActivePage('simulation')}
              className={`px-3 py-1 rounded text-sm font-semibold ${activePage === 'simulation' ? 'bg-cyan-600/20 text-cyan-300' : 'bg-white/5 text-gray-300'}`}
            >
              Mock Simulation
            </button>
            <button
              onClick={() => setActivePage('playground')}
              className={`px-3 py-1 rounded text-sm font-semibold ${activePage === 'playground' ? 'bg-cyan-600/20 text-cyan-300' : 'bg-white/5 text-gray-300'}`}
            >
              Playground
            </button>
             <button
              onClick={() => setActivePage('teams')}
              className={`px-3 py-1 rounded text-sm font-semibold ${activePage === 'teams' ? 'bg-cyan-600/20 text-cyan-300' : 'bg-white/5 text-gray-300'}`}
            >
              Teams
            </button>
            <button
              onClick={() => setActivePage('live')}
              className={`px-3 py-1 rounded text-sm font-semibold ${activePage === 'live' ? 'bg-cyan-600/20 text-cyan-300' : 'bg-white/5 text-gray-300'}`}
            >
              Live
            </button>
          </div>
          <div className="text-sm text-gray-400">
            Page: {activePage === 'simulation' ? 'Mock Simulation' : activePage === 'playground' ? 'Playground' : activePage === 'teams' ? 'Teams' : 'Live'}
          </div>
        </div>

        {activePage === 'simulation' ? (
          // Simulation content
          <>
            {/* Game State */}
            {gameState && (
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 mb-6 border border-white/20">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold flex items-center">
                    <Activity className="w-5 h-5 mr-2" />
                    Live Game
                  </h2>
                  <div className="flex items-center space-x-4 text-sm">
                    <span>Q{gameState.quarter}</span>
                    <span>{gameState.time_remaining}</span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-cyan-400">{gameState.home_score}</div>
                    <div className="text-sm text-gray-300">{gameState.home_team}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold text-white">VS</div>
                    <div className="text-sm text-gray-400">Live Game</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-400">{gameState.away_score}</div>
                    <div className="text-sm text-gray-300">{gameState.away_team}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Scenario Alert */}
            {scenario && (
              <div className="bg-orange-500/20 border border-orange-500/50 rounded-xl p-4 mb-6">
                <div className="flex items-center">
                  <AlertTriangle className="w-5 h-5 text-orange-400 mr-2" />
                  <div>
                    <div className="font-semibold text-orange-400">Scenario Update</div>
                    <div className="text-sm text-orange-200">{scenario.description}</div>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Predictions Panel */}
              <div className="lg:col-span-2">
                <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold flex items-center">
                      <TrendingUp className="w-5 h-5 mr-2" />
                      Live Predictions {predictions.length > 0 && `(${predictions.length})`}
                    </h2>
                    <div className="flex gap-2 items-center">
                      <button 
                        onClick={() => handleScenarioChange('weather_change')}
                        className="px-3 py-1 bg-blue-500/20 hover:bg-blue-500/30 rounded-lg text-sm transition-colors"
                      >
                        Weather Change
                      </button>
                      <button 
                        onClick={() => handleScenarioChange('high_scoring')}
                        className="px-3 py-1 bg-purple-500/20 hover:bg-purple-500/30 rounded-lg text-sm transition-colors"
                      >
                        High Scoring
                      </button>
                      {/* Header-level info explaining the scenario buttons */}
                      <div className="relative" ref={headerInfoRef}>
                        <button
                          onClick={(e) => { e.stopPropagation(); setShowHeaderInfo(s => !s); }}
                          aria-haspopup="dialog"
                          aria-expanded={showHeaderInfo}
                          className="p-1 rounded hover:bg-white/5 ml-2"
                          title="What do these scenario buttons do?"
                        >
                          <Info className="w-4 h-4 text-gray-300" />
                        </button>

                        {showHeaderInfo && (
                          <div className="absolute right-0 mt-2 w-80 bg-black/90 border border-white/10 p-3 rounded shadow-lg text-sm text-gray-200 z-50">
                            <div className="font-semibold">Scenario Buttons</div>
                            <div className="text-xs text-gray-300 mt-1">
                              <div className="mt-1">
                                <strong>Weather Change</strong>: Simulates adverse weather effects. It reduces passing effectiveness (example: applies a ~15% reduction to passing-based predictions) and lowers overall confidence for affected stats.
                              </div>
                              <div className="mt-2">
                                <strong>High Scoring</strong>: Simulates a high-scoring environment. It increases predicted offensive stats (example: increases expected yardage/points by ~15–20%) and may raise confidence for offensive players.
                              </div>
                              <div className="mt-2 text-xs">These are temporary scenario simulations sent to the server to demonstrate how event/context changes can shift model predictions in real time.</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {predictions.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                      Waiting for predictions...
                    </div>
                  )}

                  <div className="space-y-4">
                    {predictions.map((item) => (
                      <div
                        key={item.prediction.player_id}
                        className={`border rounded-xl p-4 transition-all cursor-pointer ${
                          selectedPlayer === item.prediction.player_id
                            ? 'border-cyan-400/50 bg-cyan-400/10' 
                            : 'border-white/10 hover:border-white/20'
                        }`}
                        onClick={() => setSelectedPlayer(
                          selectedPlayer === item.prediction.player_id ? null : item.prediction.player_id
                        )}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-r from-cyan-400 to-purple-400 rounded-full flex items-center justify-center text-sm font-bold">
                              {item.prediction.player_name.split(' ').map(n => n[0]).join('')}
                            </div>
                            <div>
                              <div className="font-semibold">{item.prediction.player_name}</div>
                              <div className="text-sm text-gray-400">{item.prediction.position}</div>
                            </div>
                          </div>
                          <ConfidenceWithInfo confidence={item.prediction.overall_confidence} />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                          {Object.entries(item.prediction?.predictions || {}).map(([statType, statData]) => (
                            <div key={statType} className="bg-white/5 rounded p-3">
                              <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                                {statType.replace('_', ' ')}
                              </div>
                              <div className="text-lg font-bold text-white">
                                {statData.predicted_value}
                                {statData.live_stats > 0 && (
                                  <span className="text-xs text-green-400 ml-2">
                                    +{statData.live_stats} live
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-gray-400 mt-1">
                                {statData.probability_over ? `Over: ${(statData.probability_over * 100).toFixed(0)}%` : 'Over: N/A'}
                              </div>
                              <div className="w-full bg-white/10 rounded-full h-1.5 mt-2">
                                <div 
                                  className="bg-cyan-400 h-1.5 rounded-full transition-all"
                                  style={{ width: `${statData.confidence * 100}%` }}
                                />
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                {(statData.confidence ? (statData.confidence * 100).toFixed(0) : 'N/A')}%
                              </div>
                            </div>
                          ))}
                        </div>

                        {selectedPlayer === item.prediction?.player_id && item.explanation && (
                          <div className="mt-4 pt-4 border-t border-white/10">
                            <div className="text-sm text-gray-300">
                              <p className="mb-2">{item.explanation?.overall_summary || 'No explanation available.'}</p>
                              {item.explanation.key_factors && (
                                <div className="mt-2">
                                  <span className="text-xs font-semibold text-gray-400">Key Factors:</span>
                                  <ul className="mt-1 space-y-1">
                                    {item.explanation.key_factors.map((factor, idx) => (
                                      <li key={idx} className="text-xs text-gray-400">• {factor}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Sidebar */}
              <div className="space-y-6">
                {/* Live Events */}
                <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                  <h3 className="text-lg font-bold mb-4 flex items-center">
                    <Zap className="w-5 h-5 mr-2" />
                    Live Events
                  </h3>
                  <div className="space-y-3">
                    {liveEvents.slice(0, 5).map((event) => (
                      <div key={event.id} className="flex items-center space-x-3 bg-white/5 rounded-lg p-3">
                        <div className="text-lg">{getEventIcon(event.type)}</div>
                        <div className="flex-1">
                          <div className="text-sm font-medium">{event.description}</div>
                          <div className="text-xs text-gray-400">Q{event.quarter} • {new Date(event.timestamp).toLocaleTimeString()}</div>
                        </div>
                      </div>
                    ))}
                    {liveEvents.length === 0 && (
                      <div className="text-sm text-gray-400 text-center py-4">
                        Waiting for live events...
                      </div>
                    )}
                  </div>
                </div>

                {/* Cedar AI Chat */}
                <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                  <h3 className="text-lg font-bold mb-4 flex items-center">
                    <MessageCircle className="w-5 h-5 mr-2" />
                    Cedar AI Explainer
                  </h3>
                  
                  <div className="h-64 overflow-y-auto mb-4 space-y-3">
                    {chatMessages.length === 0 && (
                      <div className="text-sm text-gray-400 text-center py-8">
                        Welcome to SeeThePlay! Ask me about player predictions, confidence levels, or what factors influence the forecasts.
                      </div>
                    )}
                    {chatMessages.map((msg) => (
                      <div key={msg.id} className={`${msg.type === 'user' ? 'text-right' : 'text-left'}`}>
                        {msg.playerName && (
                          <div className={`text-xs ${msg.type === 'user' ? 'text-cyan-300' : 'text-purple-300'} mb-1`}>
                            {msg.playerName}
                          </div>
                        )}
                        <div className={`inline-block max-w-xs p-3 rounded-lg text-sm ${
                          msg.type === 'user' 
                            ? 'bg-cyan-500/20 text-cyan-200' 
                            : 'bg-purple-500/20 text-purple-200'
                        }`}>
                          {msg.text}
                        </div>
                      </div>
                    ))}
                    {isAssistantThinking && (
                      <div className="text-left">
                        <div className="inline-flex items-center max-w-xs p-3 rounded-lg text-sm bg-purple-500/10 text-purple-200" role="status" aria-live="polite">
                          <span className="mr-2">Cedar is typing</span>
                          <span className="inline-block w-3 h-3 rounded-full border-2 border-white/30 border-t-transparent animate-spin" aria-hidden="true" />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Show player context badge above input if available */}
                  <div className="mb-2">
                    {(() => {
                      const pname = selectedPlayer ? (predictions.find(p => p.prediction.player_id === selectedPlayer)?.prediction?.player_name) : (predictions[0]?.prediction?.player_name);
                      return pname ? (
                        <div className="inline-flex items-center px-2 py-1 text-xs bg-white/5 rounded-full text-gray-300">Asking about: <span className="ml-2 font-semibold text-white">{pname}</span></div>
                      ) : null;
                    })()}
                  </div>

                  <form onSubmit={handleChatSubmit} className="flex gap-2">
                    <input
                      type="text"
                      value={currentQuestion}
                      onChange={(e) => setCurrentQuestion(e.target.value)}
                      placeholder="Ask about predictions..."
                      className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-cyan-400/50"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 rounded-lg text-sm font-semibold transition-colors"
                    >
                      Ask
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </>
        ) : activePage === 'playground' ? (
          // Render the full playground (field SVG + markers + pickers)
          renderPlayground()
         ) : activePage === 'live' ? (
          // Live page
          <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 mb-6 border border-white/10 text-gray-300">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <Zap className="w-5 h-5 mr-2" />
              Live Games
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Example live game card */}
              <div className="bg-white/10 rounded-lg p-4">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">LIVE</span>
                  <span className="text-sm text-gray-400">Quarter 2 • 8:45</span>
                </div>
                <div className="flex justify-between items-center">
                  <div className="text-center flex-1">
                    <div className="text-2xl font-bold text-white">24</div>
                    <div className="text-sm text-gray-400">Eagles</div>
                  </div>
                  <div className="text-center px-4">
                    <div className="text-sm font-semibold">VS</div>
                  </div>
                  <div className="text-center flex-1">
                    <div className="text-2xl font-bold text-white">17</div>
                    <div className="text-sm text-gray-400">Cowboys</div>
                  </div>
                </div>
                <div className="mt-4">
                  <button className="w-full bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 py-2 rounded text-sm transition-colors">
                    View Details
                  </button>
                </div>
              </div>
              
              {/* Placeholder for upcoming game */}
              <div className="bg-white/10 rounded-lg p-4">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-xs bg-gray-500/20 text-gray-400 px-2 py-1 rounded">UPCOMING</span>
                  <span className="text-sm text-gray-400">Today 4:30 PM</span>
                </div>
                <div className="flex justify-between items-center">
                  <div className="text-center flex-1">
                    <div className="text-2xl font-bold text-gray-400">--</div>
                    <div className="text-sm text-gray-400">Ravens</div>
                  </div>
                  <div className="text-center px-4">
                    <div className="text-sm font-semibold text-gray-400">VS</div>
                  </div>
                  <div className="text-center flex-1">
                    <div className="text-2xl font-bold text-gray-400">--</div>
                    <div className="text-sm text-gray-400">Browns</div>
                  </div>
                </div>
                <div className="mt-4">
                  <button className="w-full bg-white/5 hover:bg-white/10 text-gray-400 py-2 rounded text-sm transition-colors">
                    Reminder
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Teams page
          <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 mb-6 border border-white/10 text-gray-300">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Teams</h2>
              <button
                onClick={loadTeams}
                className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 rounded-lg text-sm transition-colors"
              >
                Refresh Teams
              </button>
            </div>

            {teamsLoading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
              </div>
            )}

            {teamsError && (
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 mb-6 text-red-400">
                <div className="font-semibold">Error Loading Teams</div>
                <div className="text-sm mt-1">{teamsError}</div>
                <div className="text-xs mt-2 text-gray-300">Requesting: {API_BASE_URL}/api/v1/teams</div>
              </div>
            )}

            {!teamsLoading && teams.length === 0 && !teamsError && (
              <div className="text-center py-8 text-gray-400">
                <div className="text-3xl mb-2">🏈</div>
                <div>No teams loaded — try clicking Refresh or check backend.</div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {teams.map(team => (
                <div 
                  key={team.id} 
                  className={`bg-white/10 backdrop-blur-sm rounded-xl p-4 border transition-all ${
                    selectedTeamDetails?.id === team.id ? 'border-cyan-500/50' : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="font-semibold text-lg">
                        {team.market ? `${team.market} ${team.name}` : team.name}
                      </div>
                      <div className="text-sm text-gray-400">{team.abbreviation || team.id}</div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={async () => {
                          if (selectedTeamDetails?.id === team.id) {
                            setSelectedTeamDetails(null);
                            return;
                          }
                          setTeamDetailsLoading(true);
                          try {
                            const details = await getTeamDetails(team.id);
                            // Try to fetch players but don't fail the whole request if players are missing
                            let players = [];
                            try {
                              players = await getTeamPlayers(team.id);
                            } catch (pErr) {
                              console.warn(`Failed to fetch players for team ${team.id}:`, pErr);
                              // Surface players error inside the selectedTeamDetails so user can retry
                              setSelectedTeamDetails({ ...details, id: team.id, players: [], players_error: pErr?.message || String(pErr) });
                              setTeamDetailsLoading(false);
                              return;
                            }
                            setSelectedTeamDetails({ ...details, id: team.id, players: players || [] });
                          } catch (err) {
                            console.error('Failed to load team details', err);
                            setSelectedTeamDetails({ id: team.id, error: err?.message || 'Failed to load details', players: [] });
                          } finally {
                            setTeamDetailsLoading(false);
                          }
                        }}
                        className={`px-3 py-1 rounded text-sm transition-colors ${
                          selectedTeamDetails?.id === team.id ? 'bg-cyan-500/30 text-cyan-300' : 'bg-white/5 hover:bg-white/10'
                        }`}
                      >
                        {selectedTeamDetails?.id === team.id ? 'Hide' : 'View Roster'}
                       </button>
                    </div>
                  </div>

                  {selectedTeamDetails?.id === team.id && (
                    <div className="mt-4 border-t border-white/10 pt-4">
                      {teamDetailsLoading ? (
                        <div className="flex items-center justify-center py-4">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-500"></div>
                        </div>
                      ) : selectedTeamDetails.error ? (
                        <div className="text-red-400 text-sm">{selectedTeamDetails.error}</div>
                      ) : (
                        <div>
                          <div className="text-sm font-semibold mb-3">Team Roster</div>
                          <div className="grid grid-cols-1 gap-2 max-h-96 overflow-y-auto pr-2">
                            {selectedTeamDetails.players?.length > 0 ? selectedTeamDetails.players.map(player => (
                               <div 
                                 key={player.id}
                                 className="bg-white/5 rounded-lg p-3 hover:bg-white/10 transition-colors cursor-pointer group"
                                 onClick={() => toggleRosterPlayer(player)}
                               >
                                 <div className="flex items-center justify-between">
                                   <div>
                                     <div className="font-medium">{player.first_name} {player.last_name}</div>
                                     <div className="text-xs text-gray-400">{player.position} #{player.jersey_number || 'N/A'}</div>
                                   </div>
                                   <div className="text-xs px-2 py-1 rounded bg-cyan-500/20 text-cyan-300 opacity-0 group-hover:opacity-100 transition-opacity">
                                     View Stats
                                   </div>
                                 </div>

                                 {selectedRosterPlayer === player.id && (
                                   <div className="mt-3 pt-3 border-t border-white/10">
                                     {playerPredictionsLoading === player.id ? (
                                       <div className="flex items-center justify-center py-4">
                                         <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-500"></div>
                                       </div>
                                     ) : playerPredictionsError ? (
                                       <div className="text-red-400 text-sm">{playerPredictionsError}</div>
                                     ) : (
                                       (() => {
                                         const pred = playerPredictionsMap[player.id];
                                         if (!pred) {
                                           return <div className="text-xs text-gray-400">No prediction available.</div>;
                                         }

                                         return (
                                           <div>
                                             <div className="flex items-center justify-between mb-3">
                                               <div>
                                                 <div className="font-semibold">{pred.player_name} — {pred.position}</div>
                                                 <div className="text-xs text-gray-400">Updated: {new Date(pred.timestamp).toLocaleString()}</div>
                                               </div>
                                               <ConfidenceWithInfo confidence={pred.overall_confidence} />
                                             </div>

                                             <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                               {Object.entries(pred.predictions || {}).map(([statType, statData]) => (
                                                 <div key={statType} className="bg-white/6 rounded p-3">
                                                   <div className="text-xs text-gray-300 uppercase tracking-wide mb-1">{statType.replace('_',' ')}</div>
                                                   <div className="text-lg font-bold">{statData.predicted_value}</div>
                                                   <div className="text-xs text-gray-400">Over: {(statData.probability_over*100).toFixed(0)}%</div>
                                                   <div className="w-full bg-white/10 rounded-full h-1.5 mt-2">
                                                     <div className="bg-cyan-400 h-1.5 rounded-full transition-all" style={{ width: `${(statData.confidence||0)*100}%` }} />
                                                   </div>
                                                 </div>
                                               ))}
                                             </div>
                                           </div>
                                         );
                                       })()
                                     )}
                                   </div>
                                 )}
                                </div>
                            )) : (
                              <div className="text-sm text-gray-400">
                                No players found for this team.
                                {selectedTeamDetails.players_error && (
                                  <div className="mt-2 text-xs text-red-300">{selectedTeamDetails.players_error}</div>
                                )}
                                <div className="mt-2">
                                  <button
                                    onClick={async () => {
                                      // Retry loading players only
                                      setTeamDetailsLoading(true);
                                      try {
                                        const players = await getTeamPlayers(team.id);
                                        setSelectedTeamDetails(prev => ({ ...prev, players: players || [], players_error: undefined }));
                                      } catch (retryErr) {
                                        console.error('Retry failed to fetch players', retryErr);
                                        setSelectedTeamDetails(prev => ({ ...prev, players: [], players_error: retryErr?.message || String(retryErr) }));
                                      } finally {
                                        setTeamDetailsLoading(false);
                                      }
                                    }}
                                    className="mt-2 px-3 py-1 bg-white/5 rounded text-xs"
                                  >Retry players</button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SeeThePlayDashboard;