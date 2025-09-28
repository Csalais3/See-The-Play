#!/usr/bin/env python3
# backend/test_backend.py - Test all backend components

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
PULSE_URL = "http://localhost:1339"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_pulse_mock():
    """Test Pulse Mock connection"""
    print("\n🔍 Testing Pulse Mock API...")
    try:
        response = requests.get(f"{PULSE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Pulse Mock is running")
            return True
        else:
            print(f"❌ Pulse Mock failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Pulse Mock error: {e}")
        return False

def test_teams():
    """Test teams endpoint"""
    print("\n🔍 Testing teams endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/predictions/teams", timeout=10)
        if response.status_code == 200:
            teams = response.json()
            print(f"✅ Teams endpoint working - Found {len(teams)} teams")
            if teams:
                print(f"   Sample team: {teams[0].get('name', 'Unknown')}")
            return True
        else:
            print(f"❌ Teams endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Teams error: {e}")
        return False

def test_predictions():
    """Test predictions endpoint"""
    print("\n🔍 Testing predictions endpoint...")
    try:
        # First get teams to find Eagles
        teams_response = requests.get(f"{BASE_URL}/api/predictions/teams", timeout=10)
        teams = teams_response.json()
        
        eagles = None
        for team in teams:
            if 'eagles' in team.get('name', '').lower() or 'eagles' in team.get('alias', '').lower():
                eagles = team
                break
        
        if not eagles:
            print("⚠️  Eagles team not found, using first available team")
            eagles = teams[0] if teams else None
        
        if not eagles:
            print("❌ No teams available for testing")
            return False
        
        team_id = eagles.get('id')
        team_name = eagles.get('name', 'Unknown')
        
        print(f"   Using team: {team_name} (ID: {team_id})")
        
        # Get predictions
        response = requests.get(
            f"{BASE_URL}/api/predictions/team/{team_id}/players",
            params={"limit": 5},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            predictions = data.get('predictions', [])
            print(f"✅ Predictions endpoint working - {len(predictions)} predictions returned")
            
            if predictions:
                pred = predictions[0]
                player = pred.get('prediction', {})
                print(f"   Sample: {player.get('player_name')} - {player.get('position')}")
                print(f"   Confidence: {player.get('overall_confidence', 0)*100:.1f}%")
            
            return True
        else:
            print(f"❌ Predictions endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Predictions error: {e}")
        return False

def test_live_games():
    """Test live games endpoint"""
    print("\n🔍 Testing live games endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/live/games", timeout=10)
        if response.status_code == 200:
            games = response.json()
            print(f"✅ Live games endpoint working - {len(games)} games found")
            return True
        else:
            print(f"❌ Live games failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Live games error: {e}")
        return False

def test_websocket():
    """Test WebSocket connection (basic check)"""
    print("\n🔍 Testing WebSocket endpoint...")
    try:
        import websocket
        ws = websocket.create_connection(f"ws://localhost:8000/ws", timeout=5)
        print("✅ WebSocket connection successful")
        ws.close()
        return True
    except ImportError:
        print("⚠️  websocket-client not installed, skipping WebSocket test")
        print("   Install with: pip install websocket-client")
        return True
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False

def run_all_tests():
    """Run all backend tests"""
    print("=" * 60)
    print("🧪 SeeThePlay Backend Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Pulse Mock", test_pulse_mock()))
    results.append(("Teams Endpoint", test_teams()))
    results.append(("Predictions Endpoint", test_predictions()))
    results.append(("Live Games Endpoint", test_live_games()))
    results.append(("WebSocket Connection", test_websocket()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(run_all_tests())