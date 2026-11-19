# Sistema de Gestión de Formatos AT · CAR Cusco — imagen para Cloud Run
FROM node:20-slim

ENV NEXT_TELEMETRY_DISABLED=1

# LibreOffice (conversión XLSX → PDF preservando la plantilla oficial) y fuentes métricas
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       libreoffice-calc \
       fonts-crosextra-carlito \
       fonts-liberation \
       ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json* ./
RUN (npm ci --include=dev || npm install --include=dev)

COPY . .
RUN npm run build

ENV NODE_ENV=production \
    DATA_BACKEND=firestore \
    FIREBASE_PROJECT_ID=car-cusco \
    PORT=8080 \
    HOSTNAME=0.0.0.0

EXPOSE 8080
CMD ["node", ".next/standalone/server.js"]
