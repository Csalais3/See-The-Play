# Add this at the top of _initialize_game method (around line 45)

# ALWAYS use sample Eagles players (don't rely on Pulse Mock)
eagles_players = [
    {'id': 'jh1', 'first_name': 'Jalen', 'last_name': 'Hurts', 'position': 'QB'},
    {'id': 'ajb1', 'first_name': 'A.J.', 'last_name': 'Brown', 'position': 'WR'},
    {'id': 'ds1', 'first_name': 'DeVonta', 'last_name': 'Smith', 'position': 'WR'},
    {'id': 'dg1', 'first_name': 'Dallas', 'last_name': 'Goedert', 'position': 'TE'},
    {'id': 'kg1', 'first_name': 'Kenneth', 'last_name': 'Gainwell', 'position': 'RB'},
]

eagles = {'id': 'PHI', 'name': 'Eagles', 'market': 'Philadelphia'}
