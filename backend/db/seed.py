# backend/db/seed.py
"""
Database seeding utilities for SeeThePlay
Seeds the database with initial data for development and demo purposes
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import json

from sqlalchemy.orm import Session
from .base import SessionLocal, init_db
from .models import Game, Prediction, GameEvent
from ..utils.api_clients import PulseAPIClient
from ..services.ml_model import PredictionEngine

logger = logging.getLogger(__name__)

class DatabaseSeeder:
    def __init__(self):
        self.pulse_client = PulseAPIClient()
        self.prediction_engine = PredictionEngine(self.pulse_client)
        
    def seed_all(self, db: Session = None):
        """
        Seed all data: games, predictions, events
        """
        if db is None:
            db = SessionLocal()
        
        try:
            logger.info("🌱 Starting database seeding process")
            
            # Seed games first
            games = self.seed_games(db)
            logger.info(f"✅ Seeded {len(games)} games")
            
            # Seed predictions for each game
            total_predictions = 0
            for game in games:
                predictions = self.seed_predictions(db, game.id)
                total_predictions += len(predictions)
            logger.info(f"✅ Seeded {total_predictions} predictions")
            
            # Seed game events
            total_events = 0
            for game in games:
                events = self.seed_game_events(db, game.id)
                total_events += len(events)
            logger.info(f"✅ Seeded {total_events} game events")
            
            db.commit()
            logger.info("🎉 Database seeding completed successfully!")
            
            return {
                "games": len(games),
                "predictions": total_predictions,
                "events": total_events
            }
            
        except Exception as e:
            logger.error(f"❌ Error during seeding: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def seed_games(self, db: Session) -> List[Game]:
        """
        Create sample games for demo purposes
        """
        logger.info("Seeding games...")
        
        games = []
        
        # Get Eagles (we have full data for them)
        eagles = self.pulse_client.find_team_by_name("Eagles")
        if not eagles:
            logger.error("Could not find Eagles team for seeding")
            return []
        
        # Create sample games
        game_scenarios = [
            {
                "id": "sim_game_001",
                "home_team_id": eagles['id'],
                "away_team_id": "generic_team_001",
                "status": "in_progress",
                "quarter": 2,
                "time_remaining": "8:45",
                "home_score": 14,
                "away_score": 10
            },
            {
                "id": "sim_game_002", 
                "home_team_id": "generic_team_002",
                "away_team_id": eagles['id'],
                "status": "scheduled",
                "quarter": 1,
                "time_remaining": "15:00",
                "home_score": 0,
                "away_score": 0
            },
            {
                "id": "sim_game_003",
                "home_team_id": eagles['id'],
                "away_team_id": "generic_team_003", 
                "status": "completed",
                "quarter": 4,
                "time_remaining": "0:00",
                "home_score": 28,
                "away_score": 21
            }
        ]
        
        for game_data in game_scenarios:
            # Check if game already exists
            existing = db.query(Game).filter(Game.id == game_data["id"]).first()
            if existing:
                logger.info(f"Game {game_data['id']} already exists, skipping")
                games.append(existing)
                continue
            
            game = Game(
                id=game_data["id"],
                home_team_id=game_data["home_team_id"],
                away_team_id=game_data["away_team_id"],
                status=game_data["status"],
                quarter=game_data["quarter"],
                time_remaining=game_data["time_remaining"],
                home_score=game_data["home_score"],
                away_score=game_data["away_score"]
            )
            
            db.add(game)
            games.append(game)
            logger.info(f"Created game: {game.id}")
        
        return games
    
    def seed_predictions(self, db: Session, game_id: str) -> List[Prediction]:
        """
        Generate and store ML predictions for a game
        """
        logger.info(f"Seeding predictions for game {game_id}")
        
        predictions = []
        
        # Get Eagles players
        eagles = self.pulse_client.find_team_by_name("Eagles")
        if not eagles:
            return predictions
        
        players = self.pulse_client.get_team_players(eagles['id'])
        if not players:
            return predictions
        
        # Generate predictions for top players
        for player in players[:10]:  # Top 10 players
            try:
                # Generate ML prediction
                player_prediction = self.prediction_engine.predict_player_performance(
                    player, eagles['id']
                )
                
                # Create database records for each stat prediction
                for stat_type, stat_data in player_prediction['predictions'].items():
                    # Check if prediction already exists
                    existing = db.query(Prediction).filter(
                        Prediction.game_id == game_id,
                        Prediction.player_id == player['id'],
                        Prediction.stat_type == stat_type
                    ).first()
                    
                    if existing:
                        continue
                    
                    prediction = Prediction(
                        game_id=game_id,
                        player_id=player['id'],
                        stat_type=stat_type,
                        predicted_value=stat_data['predicted_value'],
                        confidence=stat_data['confidence'],
                        probability_over=stat_data.get('probability_over'),
                        explanation=json.dumps({
                            "player_name": player_prediction['player_name'],
                            "position": player_prediction['position'],
                            "factors": "ML-generated explanation"
                        })
                    )
                    
                    db.add(prediction)
                    predictions.append(prediction)
                    
            except Exception as e:
                logger.error(f"Error generating prediction for player {player.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Generated {len(predictions)} predictions for game {game_id}")
        return predictions
    
    def seed_game_events(self, db: Session, game_id: str) -> List[GameEvent]:
        """
        Create sample game events for live simulation
        """
        logger.info(f"Seeding game events for {game_id}")
        
        events = []
        
        # Get Eagles players for events
        eagles = self.pulse_client.find_team_by_name("Eagles")
        if not eagles:
            return events
        
        players = self.pulse_client.get_team_players(eagles['id'])
        if not players:
            return events
        
        # Event types with realistic probabilities
        event_types = [
            ("pass_completion", 0.25),
            ("rush_attempt", 0.20),
            ("touchdown", 0.08),
            ("field_goal", 0.05),
            ("interception", 0.03),
            ("fumble", 0.02),
            ("sack", 0.04),
            ("timeout", 0.15),
            ("penalty", 0.18)
        ]
        
        # Generate events for each quarter
        for quarter in range(1, 5):
            num_events = random.randint(8, 15)  # 8-15 events per quarter
            
            for i in range(num_events):
                # Select event type based on probabilities
                event_type = random.choices(
                    [et[0] for et in event_types],
                    weights=[et[1] for et in event_types]
                )[0]
                
                # Select random player
                player = random.choice(players)
                
                # Generate description
                descriptions = {
                    "pass_completion": f"{player.get('first_name', '')} {player.get('last_name', '')} completes pass for {random.randint(5, 25)} yards",
                    "rush_attempt": f"{player.get('first_name', '')} {player.get('last_name', '')} rushes for {random.randint(1, 15)} yards",
                    "touchdown": f"TOUCHDOWN! {player.get('first_name', '')} {player.get('last_name', '')} scores!",
                    "field_goal": f"Field goal good from {random.randint(25, 50)} yards",
                    "interception": "Pass intercepted by defense",
                    "fumble": f"{player.get('first_name', '')} {player.get('last_name', '')} fumbles",
                    "sack": f"Quarterback sacked for {random.randint(3, 12)} yard loss",
                    "timeout": "Timeout called",
                    "penalty": f"Penalty: {random.choice(['Holding', 'False Start', 'Pass Interference'])}"
                }
                
                description = descriptions.get(event_type, f"Game event: {event_type}")
                
                # Create event
                event = GameEvent(
                    game_id=game_id,
                    event_type=event_type,
                    player_id=player['id'],
                    description=description,
                    quarter=quarter,
                    timestamp=datetime.utcnow() - timedelta(minutes=random.randint(0, 60))
                )
                
                db.add(event)
                events.append(event)
        
        logger.info(f"Generated {len(events)} events for game {game_id}")
        return events
    
    def clear_all_data(self, db: Session = None):
        """
        Clear all seeded data (useful for reset)
        """
        if db is None:
            db = SessionLocal()
        
        try:
            logger.info("🗑️  Clearing all seeded data")
            
            # Delete in reverse order due to foreign keys
            db.query(GameEvent).delete()
            db.query(Prediction).delete() 
            db.query(Game).delete()
            
            db.commit()
            logger.info("✅ All seeded data cleared")
            
        except Exception as e:
            logger.error(f"❌ Error clearing data: {e}")
            db.rollback()
            raise
        finally:
            db.close()

# Utility functions for easy seeding

def seed_database():
    """
    Main function to seed the database
    Call this to populate with demo data
    """
    # Initialize database first
    if not init_db():
        logger.error("Failed to initialize database")
        return False
    
    seeder = DatabaseSeeder()
    try:
        result = seeder.seed_all()
        logger.info(f"Seeding completed: {result}")
        return True
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        return False

def clear_and_reseed():
    """
    Clear existing data and reseed fresh
    """
    seeder = DatabaseSeeder()
    
    # Clear existing data
    seeder.clear_all_data()
    
    # Seed fresh data
    return seed_database()

def quick_seed_for_demo():
    """
    Quick seeding function for demo/development
    Creates minimal data needed for the demo
    """
    logger.info("🚀 Quick seeding for demo")
    
    db = SessionLocal()
    seeder = DatabaseSeeder()
    
    try:
        # Just create one active game with predictions
        games = seeder.seed_games(db)
        if games:
            game = games[0]  # Use first game
            predictions = seeder.seed_predictions(db, game.id)
            events = seeder.seed_game_events(db, game.id)
            
            db.commit()
            
            logger.info(f"Demo seeding complete: 1 game, {len(predictions)} predictions, {len(events)} events")
            return True
    except Exception as e:
        logger.error(f"Demo seeding failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

# Command-line interface for seeding
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python seed.py [seed|clear|demo]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "seed":
        if seed_database():
            print("✅ Database seeded successfully!")
        else:
            print("❌ Database seeding failed!")
            sys.exit(1)
    
    elif command == "clear":
        seeder = DatabaseSeeder()
        seeder.clear_all_data()
        print("✅ Database cleared!")
    
    elif command == "demo":
        if quick_seed_for_demo():
            print("✅ Demo data seeded successfully!")
        else:
            print("❌ Demo seeding failed!")
            sys.exit(1)
    
    else:
        print("Unknown command. Use: seed, clear, or demo")
        sys.exit(1)
