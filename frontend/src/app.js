import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, Users, MessageCircle, Zap, Target, BarChart3, Play, Pause, AlertTriangle } from 'lucide-react';

const SeeThePlayDashboard = () => {
  const [gameState, setGameState] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [explanations, setExplanations] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [liveEvents, setLiveEvents] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [scenario, setScenario] = useState(null);

  // WebSocket connection (simulated for demo)
  useEffect(() => {
    // Simulate WebSocket connection
    setIsConnected(true);
    
    // Simulate initial game state
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

    // Simulate initial predictions
    const initialPredictions = [
      {
        prediction: {
          player_id: 'player_001',
          player_name: 'Jalen Hurts',
          position: 'QB',
          predictions: {
            passing_yards: { predicted_value: 285.3, confidence: 0.847, probability_over: 0.73 },
            rushing_yards: { predicted_value: 67.2, confidence: 0.782, probability_over: 0.68 },
            touchdowns: { predicted_value: 2.1, confidence: 0.791, probability_over: 0.71 }
          },
          overall_confidence: 0.807
        },
        explanation: {
          overall_summary: "Jalen Hurts (QB) is expected to have a strong overall performance today with excellent dual-threat capability.",
          narrative_explanations: {
            passing_yards: "Hurts is projected to achieve 285.3 passing yards with 84.7% confidence. The main driver is team pace, which strongly favors higher performance.",
            rushing_yards: "Projected 67.2 rushing yards reflects his excellent mobility and designed runs in the offense."
          }
        }
      },
      {
        prediction: {
          player_id: 'player_002',
          player_name: 'A.J. Brown',
          position: 'WR',
          predictions: {
            receiving_yards: { predicted_value: 89.4, confidence: 0.823, probability_over: 0.76 },
            touchdowns: { predicted_value: 0.8, confidence: 0.745, probability_over: 0.62 }
          },
          overall_confidence: 0.784
        },
        explanation: {
          overall_summary: "A.J. Brown (WR) should see significant targets with good receiving production.",
          narrative_explanations: {
            receiving_yards: "Brown is projected for 89.4 receiving yards with strong target share expectations."
          }
        }
      },
      {
        prediction: {
          player_id: 'player_003',
          player_name: 'D\'Andre Swift',
          position: 'RB',
          predictions: {
            rushing_yards: { predicted_value: 78.6, confidence: 0.756, probability_over: 0.69 },
            receiving_yards: { predicted_value: 34.2, confidence: 0.692, probability_over: 0.58 },
            touchdowns: { predicted_value: 0.9, confidence: 0.738, probability_over: 0.64 }
          },
          overall_confidence: 0.729
        },
        explanation: {
          overall_summary: "D'Andre Swift (RB) should have solid performance with both rushing and receiving opportunities.",
          narrative_explanations: {
            rushing_yards: "Swift projected for 78.6 rushing yards with moderate confidence due to game script uncertainty."
          }
        }
      }
    ];

    setPredictions(initialPredictions);

    // Simulate live events
    let eventCount = 0;
    const eventInterval = setInterval(() => {
      if (eventCount < 20) {
        const eventTypes = ['pass_completion', 'rush_attempt', 'touchdown', 'field_goal', 'sack'];
        const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
        const player = initialPredictions[Math.floor(Math.random() * initialPredictions.length)];
        
        const newEvent = {
          id: `event_${eventCount}`,
          type: eventType,
          timestamp: new Date().toISOString(),
          player_name: player.prediction.player_name,
          description: `${player.prediction.player_name} ${eventType.replace('_', ' ')}`,
          quarter: Math.ceil(eventCount / 5),
          impact: eventType === 'touchdown' ? 'positive' : eventType === 'sack' ? 'negative' : 'neutral'
        };
        
        setLiveEvents(prev => [newEvent, ...prev.slice(0, 9)]);
        
        // Update predictions occasionally
        if (eventCount % 3 === 0 && eventType === 'touchdown') {
          setPredictions(prev => prev.map(p => {
            if (p.prediction.player_id === player.prediction.player_id) {
              return {
                ...p,
                prediction: {
                  ...p.prediction,
                  predictions: {
                    ...p.prediction.predictions,
                    touchdowns: {
                      ...p.prediction.predictions.touchdowns,
                      predicted_value: p.prediction.predictions.touchdowns?.predicted_value + 0.2 || 1.2,
                      confidence: Math.min(0.95, (p.prediction.predictions.touchdowns?.confidence || 0.7) + 0.05)
                    }
                  }
                }
              };
            }
            return p;
          }));
        }
        
        eventCount++;
      } else {
        clearInterval(eventInterval);
      }
    }, 4000);

    // Add welcome message to chat
    setChatMessages([
      {
        id: 'welcome',
        type: 'system',
        message: "Welcome to SeeThePlay! Ask me about player predictions, confidence levels, or what factors influence the forecasts.",
        timestamp: new Date().toISOString()
      }
    ]);

    return () => clearInterval(eventInterval);
  }, []);

  const handleQuestionSubmit = () => {
    if (!currentQuestion.trim()) return;

    // Add user question
    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      message: currentQuestion,
      timestamp: new Date().toISOString()
    };
    setChatMessages(prev => [...prev, userMessage]);

    // Simulate Cedar AI response
    setTimeout(() => {
      let response = "";
      const question = currentQuestion.toLowerCase();
      
      if (question.includes('confidence')) {
        response = "Confidence levels reflect how certain our model is about each prediction. High confidence (>80%) means strong consensus across all factors, while lower confidence indicates mixed signals or uncertainty.";
      } else if (question.includes('yards')) {
        response = "Yardage predictions are based on player skill, recent form, team offensive strength, opponent defense, and game context. Weather and game script can significantly impact these projections.";
      } else if (question.includes('touchdown')) {
        response = "Touchdown predictions consider red zone efficiency, goal line opportunities, player usage patterns, and game flow expectations. Higher-scoring games typically increase all touchdown probabilities.";
      } else if (question.includes('why') || question.includes('how')) {
        response = "Our predictions use machine learning models trained on historical data, considering factors like player performance, team dynamics, opponent strength, weather conditions, and real-time game events.";
      } else {
        response = "I can explain specific predictions, confidence levels, or the factors that influence our forecasts. Try asking about a particular stat or player!";
      }

      const aiMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        message: response,
        timestamp: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, aiMessage]);
    }, 1000);

    setCurrentQuestion('');
  };

  const triggerScenario = (scenarioType) => {
    const scenarios = {
      weather: {
        type: 'weather_change',
        description: 'Weather conditions worsen - expect 15-20% decrease in passing stats',
        impact: 'negative'
      },
      injury: {
        type: 'player_injury',
        description: 'Key player injury - redistributing target share and opportunities',
        impact: 'mixed'
      },
      script: {
        type: 'game_script',
        description: 'Game becomes high-scoring - all offensive stats likely to increase',
        impact: 'positive'
      }
    };

    setScenario(scenarios[scenarioType]);
    
    // Clear scenario after 5 seconds
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
                {['Why this prediction?', 'Confidence levels?', 'Risk factors?'].map((question) => (
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