// frontend/src/App.js - COMPLETE FILE
import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, MessageCircle, Zap, Target, AlertTriangle } from 'lucide-react';

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

  useEffect(() => {
    const initializeDashboard = async () => {
      try {
        // Fetch Eagles team ID
        const teamsResponse = await fetch('http://localhost:8000/api/predictions/teams');
        const teams = await teamsResponse.json();
        const eagles = teams.find(t => t.name === 'Eagles');
        
        if (!eagles) {
          console.error('Eagles team not found');
          loadDemoData();
          return;
        }
        
        // Fetch real predictions from backend
        const predictionsResponse = await fetch(`http://localhost:8000/api/predictions/team/${eagles.id}/players?limit=10`);
        const predictionsData = await predictionsResponse.json();
        
        // Transform backend data to frontend format
        const transformedPredictions = predictionsData.predictions.map(pred => ({
          prediction: pred,
          explanation: {
            overall_summary: `${pred.player_name} (${pred.position}) prediction based on ML analysis`,
            narrative_explanations: Object.keys(pred.predictions).reduce((acc, stat) => {
              acc[stat] = `Projected ${pred.predictions[stat].predicted_value} ${stat.replace('_', ' ')} with ${(pred.predictions[stat].confidence * 100).toFixed(0)}% confidence.`;
              return acc;
            }, {})
          }
        }));
        
        setPredictions(transformedPredictions);
        
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
        
      } catch (error) {
        console.error('Error fetching predictions:', error);
        loadDemoData();
      }
      
      // Connect to WebSocket for live updates
      const websocket = new WebSocket('ws://localhost:8000/ws');
      
      websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
      };
      
      websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('📩 WebSocket message:', message);
        
        if (message.type === 'game_initialized') {
          setGameState(message.game_state);
          
          if (message.initial_predictions) {
            setPredictions(message.initial_predictions);
          }
        } else if (message.type === 'live_update') {
          setGameState(message.game_state);
          
          const newEvent = {
            id: message.event.id,
            type: message.event.type,
            timestamp: message.timestamp,
            player_name: message.event.player_name,
            description: message.event.description,
            quarter: message.event.quarter,
            impact: message.event.impact || 'neutral'
          };
          setLiveEvents(prev => [newEvent, ...prev.slice(0, 9)]);
          
          if (message.updated_prediction) {
            setPredictions(prev => prev.map(p => {
              if (p.prediction.player_id === message.updated_prediction.player_id) {
                return {
                  prediction: message.updated_prediction,
                  explanation: message.explanation
                };
              }
              return p;
            }));
          }
        } else if (message.type === 'scenario_update') {
          if (message.updated_predictions) {
            message.updated_predictions.forEach(update => {
              setPredictions(prev => prev.map(p => {
                if (p.prediction.player_id === update.prediction.player_id) {
                  return update;
                }
                return p;
              }));
            });
          }
        }
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
      
      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
      };
      
      setWs(websocket);
      
      setChatMessages([
        {
          id: 'welcome',
          type: 'system',
          message: "Welcome to SeeThePlay! Ask me about player predictions, confidence levels, or what factors influence the forecasts.",
          timestamp: new Date().toISOString()
        }
      ]);
      
      return () => {
        websocket.close();
      };
    };
    
    const loadDemoData = () => {
      const demoData = [
        {
          prediction: {
            player_id: 'player_001',
            player_name: 'Jalen Hurts',
            position: 'QB',
            predictions: {
              passing_yards: { predicted_value: 275.0, confidence: 0.850, probability_over: 0.72, live_stats: 0 },
              rushing_yards: { predicted_value: 45.0, confidence: 0.780, probability_over: 0.68, live_stats: 0 },
              touchdowns: { predicted_value: 2.1, confidence: 0.820, probability_over: 0.70, live_stats: 0 }
            },
            overall_confidence: 0.817
          },
          explanation: {
            overall_summary: "Jalen Hurts (QB) is expected to have a strong overall performance today.",
            narrative_explanations: {
              passing_yards: "Projected 275 passing yards with 85% confidence.",
            }
          }
        }
      ];
      setPredictions(demoData);
      
      const initialGameState = {
        game_id: 'demo_game',
        quarter: 1,
        time_remaining: '15:00',
        home_team: 'Philadelphia Eagles',
        away_team: 'Generic Opponents',
        home_score: 0,
        away_score: 0,
        status: 'in_progress'
      };
      setGameState(initialGameState);
    };
    
    initializeDashboard();
  }, []);

  const handleQuestionSubmit = async () => {
    if (!currentQuestion.trim()) return;

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      message: currentQuestion,
      timestamp: new Date().toISOString()
    };
    setChatMessages(prev => [...prev, userMessage]);

    try {
      const targetPlayer = selectedPlayer 
        ? predictions.find(p => p.prediction.player_id === selectedPlayer)?.prediction
        : predictions[0]?.prediction;

      if (!targetPlayer) {
        throw new Error('No player data available');
      }

      const response = await fetch('http://localhost:8000/api/predictions/question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: currentQuestion,
          player_data: targetPlayer
        })
      });

      const data = await response.json();
      
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        message: data.answer,
        timestamp: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, aiMessage]);
      
    } catch (error) {
      console.error('Error asking question:', error);
      
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        message: "I'm having trouble connecting. Make sure the backend is running on port 8000.",
        timestamp: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, aiMessage]);
    }

    setCurrentQuestion('');
  };

  const triggerScenario = (scenarioType) => {
    const scenarios = {
      weather: {
        type: 'weather_change',
        description: 'Weather conditions worsen - expect 15-20% decrease in passing stats',
        impact: 'negative'
      },
      script: {
        type: 'game_script',
        description: 'Game becomes high-scoring - all offensive stats likely to increase',
        impact: 'positive'
      }
    };

    setScenario(scenarios[scenarioType]);
    
    // Send to backend via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'scenario_change',
        data: { type: scenarioType, severity: 0.15 }
      }));
    }
    
    setTimeout(() => setScenario(null), 5000);
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100';
    if (confidence >= 0.7) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'touchdown': return '🏈';
      case 'field_goal': return '⚽';
      case 'pass_completion': return '✅';
      case 'reception': return '📥';
      case 'rush_attempt': return '🏃';
      case 'sack': return '❌';
      default: return '📊';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 text-white">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-cyan-400 to-purple-400 rounded-lg flex items-center justify-center">
                <Target className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                  SeeThePlay
                </h1>
                <p className="text-sm text-gray-300">You don't just get numbers, you see them.</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                <span className="text-sm">{isConnected ? 'Live' : 'Disconnected'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
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
                  Live Predictions
                </h2>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => triggerScenario('weather')}
                    className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-sm hover:bg-blue-500/30 transition-colors"
                  >
                    Weather Change
                  </button>
                  <button 
                    onClick={() => triggerScenario('script')}
                    className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg text-sm hover:bg-green-500/30 transition-colors"
                  >
                    High Scoring
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                {predictions.map((item, index) => (
                  <div 
                    key={item.prediction.player_id}
                    className={`bg-white/5 rounded-lg p-4 border transition-all cursor-pointer ${
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
                      <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getConfidenceColor(item.prediction.overall_confidence)}`}>
                        {(item.prediction.overall_confidence * 100).toFixed(0)}% Confidence
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                      {Object.entries(item.prediction.predictions).map(([statType, statData]) => (
                        <div key={statType} className="bg-white/5 rounded p-3">
                          <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                            {statType.replace('_', ' ')}
                          </div>
                          <div className="text-lg font-bold text-white">
                            {statData.predicted_value}
                            {statData.live_stats > 0 && (
                              <span className="text-xs text-green-400 ml-1">
                                ({statData.live_stats} live)
                              </span>
                            )}
                          </div>
                          <div className="flex justify-between text-xs text-gray-300">
                            <span>Over: {(statData.probability_over * 100).toFixed(0)}%</span>
                            <span>{(statData.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <div className="w-full bg-gray-700 rounded-full h-1 mt-2">
                            <div 
                              className="bg-gradient-to-r from-cyan-400 to-purple-400 h-1 rounded-full"
                              style={{ width: `${statData.confidence * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    {selectedPlayer === item.prediction.player_id && (
                      <div className="border-t border-white/10 pt-3">
                        <div className="text-sm text-gray-300">
                          <strong className="text-white">Analysis:</strong> {item.explanation.overall_summary}
                        </div>
                        {Object.entries(item.explanation.narrative_explanations || {}).map(([stat, explanation]) => (
                          <div key={stat} className="mt-2 text-xs text-gray-400">
                            <strong className="text-gray-300">{stat.replace('_', ' ')}:</strong> {explanation}
                          </div>
                        ))}
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
                {chatMessages.map((msg) => (
                  <div key={msg.id} className={`${msg.type === 'user' ? 'text-right' : 'text-left'}`}>
                    <div className={`inline-block max-w-xs p-3 rounded-lg text-sm ${
                      msg.type === 'user' 
                        ? 'bg-cyan-500/20 text-cyan-200' 
                        : msg.type === 'ai'
                        ? 'bg-purple-500/20 text-purple-200'
                        : 'bg-gray-500/20 text-gray-300'
                    }`}>
                      {msg.message}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex space-x-2">
                <input
                  type="text"
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleQuestionSubmit()}
                  placeholder="Ask about predictions..."
                  className="flex-1 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-cyan-400"
                />
                <button 
                  onClick={handleQuestionSubmit}
                  className="bg-gradient-to-r from-cyan-500 to-purple-500 px-4 py-2 rounded-lg text-sm font-medium hover:from-cyan-400 hover:to-purple-400 transition-all"
                >
                  Ask
                </button>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {['How many passing yards?', 'Which player is best?', 'Any concerns?'].map((question) => (
                  <button
                    key={question}
                    onClick={() => setCurrentQuestion(question)}
                    className="text-xs px-3 py-1 bg-white/10 rounded-full hover:bg-white/20 transition-colors"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SeeThePlayDashboard;