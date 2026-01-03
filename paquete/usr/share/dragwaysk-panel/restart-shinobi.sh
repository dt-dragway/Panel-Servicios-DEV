#!/bin/bash
# Script para reiniciar Shinobi usando PM2
# Autor: Dragwaysk
# Fecha: 2026-01-02

echo "🔄 Reiniciando Shinobi CCTV..."

# Verificar si PM2 está instalado
if ! command -v pm2 &> /dev/null; then
    echo "❌ Error: PM2 no está instalado"
    exit 1
fi

# Verificar si Shinobi está corriendo
if ! pm2 list | grep -q "shinobi"; then
    echo "⚠️  Shinobi no está en ejecución. Iniciando..."
    ./start-shinobi.sh
    exit $?
fi

# Reiniciar Shinobi
pm2 restart shinobi

# Guardar la configuración
pm2 save

echo "✅ Shinobi reiniciado correctamente"
pm2 list
