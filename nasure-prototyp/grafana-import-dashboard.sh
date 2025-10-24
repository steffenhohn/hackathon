#!/bin/bash
# Import dashboard into Grafana via API

echo "Importing dashboard..."

# Read the dashboard JSON and wrap it properly
DASHBOARD_JSON=$(cat /etc/grafana/provisioning/dashboards/lab-metrics.json)

# Create the payload with proper wrapping
PAYLOAD=$(jq -n \
  --argjson dashboard "$DASHBOARD_JSON" \
  '{
    dashboard: $dashboard,
    overwrite: true,
    message: "Imported via provisioning script"
  }')

# Import via API
RESPONSE=$(curl -s -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q "success"; then
  echo "✓ Dashboard imported successfully"
  exit 0
else
  echo "✗ Dashboard import failed"
  exit 1
fi
