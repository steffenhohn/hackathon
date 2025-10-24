#!/bin/bash
set -e

echo "Starting Grafana with delayed provisioning..."

# Start Grafana in background (without provisioning initially)
/usr/share/grafana/bin/grafana server \
  --homepath=/usr/share/grafana \
  --config=/etc/grafana/grafana.ini \
  cfg:default.paths.data=/var/lib/grafana \
  cfg:default.paths.logs=/var/log/grafana \
  cfg:default.paths.plugins=/var/lib/grafana/plugins &

GRAFANA_PID=$!

# Wait for Grafana to be ready
echo "Waiting for Grafana to start..."
MAX_RETRIES=60
RETRY_COUNT=0

until curl -s http://localhost:3000/api/health > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT+1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "✗ Grafana failed to start"
    exit 1
  fi
  echo "  Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

echo "✓ Grafana is ready!"

# Wait for Infinity plugin to be installed
echo "Waiting for Infinity plugin to be installed..."
sleep 10

# Check if plugin is installed
if [ -d "/var/lib/grafana/plugins/yesoreyeram-infinity-datasource" ]; then
  echo "✓ Infinity plugin is installed"

  # Now enable provisioning by copying config to the right location
  echo "Enabling provisioning..."
  mkdir -p /etc/grafana/provisioning/datasources
  mkdir -p /etc/grafana/provisioning/dashboards
  cp -r /etc/grafana/provisioning-ready/datasources/* /etc/grafana/provisioning/datasources/ 2>/dev/null || true
  cp -r /etc/grafana/provisioning-ready/dashboards/* /etc/grafana/provisioning/dashboards/ 2>/dev/null || true

  echo "✓ Provisioning files copied"

  # Import dashboard via API (more reliable than provisioning after startup)
  echo "Importing dashboard via API..."
  sleep 3

  # Use the import script
  /bin/bash /grafana-import-dashboard.sh
else
  echo "⚠ Infinity plugin not found, provisioning skipped"
fi

# Keep the container running
wait $GRAFANA_PID
