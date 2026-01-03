#!/bin/bash
# Script para iniciar Shinobi usando PM2
# Autor: Dragwaysk
# Fecha: 2026-01-02

echo "🚀 Iniciando Shinobi CCTV..."

# Verificar si PM2 está instalado
if ! command -v pm2 &> /dev/null; then
    echo "❌ Error: PM2 no está instalado"
    echo "Instálalo con: npm install -g pm2"
    exit 1
fi

# Verificar si Shinobi ya está corriendo (online)
if pm2 jlist 2>/dev/null | grep -q '"name":"shinobi".*"status":"online"'; then
    echo "⚠️  Shinobi ya está en ejecución"
    pm2 list | grep shinobi
    exit 0
fi

# Iniciar Shinobi con PM2
SHINOBI_PATH="/home/dragwaysk/Shinobi"

if [ ! -d "$SHINOBI_PATH" ]; then
    echo "❌ Error: No se encuentra Shinobi en $SHINOBI_PATH"
    echo "Por favor, ajusta la variable SHINOBI_PATH en este script"
    exit 1
fi

cd "$SHINOBI_PATH" || exit 1

# Iniciar con PM2 (restart funciona tanto si existe como si no)
pm2 restart shinobi 2>/dev/null || pm2 start camera.js --name shinobi

# Guardar la configuración de PM2
pm2 save

echo "✅ Shinobi iniciado correctamente"
echo "📊 Accede a Shinobi en: http://localhost:8080"
pm2 list
