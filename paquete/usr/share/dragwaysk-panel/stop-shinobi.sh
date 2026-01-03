#!/bin/bash
# Script para detener Shinobi usando PM2
# Autor: Dragwaysk
# Fecha: 2026-01-02

echo "🛑 Deteniendo Shinobi CCTV..."

# Verificar si PM2 está instalado
if ! command -v pm2 &> /dev/null; then
    echo "❌ Error: PM2 no está instalado"
    exit 1
fi

# Verificar si Shinobi está corriendo
if ! pm2 list | grep -q "shinobi"; then
    echo "⚠️  Shinobi no está en ejecución"
    exit 0
fi

# Detener Shinobi
pm2 stop shinobi

# Guardar la configuración
pm2 save

echo "✅ Shinobi detenido correctamente"
pm2 list
