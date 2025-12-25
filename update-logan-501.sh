#!/usr/bin/env bash
set -e

APP_DIR="$HOME/logan-501"

echo "➡️  Updating Logan 501"

if [ ! -d "$APP_DIR" ]; then
  echo "❌ Directory not found: $APP_DIR"
  exit 1
fi

cd "$APP_DIR"
echo "📁 Working directory: $(pwd)"

if [ ! -f docker-compose.yml ]; then
  echo "❌ docker-compose.yml not found in $(pwd)"
  exit 1
fi

echo "🛑 Stopping containers"
docker compose down

echo "⬇️  Pulling latest changes"
git pull --ff-only

echo "🔨 Building image"
docker compose build

echo "🚀 Starting containers"
docker compose up -d

echo "✅ Update complete"
