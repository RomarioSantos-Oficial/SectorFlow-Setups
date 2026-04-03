"""
app.py — Janela principal do LMU Virtual Engineer.

CustomTkinter com Dark Mode, sistema de abas moderno,
interface conversacional e barra de status.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from config import APP_NAME, APP_VERSION
from gui.tab_telemetry import TelemetryTab
from gui.tab_adjustment import AdjustmentTab
from gui.tab_setup import SetupTab
from gui.tab_database import DatabaseTab
from gui.widgets import StatusIndicator, WeatherIndicator, COLORS

logger = logging.getLogger("LMU_VE.gui")


class MainApp(ctk.CTk):
    """Janela principal do LMU Virtual Engineer."""

    def __init__(self, engine=None):
        super().__init__()

        self.engine = engine

        # ─── Configuração da janela ────────────────────────
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1200x800")
        self.minsize(1000, 650)

        # Ícone da janela (logo SectorFlow)
        self._logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        self._ico_path = Path(__file__).parent.parent / "assets" / "logo.ico"
        self._logo_images = {}  # cache de imagens PIL
        self._logo_tk = {}      # cache de ImageTk

        # Definir ícone .ico para Windows (taskbar + alt-tab + barra de título)
        if self._ico_path.exists():
            try:
                self.iconbitmap(str(self._ico_path))
            except Exception as e:
                logger.debug("Erro ao definir .ico: %s", e)

        # Fallback com iconphoto (PNG) se .ico falhar
        if self._logo_path.exists():
            try:
                from PIL import Image, ImageTk
                for size in (16, 32, 48, 128):
                    img = Image.open(self._logo_path)
                    img = img.resize((size, size), Image.LANCZOS)
                    self._logo_images[size] = img
                    self._logo_tk[size] = ImageTk.PhotoImage(img)
                self.iconphoto(
                    True,
                    self._logo_tk[48],
                    self._logo_tk[32],
                    self._logo_tk[16],
                )
            except ImportError:
                logger.debug("Pillow não disponível para ícone PNG.")
            except Exception as e:
                logger.debug("Erro ao definir ícone PNG: %s", e)

        # Dark mode
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ─── Layout principal ──────────────────────────────
        self._build_menu()
        self._build_header()
        self._build_tabs()
        self._build_footer()

        # ─── Estado ────────────────────────────────────────
        self._update_job = None
        self._running = True

        # Registrar callbacks de auto-suggest e alertas
        if self.engine:
            self.engine._on_auto_suggestion_callback = self._on_auto_suggestion
            self.engine._on_trend_alert_callback = self._on_trend_alert

        # System tray (bandeja do sistema)
        self._tray_icon = None
        self._setup_tray()

        # Iniciar atualização periódica
        self._schedule_update()

        # Fechar limpo
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────
    # Layout
    # ─────────────────────────────────────────────────────

    def _build_menu(self):
        """Menu simplificado — funções de setup agora estão na aba 🎯 Setup."""
        import tkinter as tk

        menubar = tk.Menu(self, tearoff=0)
        self.configure(menu=menubar)

        # ── Menu Arquivo ──
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(
            label="📤 Exportar Dados...",
            command=self._on_export,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self._on_close)

        # ── Menu Ajuda ──
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(
            label="ℹ️ Sobre",
            command=self._on_about,
        )

    # ─────────────────────────────────────────────────────

    def _build_header(self):
        """Cabeçalho moderno com nome, indicadores e clima."""
        header = ctk.CTkFrame(
            self, height=60, corner_radius=0,
            fg_color=COLORS["bg_card"],
            border_width=0,
        )
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        # Logo + título
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=15)

        # Inserir logo no header
        if self._logo_path.exists():
            try:
                from PIL import Image
                if 32 not in self._logo_images:
                    img = Image.open(self._logo_path)
                    img = img.resize((32, 32), Image.LANCZOS)
                    self._logo_images[32] = img
                header_img = ctk.CTkImage(
                    light_image=self._logo_images[32],
                    dark_image=self._logo_images[32],
                    size=(32, 32),
                )
                ctk.CTkLabel(
                    title_frame, image=header_img, text="",
                ).pack(side="left", padx=(0, 8))
                self._header_logo = header_img  # manter referência
            except Exception as e:
                logger.debug("Erro ao colocar logo no header: %s", e)

        ctk.CTkLabel(
            title_frame, text=APP_NAME,
            font=("Arial", 18, "bold"),
            text_color=COLORS["accent_cyan"],
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame, text=f"  v{APP_VERSION}",
            font=("Arial", 10),
            text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=(4, 0), anchor="s", pady=(0, 2))

        # Indicadores no canto direito
        indicators_frame = ctk.CTkFrame(header, fg_color="transparent")
        indicators_frame.pack(side="right", padx=15)

        self.ind_game = StatusIndicator(indicators_frame, label="LMU")
        self.ind_game.pack(side="left", padx=(0, 12))

        self.ind_ai = StatusIndicator(indicators_frame, label="IA")
        self.ind_ai.pack(side="left", padx=(0, 12))

        self.ind_db = StatusIndicator(indicators_frame, label="DB")
        self.ind_db.pack(side="left")

        # Clima centralizado
        self._weather = WeatherIndicator(header)
        self._weather.pack(side="right", padx=15)

    def _build_tabs(self):
        """Constrói o sistema de abas reorganizado."""
        self.tabview = ctk.CTkTabview(
            self, corner_radius=10,
            segmented_button_fg_color=COLORS["bg_card"],
            segmented_button_selected_color=COLORS["accent_blue"],
            segmented_button_selected_hover_color="#3588b8",
            segmented_button_unselected_color=COLORS["bg_card"],
            segmented_button_unselected_hover_color=COLORS["bg_card_hover"],
        )
        self.tabview.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        # Criar abas na nova ordem
        tab_setup = self.tabview.add("🎯 Setup")
        tab_tele = self.tabview.add("📊 Telemetria")
        tab_fb = self.tabview.add("🎮 Feedback")
        tab_db = self.tabview.add("🗄️ Dados")

        # Instanciar conteúdo
        self.tab_setup = SetupTab(tab_setup, engine=self.engine)
        self.tab_setup.pack(fill="both", expand=True)

        self.tab_telemetry = TelemetryTab(tab_tele, engine=self.engine)
        self.tab_telemetry.pack(fill="both", expand=True)

        self.tab_adjustment = AdjustmentTab(tab_fb, engine=self.engine)
        self.tab_adjustment.pack(fill="both", expand=True)

        self.tab_database = DatabaseTab(tab_db, engine=self.engine)
        self.tab_database.pack(fill="both", expand=True)

        # Definir aba inicial
        self.tabview.set("🎯 Setup")

    def _build_footer(self):
        """Barra de status moderna no rodapé."""
        footer = ctk.CTkFrame(
            self, height=34, corner_radius=0,
            fg_color=COLORS["bg_card"],
        )
        footer.pack(fill="x", padx=0, pady=0)
        footer.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            footer, text="Aguardando conexão com LMU...",
            font=("JetBrains Mono", 10), text_color=COLORS["text_secondary"],
        )
        self.status_label.pack(side="left", padx=12)

        self.car_label = ctk.CTkLabel(
            footer, text="",
            font=("JetBrains Mono", 10), text_color=COLORS["text_secondary"],
        )
        self.car_label.pack(side="right", padx=12)

        # Indicador do setup base
        self._base_label = ctk.CTkLabel(
            footer, text="Nenhum setup base",
            font=("JetBrains Mono", 10), text_color=COLORS["text_secondary"],
        )
        self._base_label.pack(side="right", padx=(0, 20))

    # ─────────────────────────────────────────────────────
    # Callbacks do tab_setup (integração)
    # ─────────────────────────────────────────────────────

    def _on_base_loaded(self, filepath: str):
        """Chamado pelo tab_setup quando um setup base é carregado."""
        name = Path(filepath).name
        self._base_label.configure(
            text=f"📄 Base: {name}",
            text_color=COLORS["accent_cyan"],
        )
        self.set_status(f"Setup base carregado: {name}", "#00cc44")

    def _on_base_cleared(self):
        """Chamado pelo tab_setup quando o base é limpo."""
        self._base_label.configure(
            text="Nenhum setup base",
            text_color=COLORS["text_secondary"],
        )
        self.set_status("Setup base removido.", "#aaaaaa")

    # ─────────────────────────────────────────────────────
    # Auto-suggest e alertas (callbacks do engine)
    # ─────────────────────────────────────────────────────

    def _on_auto_suggestion(self, suggestion: dict):
        """
        Chamado pelo engine quando uma auto-sugestão é gerada.
        Usa after() para garantir thread-safety com Tk.
        """
        self.after(0, self._handle_auto_suggestion, suggestion)

    def _handle_auto_suggestion(self, suggestion: dict):
        """Processa a auto-sugestão na thread do Tk."""
        if not hasattr(self, "tab_setup"):
            return

        # Mostrar no chat
        explanation = suggestion.get("explanation", "Sugestão automática gerada.")
        self.tab_setup.add_message(explanation, sender="ai")

        # Atualizar deltas no painel (usar display_deltas em formato delta-name)
        deltas = suggestion.get("display_deltas", suggestion.get("deltas", {}))
        warnings = suggestion.get("warnings", [])
        self.tab_setup.display_suggestions(deltas, warnings)

        # Notificação na barra de status
        lap = suggestion.get("lap", "?")
        source = suggestion.get("source", "IA")
        self.set_status(
            f"🤖 Auto-sugestão (volta {lap}, via {source})", "#00cc44"
        )

        # Mudar para aba Setup se não estiver nela
        current_tab = self.tabview.get()
        if "Setup" not in current_tab:
            self.tabview.set("🎯 Setup")

    def _on_trend_alert(self, alert_text: str):
        """
        Chamado pelo engine quando uma tendência/alerta é detectada.
        Usa after() para garantir thread-safety com Tk.
        """
        self.after(0, self._handle_trend_alert, alert_text)

    def _handle_trend_alert(self, alert_text: str):
        """Processa o alerta de tendência na thread do Tk."""
        if hasattr(self, "tab_setup"):
            self.tab_setup.add_message(alert_text, sender="system")

    # ─────────────────────────────────────────────────────
    # Menu callbacks
    # ─────────────────────────────────────────────────────

    def _on_export(self):
        """Exporta dados do banco."""
        if self.engine and hasattr(self.engine, "export_data"):
            try:
                path = self.engine.export_data()
                messagebox.showinfo("Exportação", f"Dados exportados em:\n{path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar:\n{e}")

    def _on_about(self):
        """Mostra janela Sobre com logo."""
        about_win = ctk.CTkToplevel(self)
        about_win.title(f"Sobre {APP_NAME}")
        about_win.geometry("380x340")
        about_win.resizable(False, False)
        about_win.transient(self)
        about_win.grab_set()

        # Ícone da janela About
        if self._ico_path.exists():
            try:
                about_win.after(200, lambda: about_win.iconbitmap(str(self._ico_path)))
            except Exception:
                pass

        # Logo grande
        if self._logo_path.exists():
            try:
                from PIL import Image
                if 128 not in self._logo_images:
                    img = Image.open(self._logo_path)
                    img = img.resize((128, 128), Image.LANCZOS)
                    self._logo_images[128] = img
                about_logo = ctk.CTkImage(
                    light_image=self._logo_images[128],
                    dark_image=self._logo_images[128],
                    size=(128, 128),
                )
                ctk.CTkLabel(
                    about_win, image=about_logo, text="",
                ).pack(pady=(20, 10))
                self._about_logo = about_logo  # manter referência
            except Exception:
                pass

        ctk.CTkLabel(
            about_win, text=f"{APP_NAME}",
            font=("Arial", 18, "bold"),
            text_color=COLORS["accent_cyan"],
        ).pack()

        ctk.CTkLabel(
            about_win, text=f"v{APP_VERSION}",
            font=("Arial", 12),
            text_color=COLORS["text_secondary"],
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            about_win,
            text="Engenheiro Virtual para LMU/rFactor 2\n"
                 "Inteligência Artificial + Heurísticas\n"
                 "para otimização de setups de corrida.",
            font=("Arial", 11),
            text_color=COLORS["text_primary"],
            justify="center",
        ).pack(pady=(0, 15))

        ctk.CTkButton(
            about_win, text="Fechar", width=100,
            command=about_win.destroy,
        ).pack()

    # ─────────────────────────────────────────────────────
    # Atualização periódica
    # ─────────────────────────────────────────────────────

    def _schedule_update(self):
        """Agenda atualização periódica da GUI."""
        if not self._running:
            return
        self._periodic_update()
        self._update_job = self.after(500, self._schedule_update)

    def _periodic_update(self):
        """Atualiza elementos visuais com dados atuais."""
        if not self.engine:
            return

        try:
            self._update_indicators()

            # Atualizar aba ativa
            current_tab = self.tabview.get()
            if "Telemetria" in current_tab:
                self.tab_telemetry.refresh()
            elif "Setup" in current_tab:
                self.tab_setup.refresh()

        except Exception as e:
            logger.debug("Erro na atualização periódica: %s", e)

    def _update_indicators(self):
        """Atualiza os indicadores de status no header."""
        if not self.engine:
            return

        # Game conectado?
        if hasattr(self.engine, "is_game_connected"):
            if self.engine.is_game_connected():
                self.ind_game.set_status("ok")
                car_info = self.engine.get_car_info()
                if car_info:
                    self.car_label.configure(
                        text=f"{car_info.get('vehicle_name', '')} @ "
                             f"{car_info.get('track_name', '')}"
                    )
                    self.status_label.configure(
                        text="Conectado ao LMU ✓",
                        text_color="#00cc44",
                    )
            else:
                self.ind_game.set_status("off")
                self.status_label.configure(
                    text="Aguardando conexão com LMU...",
                    text_color="#888888",
                )
        else:
            self.ind_game.set_status("off")

        # IA ativa?
        if hasattr(self.engine, "ai_confidence"):
            conf = self.engine.ai_confidence()
            if conf > 0.4:
                self.ind_ai.set_status("ok")
            elif conf > 0:
                self.ind_ai.set_status("warning")
            else:
                self.ind_ai.set_status("off")
        else:
            self.ind_ai.set_status("off")

        # DB ok?
        if hasattr(self.engine, "db"):
            self.ind_db.set_status("ok" if self.engine.db else "off")
        else:
            self.ind_db.set_status("off")

        # Atualizar clima
        if hasattr(self.engine, "get_weather_data"):
            weather = self.engine.get_weather_data()
            if weather:
                self._weather.update_weather(
                    rain=weather.get("rain", 0.0),
                    track_temp=weather.get("track_temp", 0.0),
                    ambient_temp=weather.get("air_temp", 0.0),
                    wetness=weather.get("wetness", 0.0),
                )

    # ─────────────────────────────────────────────────────
    # Métodos públicos
    # ─────────────────────────────────────────────────────

    def set_status(self, text: str, color: str = "#aaaaaa"):
        """Atualiza a mensagem na barra de status."""
        self.status_label.configure(text=text, text_color=color)

    # ─────────────────────────────────────────────────────
    # System Tray (Bandeja do Sistema)
    # ─────────────────────────────────────────────────────

    def _setup_tray(self):
        """Configura ícone na bandeja do sistema Windows."""
        try:
            import pystray
            from PIL import Image

            if not self._logo_path.exists():
                return

            tray_img = Image.open(self._logo_path)
            tray_img = tray_img.resize((64, 64), Image.LANCZOS)

            menu = pystray.Menu(
                pystray.MenuItem(
                    f"{APP_NAME} v{APP_VERSION}",
                    lambda: None, enabled=False,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Abrir", self._tray_show),
                pystray.MenuItem("Sair", self._tray_quit),
            )

            self._tray_icon = pystray.Icon(
                APP_NAME, tray_img, f"{APP_NAME}", menu,
            )

            import threading
            tray_thread = threading.Thread(
                target=self._tray_icon.run, daemon=True,
            )
            tray_thread.start()
            logger.info("Ícone na bandeja do sistema ativo.")

        except ImportError:
            logger.debug("pystray não disponível — sem ícone na bandeja.")
        except Exception as e:
            logger.debug("Erro ao configurar tray: %s", e)

    def _tray_show(self, icon=None, item=None):
        """Restaura a janela a partir da bandeja."""
        self.after(0, self._restore_window)

    def _restore_window(self):
        """Restaura a janela na thread do Tk."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def _tray_quit(self, icon=None, item=None):
        """Fecha o programa a partir da bandeja."""
        self.after(0, self._on_close)

    # ─────────────────────────────────────────────────────
    # Encerramento
    # ─────────────────────────────────────────────────────

    def _on_close(self):
        """Encerramento limpo da aplicação."""
        self._running = False
        if self._update_job:
            self.after_cancel(self._update_job)

        # Parar ícone da bandeja
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass

        if self.engine and hasattr(self.engine, "shutdown"):
            try:
                self.engine.shutdown()
            except Exception as e:
                logger.error("Erro ao desligar engine: %s", e)

        self.destroy()
        logger.info("Aplicação encerrada.")
