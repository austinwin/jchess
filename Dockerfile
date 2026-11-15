FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update -qq && apt-get install -y --no-install-recommends stockfish && rm -rf /var/lib/apt/lists/*
ENV STOCKFISH_PATH=/usr/games/stockfish
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py db.py content.py lessons.py bot.py game_routes.py adaptive.py ./
RUN python -c "import main, lessons, bot, game_routes, adaptive; assert len(lessons.LESSONS) >= 14; assert adaptive.engine_path()"
COPY scripts ./scripts
COPY frontend/package.json frontend/package.json
COPY --from=frontend /app/frontend/dist ./frontend/dist
EXPOSE 10000
CMD ["python", "main.py", "--prod"]
