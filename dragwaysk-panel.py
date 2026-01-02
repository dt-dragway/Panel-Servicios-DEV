#!/usr/bin/env python3
import gi
import subprocess
import threading
import logging
from datetime import datetime

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

# Configurar logging
logging.basicConfig(
    filename='/tmp/dragwaysk-panel.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- CONFIGURACIÓN: AGREGA AQUÍ TUS SERVICIOS ---
SERVICES_CONFIG = [
    {"label": "PostgreSQL", "service": "postgresql", "icon": "server-database"},
    {"label": "MariaDB", "service": "mariadb", "icon": "drive-harddisk"},
    {"label": "Docker Engine", "service": "docker", "icon": "system-run"},
    {"label": "Shinobi CCTV", "service": "shinobi", "icon": "camera-video"},
]

class ServiceValidator:
    """Valida y obtiene información de servicios systemd"""
    
    @staticmethod
    def service_exists(service_name):
        """Verifica si un servicio existe en systemd"""
        try:
            result = subprocess.run(
                ["systemctl", "list-unit-files", service_name + ".service"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return service_name in result.stdout
        except Exception as e:
            logging.error(f"Error verificando existencia de {service_name}: {e}")
            return False
    
    @staticmethod
    def get_service_status(service_name):
        """Obtiene el estado detallado de un servicio"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            status = result.stdout.strip()
            return status if status in ["active", "inactive", "failed"] else "unknown"
        except Exception as e:
            logging.error(f"Error obteniendo estado de {service_name}: {e}")
            return "error"

class ServiceRow(Gtk.ListBoxRow):
    def __init__(self, service_data, parent_window):
        super().__init__()
        self.service_name = service_data["service"]
        self.service_label = service_data["label"]
        self.parent_window = parent_window
        self.is_operating = False
        
        # Verificar si el servicio existe
        self.service_exists = ServiceValidator.service_exists(self.service_name)
        
        # Contenedor horizontal
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_border_width(10)
        
        # 1. Icono del servicio
        self.service_icon = Gtk.Image.new_from_icon_name(
            service_data["icon"], 
            Gtk.IconSize.DIALOG
        )
        box.pack_start(self.service_icon, False, False, 0)
        
        # 2. Contenedor de etiqueta y estado
        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        self.label = Gtk.Label(label=service_data["label"], xalign=0)
        self.label.set_markup(f"<b>{service_data['label']}</b>")
        label_box.pack_start(self.label, False, False, 0)
        
        # Etiqueta de estado
        self.status_label = Gtk.Label(xalign=0)
        self.status_label.set_markup("<small>Verificando...</small>")
        label_box.pack_start(self.status_label, False, False, 0)
        
        box.pack_start(label_box, True, True, 0)
        
        # 3. Spinner de carga
        self.spinner = Gtk.Spinner()
        box.pack_end(self.spinner, False, False, 5)
        
        # 4. El Switch
        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_switch_activated)
        box.pack_end(self.switch, False, False, 0)
        
        # 5. Indicador de estado (LED)
        self.status_indicator = Gtk.Image.new_from_icon_name(
            "dialog-question",
            Gtk.IconSize.BUTTON
        )
        box.pack_end(self.status_indicator, False, False, 5)
        
        self.add(box)
        
        # Configurar tooltip y estado inicial
        if not self.service_exists:
            self.set_sensitive(False)
            self.set_tooltip_text(f"⚠️ El servicio '{self.service_name}' no está instalado en el sistema")
            self.status_label.set_markup("<small><span foreground='red'>No disponible</span></small>")
            self.status_indicator.set_from_icon_name("dialog-error", Gtk.IconSize.BUTTON)
            logging.warning(f"Servicio no encontrado: {self.service_name}")
        else:
            self.check_status()

    def check_status(self):
        """Verifica el estado actual del servicio"""
        if not self.service_exists:
            return
            
        status = ServiceValidator.get_service_status(self.service_name)
        is_active = status == "active"
        
        # Actualizar switch sin disparar eventos
        self.switch.handler_block_by_func(self.on_switch_activated)
        self.switch.set_active(is_active)
        self.switch.handler_unblock_by_func(self.on_switch_activated)
        
        # Actualizar indicadores visuales
        self.update_visual_status(status)
        
        # Actualizar tooltip
        self.set_tooltip_text(f"{self.service_label}\nEstado: {status}")

    def update_visual_status(self, status):
        """Actualiza los indicadores visuales según el estado"""
        if status == "active":
            self.status_label.set_markup("<small><span foreground='#4CAF50'>● Activo</span></small>")
            self.status_indicator.set_from_icon_name("emblem-default", Gtk.IconSize.BUTTON)
        elif status == "inactive":
            self.status_label.set_markup("<small><span foreground='#757575'>○ Inactivo</span></small>")
            self.status_indicator.set_from_icon_name("process-stop", Gtk.IconSize.BUTTON)
        elif status == "failed":
            self.status_label.set_markup("<small><span foreground='#F44336'>✗ Fallido</span></small>")
            self.status_indicator.set_from_icon_name("dialog-error", Gtk.IconSize.BUTTON)
        else:
            self.status_label.set_markup("<small><span foreground='#FF9800'>? Desconocido</span></small>")
            self.status_indicator.set_from_icon_name("dialog-question", Gtk.IconSize.BUTTON)

    def on_switch_activated(self, switch, state):
        """Maneja el cambio de estado del switch"""
        if self.is_operating:
            return True  # Prevenir múltiples operaciones simultáneas
        
        action = "start" if state else "stop"
        logging.info(f"Usuario solicitó {action} para {self.service_name}")
        
        # Iniciar operación en hilo separado
        self.is_operating = True
        self.spinner.start()
        self.switch.set_sensitive(False)
        
        thread = threading.Thread(
            target=self._perform_service_operation,
            args=(action, state)
        )
        thread.daemon = True
        thread.start()
        
        return True  # Prevenir cambio visual inmediato

    def _perform_service_operation(self, action, desired_state):
        """Ejecuta la operación del servicio en un hilo separado"""
        cmd = ["pkexec", "systemctl", action, self.service_name]
        success = False
        error_msg = None
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Verificar que el servicio realmente cambió de estado
                GLib.timeout_add(1000, self._verify_operation, action)
                success = True
                logging.info(f"Operación {action} exitosa para {self.service_name}")
            else:
                error_msg = result.stderr or "Operación cancelada por el usuario"
                logging.error(f"Error en {action} de {self.service_name}: {error_msg}")
                
        except subprocess.TimeoutExpired:
            error_msg = "La operación tardó demasiado tiempo"
            logging.error(f"Timeout en {action} de {self.service_name}")
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Excepción en {action} de {self.service_name}: {e}")
        
        # Actualizar UI en el hilo principal
        GLib.idle_add(self._operation_completed, success, action, error_msg)

    def _verify_operation(self, action):
        """Verifica que la operación se completó correctamente"""
        self.check_status()
        return False  # No repetir

    def _operation_completed(self, success, action, error_msg):
        """Callback ejecutado en el hilo principal al completar la operación"""
        self.spinner.stop()
        self.switch.set_sensitive(True)
        self.is_operating = False
        
        if success:
            self.parent_window.show_notification(
                f"✓ Servicio {self.service_label} {action == 'start' and 'iniciado' or 'detenido'} correctamente",
                Gtk.MessageType.INFO
            )
            self.check_status()
        else:
            self.parent_window.show_notification(
                f"✗ Error al {action == 'start' and 'iniciar' or 'detener'} {self.service_label}: {error_msg}",
                Gtk.MessageType.ERROR
            )
            # Revertir el switch al estado real
            self.check_status()
        
        return False  # No repetir

class ControlPanelWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Dragwaysk Control Center")
        self.set_border_width(10)
        self.set_default_size(450, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Aplicar CSS personalizado
        self.apply_custom_css()
        
        # Layout Principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)
        
        # Título
        header = Gtk.Label()
        header.set_markup("<b><big>Gestor de Servicios Dev</big></b>")
        header.set_margin_bottom(10)
        vbox.pack_start(header, False, False, 0)
        
        # Barra de información (para notificaciones)
        self.info_bar = Gtk.InfoBar()
        self.info_bar.set_show_close_button(True)
        self.info_bar.connect("response", lambda w, r: w.set_revealed(False))
        self.info_label = Gtk.Label()
        self.info_bar.get_content_area().add(self.info_label)
        self.info_bar.set_revealed(False)
        vbox.pack_start(self.info_bar, False, False, 0)

        # ScrolledWindow para la lista de servicios
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)

        # Lista de Servicios
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.listbox)
        
        # Almacenar referencias a las filas
        self.service_rows = []

        # Crear filas dinámicamente
        for service in SERVICES_CONFIG:
            row = ServiceRow(service, self)
            self.service_rows.append(row)
            self.listbox.add(row)

        # Contenedor de botones
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        button_box.set_margin_top(10)
        
        # Botón Refrescar
        btn_refresh = Gtk.Button(label="🔄 Refrescar")
        btn_refresh.connect("clicked", self.refresh_all)
        button_box.pack_start(btn_refresh, True, True, 0)
        
        # Botón Detener Todo
        btn_stop_all = Gtk.Button(label="⏹️ Detener Todo")
        btn_stop_all.get_style_context().add_class("destructive-action")
        btn_stop_all.connect("clicked", self.stop_all)
        button_box.pack_start(btn_stop_all, True, True, 0)
        
        # Botón Activar Todo
        btn_dev = Gtk.Button(label="🚀 Activar Todo")
        btn_dev.get_style_context().add_class("suggested-action")
        btn_dev.connect("clicked", self.activate_all)
        button_box.pack_start(btn_dev, True, True, 0)
        
        vbox.pack_end(button_box, False, False, 0)
        
        # Barra de estado
        self.status_bar = Gtk.Label()
        self.status_bar.set_markup("<small>Listo</small>")
        self.status_bar.set_xalign(0)
        self.status_bar.set_margin_top(5)
        vbox.pack_end(self.status_bar, False, False, 0)
        
        # Actualización automática cada 5 segundos
        GLib.timeout_add_seconds(5, self.auto_refresh)
        
        logging.info("Panel de control iniciado")

    def apply_custom_css(self):
        """Aplica estilos CSS personalizados"""
        css_provider = Gtk.CssProvider()
        css = b"""
        .service-row {
            padding: 5px;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def show_notification(self, message, msg_type=Gtk.MessageType.INFO):
        """Muestra una notificación en la barra de información"""
        self.info_label.set_text(message)
        self.info_bar.set_message_type(msg_type)
        self.info_bar.set_revealed(True)
        
        # Actualizar barra de estado
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.set_markup(f"<small>{timestamp} - {message}</small>")
        
        # Auto-ocultar después de 5 segundos
        GLib.timeout_add_seconds(5, lambda: self.info_bar.set_revealed(False))
        
        logging.info(f"Notificación: {message}")

    def refresh_all(self, widget=None):
        """Refresca el estado de todos los servicios"""
        for row in self.service_rows:
            row.check_status()
        self.show_notification("Estados actualizados", Gtk.MessageType.INFO)
        return False

    def auto_refresh(self):
        """Actualización automática periódica"""
        for row in self.service_rows:
            if not row.is_operating:  # No actualizar si está en operación
                row.check_status()
        return True  # Continuar ejecutando

    def activate_all(self, widget):
        """Activa todos los servicios disponibles"""
        available_services = [
            s["service"] for s in SERVICES_CONFIG 
            if ServiceValidator.service_exists(s["service"])
        ]
        
        if not available_services:
            self.show_notification("No hay servicios disponibles para activar", Gtk.MessageType.WARNING)
            return
        
        self.show_notification(f"Activando {len(available_services)} servicios...", Gtk.MessageType.INFO)
        
        def run_activation():
            try:
                subprocess.run(
                    ["pkexec", "systemctl", "start"] + available_services,
                    timeout=60
                )
                GLib.idle_add(self.show_notification, "✓ Todos los servicios activados", Gtk.MessageType.INFO)
                GLib.idle_add(self.refresh_all)
            except Exception as e:
                GLib.idle_add(self.show_notification, f"Error activando servicios: {e}", Gtk.MessageType.ERROR)
        
        thread = threading.Thread(target=run_activation)
        thread.daemon = True
        thread.start()

    def stop_all(self, widget):
        """Detiene todos los servicios disponibles"""
        available_services = [
            s["service"] for s in SERVICES_CONFIG 
            if ServiceValidator.service_exists(s["service"])
        ]
        
        if not available_services:
            self.show_notification("No hay servicios disponibles para detener", Gtk.MessageType.WARNING)
            return
        
        # Diálogo de confirmación
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="¿Detener todos los servicios?"
        )
        dialog.format_secondary_text(
            f"Se detendrán {len(available_services)} servicios. ¿Continuar?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response != Gtk.ResponseType.YES:
            return
        
        self.show_notification(f"Deteniendo {len(available_services)} servicios...", Gtk.MessageType.INFO)
        
        def run_stop():
            try:
                subprocess.run(
                    ["pkexec", "systemctl", "stop"] + available_services,
                    timeout=60
                )
                GLib.idle_add(self.show_notification, "✓ Todos los servicios detenidos", Gtk.MessageType.INFO)
                GLib.idle_add(self.refresh_all)
            except Exception as e:
                GLib.idle_add(self.show_notification, f"Error deteniendo servicios: {e}", Gtk.MessageType.ERROR)
        
        thread = threading.Thread(target=run_stop)
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    win = ControlPanelWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()