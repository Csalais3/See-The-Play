# backend/test_pulse_integration.py
#!/usr/bin/env python3
"""
Test script to verify PrizePicks Pulse Mock integration
"""
import asyncio
import logging
from utils.api_clients import PulseAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pulse_integration():
    """Test all Pulse API endpoints"""
    
    print("🏈 Testing PrizePicks Pulse Mock Integration")
    print("=" * 50)
    
    client = PulseAPIClient()
    
    # Test 1: Get all teams
    print("\n📋 Test 1: Getting all NFL teams...")
    teams = client.get_teams()
    print(f"✅ Found {len(teams)} teams")
    
    if teams:
        print(f"   Sample team: {teams[0]['market']} {teams[0]['name']}")
    
    # Test 2: Find Eagles (we have full data for them)
    print("\n🦅 Test 2: Finding Philadelphia Eagles...")
    eagles = client.find_team_by_name("Eagles")
    if eagles:
        print(f"✅ Found Eagles: {eagles['market']} {eagles['name']} (ID: {eagles['id']})")
        eagles_id = eagles['id']
        
        # Test 3: Get Eagles players
        print("\n👥 Test 3: Getting Eagles players...")
        players = client.get_team_players(eagles_id)
        print(f"✅ Found {len(players)} Eagles players")
        
        if players:
            print(f"   Sample player: {players[0].get('first_name')} {players[0].get('last_name')} ({players[0].get('position')})")
        
        # Test 4: Get Eagles stats
        print("\n📊 Test 4: Getting Eagles statistics...")
        stats = client.get_team_statistics(eagles_id)
        if stats:
            print(f"✅ Eagles stats: {stats}")
        
        # Test 5: Get quarterbacks
        print("\n🏈 Test 5: Getting all quarterbacks...")
        qbs = client.get_players_by_position("QB")
        print(f"✅ Found {len(qbs)} quarterbacks")
        
        if qbs:
            print(f"   Sample QB: {qbs[0].get('first_name')} {qbs[0].get('last_name')}")
    
    else:
        print("❌ Could not find Eagles team")
    
    # Test 6: Get all games
    print("\n🎮 Test 6: Getting all games...")
    games = client.get_all_games()
    print(f"✅ Found {len(games)} games")
    
    if games:
        print(f"   Sample game: {games[0].get('name', 'Game')}")
    
    print("\n🎯 Pulse Mock Integration Test Complete!")
    print(f"   Teams: {len(teams)}")
    print(f"   Eagles Players: {len(players) if 'players' in locals() else 0}")
    print(f"   QBs: {len(qbs) if 'qbs' in locals() else 0}")
    print(f"   Games: {len(games)}")

if __name__ == "__main__":
    asyncio.run(test_pulse_integration())
