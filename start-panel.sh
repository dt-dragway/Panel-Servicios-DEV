#!/bin/bash
# Script para iniciar el Panel de Control Dragwaysk
# Autor: Dragwaysk
# Fecha: 2026-01-02

echo "🚀 Iniciando Dragwaysk Control Center..."

# Ruta del script
PANEL_PATH="/mnt/anexo1/Disco M/Desarrollos/panel_serv_DEV"
PANEL_SCRIPT="dragwaysk-panel.py"

# Verificar si Python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado"
    exit 1
fi

# Verificar si el script existe
if [ ! -f "$PANEL_PATH/$PANEL_SCRIPT" ]; then
    echo "❌ Error: No se encuentra el script en $PANEL_PATH/$PANEL_SCRIPT"
    exit 1
fi

# Cambiar al directorio del panel
cd "$PANEL_PATH" || exit 1

# Iniciar el panel
python3 "$PANEL_SCRIPT"
