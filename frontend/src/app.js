// frontend/src/App.js - FINAL FIXED VERSION
import React, { useState, useEffect, useRef } from 'react';
import { Activity, TrendingUp, MessageCircle, Zap, Target, AlertTriangle, Info } from 'lucide-react';
import { getTeams, getTeamDetails, getTeamPlayers, getTeamStats, getPlayerStats, API_BASE_URL, getPlayerPredictions as apiGetPlayerPredictions } from './services/api';

const SeeThePlayDashboard = () => {
  const [gameState, setGameState] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [liveEvents, setLiveEvents] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [ws, setWs] = useState(null);
  const [teams, setTeams] = useState([]);
  const [teamsLoading, setTeamsLoading] = useState(false);
  const [teamsError, setTeamsError] = useState(null);
  const [selectedTeamDetails, setSelectedTeamDetails] = useState(null);
  const [teamDetailsLoading, setTeamDetailsLoading] = useState(false);
  const [selectedRosterPlayer, setSelectedRosterPlayer] = useState(null);
  const [isAssistantThinking, setIsAssistantThinking] = useState(false);
  const [showHeaderInfo, setShowHeaderInfo] = useState(false);
  const headerInfoRef = useRef(null);
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
      
      // Send initial game state to backend
      if (ws) {
        ws.send(JSON.stringify({
          type: 'game_reset',
          data: initialGameState
        }));
      }
      
      // Connect to WebSocket for live updates
      const websocket = new WebSocket('ws://localhost:8000/ws');
      
      websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
      };
      
      websocket.onmessage = (event) => {
        let message = null;
        try {
          message = JSON.parse(event.data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err, event.data);
          return; // ignore malformed messages
        }

        try {
          console.log('📩 WebSocket message:', message.type, message);

          // Handle tick updates (game clock)
          if (message.type === 'tick') {
            if (message.game_state) {
              // Check if game has ended (Q4 and time is 0:00)
              if (message.game_state.quarter === 4 && message.game_state.time_remaining === '0:00') {
                // Reset the game
                ws.send(JSON.stringify({
                  type: 'game_reset',
                  data: {
                    game_id: 'sim_game_001',
                    quarter: 1,
                    time_remaining: '15:00',
                    home_team: message.game_state.home_team,
                    away_team: message.game_state.away_team,
                    home_score: 0,
                    away_score: 0,
                    status: 'in_progress'
                  }
                }));
              } else {
                setGameState(message.game_state);
              }
            }
            return;
          }

          if (message.type === 'game_initialized') {
            console.log('🎮 Game initialized with', message.initial_predictions?.length, 'predictions');
            setGameState(message.game_state);

            if (message.initial_predictions && message.initial_predictions.length > 0) {
              setPredictions(message.initial_predictions);
              console.log('✅ Set predictions:', message.initial_predictions.map(p => p.prediction?.player_name));
            }
          } else if (message.type === 'live_update') {
            setGameState(message.game_state);
            
            // Add new event - deduplicate by ID
            const newEvent = {
              id: message.event.id,
              type: message.event.type,
              description: message.event.description,
              quarter: message.event.quarter,
              timestamp: message.event.timestamp
            };
            
            // Keep only most recent 5 events, newest first
            setLiveEvents(prev => {
              const exists = prev.some(e => e.id === newEvent.id);
              if (exists) return prev;
              return [newEvent, ...prev].slice(0, 5);
            });
            
            // Update predictions if player affected
            if (message.updated_prediction) {
              setPredictions(prev => {
                const playerIndex = prev.findIndex(
                  p => p.prediction.player_id === message.updated_prediction.player_id
                );
                
                if (playerIndex >= 0) {
                  const updated = [...prev];
                  updated[playerIndex] = {
                    prediction: message.updated_prediction,
                    explanation: message.explanation
                  };
                  return updated;
                }
                return prev;
              });
            }
          } else if (message.type === 'scenario_update') {
            setScenario(message.scenario);

            if (message.updated_predictions) {
              setPredictions(message.updated_predictions);
            }

            setTimeout(() => setScenario(null), 5000);

          // Handle Cedar AI answers
          } else if (message.type === 'cedar_answer') {
            try {
              // Try to resolve player name from the message; backend may include player_id
              let playerName = message.player_name || null;
              if (!playerName && message.player_id) {
                const found = predictions.find(p => p.prediction.player_id === message.player_id);
                playerName = found?.prediction?.player_name || null;
              }

              const assistantMsg = {
                id: Date.now() + Math.floor(Math.random() * 1000),
                type: 'assistant',
                text: message.answer || 'No answer available.',
                playerName: playerName,
                playerId: message.player_id
              };

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
        console.log('❌ WebSocket disconnected');
        setIsConnected(false);
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
      
      setWs(websocket);
      
      return () => {
        websocket.close();
      };
    };
    
    initializeDashboard();
  }, []);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!currentQuestion.trim() || !ws) return;

    if (ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not open - cannot send chat message');
      return;
    }

    // Resolve player name for context (if selected)
    const resolvedPlayerName = (() => {
      if (selectedPlayer) {
        const found = predictions.find(p => p.prediction.player_id === selectedPlayer);
        return found?.prediction?.player_name || null;
      }
      return predictions[0]?.prediction?.player_name || null;
    })();

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: currentQuestion,
      playerName: resolvedPlayerName,
      playerId: selectedPlayer || predictions[0]?.prediction?.player_id
    };

    setChatMessages(prev => [...prev, userMessage]);

    // Send to backend via WebSocket
    ws.send(JSON.stringify({
      type: 'cedar_question',
      question: currentQuestion,
      player_id: userMessage.playerId
    }));

    // Show assistant loading indicator
    setIsAssistantThinking(true);

    setCurrentQuestion('');
  };

  const handleScenarioChange = (scenarioType) => {
    if (!ws) return;
    
    ws.send(JSON.stringify({
      type: 'scenario_change',
      data: {
        type: scenarioType,
        severity: scenarioType === 'weather_change' ? 0.15 : 0.2
      }
    }));
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'bg-green-500/20 text-green-400';
    if (confidence >= 0.7) return 'bg-yellow-500/20 text-yellow-400';
    return 'bg-orange-500/20 text-orange-400';
  };

  const getEventIcon = (eventType) => {
    const icons = {
      pass_completion: '✅',
      rush_attempt: '🏃',
      reception: '📥',
      touchdown: '🏈',
      field_goal: '⚽',
      interception: '❌',
      fumble: '📊',
      sack: '❌',
      timeout: '📊',
      penalty: '📊'
    };
    return icons[eventType] || '📊';
  };

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
          // Playground placeholder
          <>
            <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 mb-6 border border-white/10 text-gray-300">
              <h2 className="text-xl font-bold mb-2">Playground</h2>
              <div className="text-sm">This is the Playground — an empty sandbox for experiments. Content coming soon.</div>
            </div>
          </>
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