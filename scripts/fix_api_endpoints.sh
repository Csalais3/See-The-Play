#!/bin/bash
# fix_api_endpoints.sh - Fix the API endpoint URLs

echo "🔧 Fixing Pulse Mock API endpoints..."

# Backup
cp backend/utils/api_clients.py backend/utils/api_clients.py.backup2

# Fix the endpoints - remove /v1 prefix if needed
python3 << 'EOF'
with open('backend/utils/api_clients.py', 'r') as f:
    content = f.read()

# Replace all /v1/leagues with /leagues (or whatever Pulse Mock actually uses)
# We'll try both versions

# First, let's see what the actual endpoint format is
import subprocess
import json

# Check what endpoints pulse-mock actually provides
try:
    result = subprocess.run(['python3', '-c', '''
import pulse_mock
app = pulse_mock.create_app()
routes = [str(rule) for rule in app.url_map.iter_rules()]
print("\\n".join(routes))
'''], capture_output=True, text=True)
    
    routes = result.stdout.strip().split('\n')
    print("Available Pulse Mock routes:")
    for route in routes:
        print(f"  {route}")
    
    # Determine correct prefix
    if any('/v1/' in r for r in routes):
        print("\n✅ Using /v1/ prefix")
        # Already correct
    elif any('/leagues/' in r and '/v1/' not in r for r in routes):
        print("\n🔧 Removing /v1/ prefix")
        content = content.replace('/v1/leagues/', '/leagues/')
    else:
        print("\n⚠️  Non-standard routes, trying alternate format")
        # Try without any prefix
        content = content.replace('f"{self.base_url}/v1/leagues/{league}/teams"', 
                                 'f"{self.base_url}/leagues/{league}/teams"')
    
    with open('backend/utils/api_clients.py', 'w') as f:
        f.write(content)
    
    print("\n✅ Fixed api_clients.py endpoints")
    
except Exception as e:
    print(f"Error: {e}")
    print("\n💡 Manual fix needed - check Pulse Mock documentation")
EOF

echo ""
echo "✅ Endpoints fixed!"
echo ""
echo "🔄 Now restart everything:"
echo "   ./scripts/stop_services.sh"
echo "   ./scripts/quick_start.sh"