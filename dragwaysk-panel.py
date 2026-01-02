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
    """Valida y obtiene información de servicios systemd y PM2"""
    
    @staticmethod
    def service_exists(service_name):
        """Verifica si un servicio existe en systemd o PM2"""
        # Caso especial para Shinobi (usa PM2)
        if service_name == "shinobi":
            try:
                result = subprocess.run(
                    ["pm2", "list"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return "shinobi" in result.stdout
            except Exception as e:
                logging.error(f"Error verificando PM2 para {service_name}: {e}")
                return False
        
        # Para otros servicios, usar systemd
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
        # Caso especial para Shinobi (usa PM2)
        if service_name == "shinobi":
            try:
                result = subprocess.run(
                    ["pm2", "jlist"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                import json
                processes = json.loads(result.stdout)
                for proc in processes:
                    if proc.get("name") == "shinobi":
                        pm2_status = proc.get("pm2_env", {}).get("status")
                        if pm2_status == "online":
                            return "active"
                        elif pm2_status == "stopped":
                            return "inactive"
                        else:
                            return "failed"
                return "inactive"
            except Exception as e:
                logging.error(f"Error obteniendo estado PM2 de {service_name}: {e}")
                return "error"
        
        # Para otros servicios, usar systemd
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
        
        # Contenedor principal con estilo de tarjeta
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.get_style_context().add_class("service-card")
        
        # Contenedor horizontal interno
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(20)
        box.set_margin_end(20)
        
        # 1. Icono del servicio con contenedor circular
        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        icon_box.set_size_request(48, 48)
        icon_box.get_style_context().add_class("icon-container")
        
        self.service_icon = Gtk.Image.new_from_icon_name(
            service_data["icon"], 
            Gtk.IconSize.LARGE_TOOLBAR
        )
        icon_box.pack_start(self.service_icon, True, True, 0)
        box.pack_start(icon_box, False, False, 0)
        
        # 2. Contenedor de etiqueta y estado
        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        self.label = Gtk.Label(label=service_data["label"], xalign=0)
        self.label.set_markup(f"<span size='large' weight='bold'>{service_data['label']}</span>")
        label_box.pack_start(self.label, False, False, 0)
        
        # Etiqueta de estado
        self.status_label = Gtk.Label(xalign=0)
        self.status_label.set_markup("<span size='small' alpha='70%'>Verificando...</span>")
        label_box.pack_start(self.status_label, False, False, 0)
        
        box.pack_start(label_box, True, True, 0)
        
        # 3. Spinner de carga
        self.spinner = Gtk.Spinner()
        box.pack_end(self.spinner, False, False, 10)
        
        # 4. El Switch moderno
        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_switch_activated)
        box.pack_end(self.switch, False, False, 0)
        
        main_box.pack_start(box, True, True, 0)
        self.add(main_box)
        
        # Configurar tooltip y estado inicial
        if not self.service_exists:
            self.set_sensitive(False)
            self.set_tooltip_text(f"⚠️ El servicio '{self.service_name}' no está instalado en el sistema")
            self.status_label.set_markup("<span size='small' foreground='#ef5350'>● No disponible</span>")
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
            self.status_label.set_markup("<span size='small' foreground='#66bb6a'>● Activo</span>")
        elif status == "inactive":
            self.status_label.set_markup("<span size='small' alpha='50%'>○ Inactivo</span>")
        elif status == "failed":
            self.status_label.set_markup("<span size='small' foreground='#ef5350'>✗ Fallido</span>")
        else:
            self.status_label.set_markup("<span size='small' foreground='#ffa726'>? Desconocido</span>")

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
        # Caso especial para Shinobi (usa PM2)
        if self.service_name == "shinobi":
            cmd = ["pm2", action, self.service_name]
        else:
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
        self.set_border_width(0)
        self.set_default_size(500, 650)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        
        # Activar modo oscuro
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)
        
        # Aplicar CSS personalizado
        self.apply_custom_css()
        
        # Layout Principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)
        
        # Header moderno
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header_box.get_style_context().add_class("header-box")
        header_box.set_margin_top(20)
        header_box.set_margin_bottom(20)
        header_box.set_margin_start(25)
        header_box.set_margin_end(25)
        
        header = Gtk.Label()
        header.set_markup("<span size='xx-large' weight='bold'>Control Center</span>")
        header.set_xalign(0)
        header_box.pack_start(header, False, False, 0)
        
        subtitle = Gtk.Label()
        subtitle.set_markup("<span size='small' alpha='60%'>Gestión de Servicios de Desarrollo</span>")
        subtitle.set_xalign(0)
        subtitle.set_margin_top(5)
        header_box.pack_start(subtitle, False, False, 0)
        
        vbox.pack_start(header_box, False, False, 0)
        
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
        scrolled.set_margin_start(15)
        scrolled.set_margin_end(15)
        vbox.pack_start(scrolled, True, True, 0)

        # Lista de Servicios
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.get_style_context().add_class("services-list")
        scrolled.add(self.listbox)
        
        # Almacenar referencias a las filas
        self.service_rows = []

        # Crear filas dinámicamente
        for service in SERVICES_CONFIG:
            row = ServiceRow(service, self)
            self.service_rows.append(row)
            self.listbox.add(row)

        # Contenedor de botones
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_margin_top(15)
        button_box.set_margin_bottom(20)
        button_box.set_margin_start(20)
        button_box.set_margin_end(20)
        
        # Botón Refrescar
        btn_refresh = Gtk.Button(label="Refrescar")
        btn_refresh.get_style_context().add_class("flat")
        btn_refresh.connect("clicked", self.refresh_all)
        button_box.pack_start(btn_refresh, True, True, 0)
        
        # Botón Detener Todo
        btn_stop_all = Gtk.Button(label="Detener Todo")
        btn_stop_all.get_style_context().add_class("destructive-action")
        btn_stop_all.connect("clicked", self.stop_all)
        button_box.pack_start(btn_stop_all, True, True, 0)
        
        # Botón Activar Todo
        btn_dev = Gtk.Button(label="Activar Todo")
        btn_dev.get_style_context().add_class("suggested-action")
        btn_dev.connect("clicked", self.activate_all)
        button_box.pack_start(btn_dev, True, True, 0)
        
        vbox.pack_end(button_box, False, False, 0)
        
        # Actualización automática cada 5 segundos
        GLib.timeout_add_seconds(5, self.auto_refresh)
        
        logging.info("Panel de control iniciado")

    def apply_custom_css(self):
        """Aplica estilos CSS personalizados para modo oscuro"""
        css_provider = Gtk.CssProvider()
        css = b"""
        /* Fondo principal */
        window {
            background-color: #1e1e1e;
        }
        
        /* Header */
        .header-box {
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        }
        
        /* Lista de servicios */
        .services-list {
            background-color: transparent;
        }
        
        .services-list row {
            background-color: transparent;
            border: none;
        }
        
        /* Tarjetas de servicio */
        .service-card {
            background: linear-gradient(135deg, #2d2d2d 0%, #323232 100%);
            border-radius: 12px;
            margin: 6px 0;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 200ms ease;
        }
        
        .service-card:hover {
            background: linear-gradient(135deg, #323232 0%, #383838 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Contenedor de icono */
        .icon-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 8px;
        }
        
        /* Textos */
        label {
            color: #e8e8e8;
        }
        
        /* Botones */
        button {
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
            min-height: 40px;
            transition: all 200ms ease;
        }
        
        button.flat {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #e8e8e8;
        }
        
        button.flat:hover {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        
        button.suggested-action {
            background: linear-gradient(135deg, #66bb6a 0%, #4caf50 100%);
            border: none;
            color: white;
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
        }
        
        button.suggested-action:hover {
            background: linear-gradient(135deg, #5cb860 0%, #43a047 100%);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
        }
        
        button.destructive-action {
            background: linear-gradient(135deg, #ef5350 0%, #e53935 100%);
            border: none;
            color: white;
            box-shadow: 0 2px 8px rgba(239, 83, 80, 0.3);
        }
        
        button.destructive-action:hover {
            background: linear-gradient(135deg, #e64a4a 0%, #d32f2f 100%);
            box-shadow: 0 4px 12px rgba(239, 83, 80, 0.4);
        }
        
        /* Switch moderno */
        switch {
            border-radius: 14px;
        }
        
        switch slider {
            border-radius: 12px;
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
                # Separar servicios systemd de PM2
                systemd_services = [s for s in available_services if s != "shinobi"]
                pm2_services = [s for s in available_services if s == "shinobi"]
                
                # Iniciar servicios systemd
                if systemd_services:
                    subprocess.run(
                        ["pkexec", "systemctl", "start"] + systemd_services,
                        timeout=60
                    )
                
                # Iniciar servicios PM2 (Shinobi)
                if pm2_services:
                    for service in pm2_services:
                        subprocess.run(
                            ["pm2", "start", service],
                            timeout=30
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
                # Separar servicios systemd de PM2
                systemd_services = [s for s in available_services if s != "shinobi"]
                pm2_services = [s for s in available_services if s == "shinobi"]
                
                # Detener servicios systemd
                if systemd_services:
                    subprocess.run(
                        ["pkexec", "systemctl", "stop"] + systemd_services,
                        timeout=60
                    )
                
                # Detener servicios PM2 (Shinobi)
                if pm2_services:
                    for service in pm2_services:
                        subprocess.run(
                            ["pm2", "stop", service],
                            timeout=30
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