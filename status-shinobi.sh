#!/bin/bash
# Script para ver el estado de Shinobi usando PM2
# Autor: Dragwaysk
# Fecha: 2026-01-02

echo "📊 Estado de Shinobi CCTV"
echo "=========================="

# Verificar si PM2 está instalado
if ! command -v pm2 &> /dev/null; then
    echo "❌ Error: PM2 no está instalado"
    exit 1
fi

# Mostrar estado de Shinobi
if pm2 list | grep -q "shinobi"; then
    echo ""
    pm2 show shinobi
    echo ""
    echo "📊 Logs recientes:"
    echo "=================="
    pm2 logs shinobi --lines 20 --nostream
else
    echo "⚠️  Shinobi no está en ejecución"
    echo ""
    echo "Para iniciar Shinobi, ejecuta: ./start-shinobi.sh"
fi
