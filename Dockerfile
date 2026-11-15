FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py db.py content.py ./
COPY scripts ./scripts
COPY frontend/package.json frontend/package.json
COPY --from=frontend /app/frontend/dist ./frontend/dist
EXPOSE 10000
CMD ["python", "main.py", "--prod"]
