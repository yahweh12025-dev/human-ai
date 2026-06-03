#!/bin/bash
# Health check script for Hermes Mission Control instances

echo "=== HERMES MISSION CONTROL HEALTH CHECK ==="
echo ""

# Check original mission control (port 4000)
echo "Checking Original Mission Control (port 4000):"
ORIGINAL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/api/health 2>/dev/null || echo "000")
if [[ "$ORIGINAL_STATUS" == "200" ]]; then
    echo "  ✓ Original Mission Control: HEALTHY (HTTP 200)"
else
    echo "  ✗ Original Mission Control: UNHEALTHY (HTTP $ORIGINAL_STATUS)"
fi

# Check Hermes mission control (port 5000)
echo ""
echo "Checking Hermes Mission Control (port 5000):"
HERMES_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/health 2>/dev/null || echo "000")
if [[ "$HERMES_STATUS" == "200" ]]; then
    echo "  ✓ Hermes Mission Control: HEALTHY (HTTP 200)"
else
    echo "  ✗ Hermes Mission Control: UNHEALTHY (HTTP $HERMES_STATUS)"
fi

# Check if both are running on different ports
echo ""
echo "=== PORT CONFLICT CHECK ==="
PORT_4000=$(netstat -tlnp 2>/dev/null | grep :4000 | grep -v grep | wc -l)
PORT_5000=$(netstat -tlnp 2>/dev/null | grep :5000 | grep -v grep | wc -l)

echo "Port 4000 usage: $PORT_4000 process(es)"
echo "Port 5000 usage: $PORT_5000 process(es)"

if [[ "$PORT_4000" -gt 0 && "$PORT_5000" -gt 0 ]]; then
    echo "  ✓ Both ports are in use - instances are separated"
else
    echo "  ⚠ Warning: Port separation may not be complete"
fi

echo ""
echo "=== SUMMARY ==="
if [[ "$ORIGINAL_STATUS" == "200" && "$HERMES_STATUS" == "200" ]]; then
    echo "🎉 Both mission control instances are running and healthy!"
    echo "   Original: http://localhost:4000"
    echo "   Hermes:   http://localhost:5000"
else
    echo "⚠ One or more instances need attention:"
    echo "   Original Mission Control (port 4000): $([[ "$ORIGINAL_STATUS" == "200" ]] && echo "HEALTHY" || echo "UNHEALTHY")"
    echo "   Hermes Mission Control (port 5000):   $([[ "$HERMES_STATUS" == "200" ]] && echo "HEALTHY" || echo "UNHEALTHY")"
fi