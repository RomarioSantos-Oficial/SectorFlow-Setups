"""
tab_setup.py — Aba unificada de Setup com interface conversacional.

Combina gerenciamento de arquivos .svm, criação de setup,
e uma interface de chat onde o usuário descreve problemas
do carro em linguagem natural e recebe sugestões da IA.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui.widgets import (
    Card,
    ChatBubble,
    ConfidenceBar,
    DeltaDisplay,
    SuggestedPhrase,
    COLORS,
)

logger = logging.getLogger("LMU_VE.gui.setup")


# ─── Frases Sugeridas ──────────────────────────────────

SUGGESTED_PHRASES = [
    # Problemas de equilíbrio
    ("🔄", "O carro está com understeer na entrada da curva"),
    ("🔄", "O carro está com oversteer na saída da curva"),
    ("🔄", "O carro escorrega muito no meio da curva"),
    ("🔄", "O carro está instável em alta velocidade"),

    # Problemas de pneu
    ("🏎", "Os pneus dianteiros superaquecem rápido"),
    ("🏎", "Os pneus traseiros não chegam na temperatura"),
    ("🏎", "O desgaste dos pneus está muito alto"),

    # Problemas de freio
    ("🛑", "O carro trava as rodas ao frear"),
    ("🛑", "Os freios não estão parando o carro"),
    ("🛑", "O carro puxa para um lado ao frear"),

    # Problemas de tração
    ("⚡", "O carro patina na saída das curvas lentas"),
    ("⚡", "Perco tração em curvas de alta velocidade"),

    # Clima
    ("🌧", "Preciso de um setup para chuva"),
    ("🌧", "A pista está secando, quero ajustar"),

    # Geral
    ("🎯", "Quero mais velocidade nas retas"),
    ("🎯", "O carro está muito duro nos meios-fios"),
    ("🎯", "Quero um setup mais estável e previsível"),

    # Combustível / Energia
    ("⛽", "Estou gastando muito combustível"),
    ("💨", "O carro bate no chão (bottoming)"),
    ("💨", "O desgaste dos pneus está muito rápido"),
]

# Frases extras por classe de carro
_CLASS_PHRASES = {
    "hypercar": [
        ("⚡", "A bateria está acabando rápido"),
        ("⚡", "Quero melhorar a gestão de energia"),
        ("⚡", "O regen está muito agressivo na frenagem"),
        ("⚡", "Quero mais energia virtual disponível"),
    ],
    "lmp2": [
        ("🎯", "O carro é imprevisível em curvas rápidas"),
        ("💨", "A direção está pesada e lenta"),
    ],
    "lmgt3": [
        ("🎯", "O carro é imprevisível, não confio nele"),
        ("💨", "A direção está pesada e lenta"),
        ("🛑", "O ABS não está ajudado o suficiente"),
    ],
}

# Frases extras por tipo de sessão
_SESSION_PHRASES = {
    "quali": [
        ("🏁", "Quero setup agressivo para qualificação"),
        ("🏁", "Quero maximizar velocidade em 1 volta"),
    ],
    "race": [
        ("🏁", "Quero setup conservador para corrida longa"),
        ("🏁", "Preciso preservar pneus na corrida"),
    ],
}

# Frases extras por clima
_WEATHER_PHRASES = {
    "wet": [
        ("🌧", "A pista está encharcada, preciso de mais dianteira"),
        ("🌧", "Quero setup mais seguro para chuva forte"),
    ],
}


class SetupTab(ctk.CTkFrame):
    """Aba unificada de Setup com chat conversacional."""

    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._chat_messages: list[dict] = []
        self._delta_widgets: dict[str, DeltaDisplay] = {}
        self._build_ui()
        self._show_welcome()

    def _build_ui(self):
        # Layout principal: lado esquerdo (chat) + lado direito (painel)
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=5, pady=5)

        # ═══ COLUNA ESQUERDA: Chat + Input ═══════════════
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))

        # Header do chat
        chat_header = ctk.CTkFrame(left, fg_color=COLORS["bg_card"],
                                   corner_radius=12, height=50)
        chat_header.pack(fill="x", pady=(0, 4))
        chat_header.pack_propagate(False)

        ctk.CTkLabel(
            chat_header, text="🤖 Engenheiro Virtual",
            font=("Arial", 15, "bold"),
            text_color=COLORS["accent_cyan"],
        ).pack(side="left", padx=14)

        self._confidence = ConfidenceBar(chat_header)
        self._confidence.pack(side="right", padx=14, fill="x", expand=True)

        # Área do chat (scrollable)
        self._chat_scroll = ctk.CTkScrollableFrame(
            left, fg_color=COLORS["bg_dark"],
            corner_radius=12,
            border_width=1, border_color=COLORS["separator"],
        )
        self._chat_scroll.pack(fill="both", expand=True, pady=(0, 4))

        # Frases sugeridas (carrossel horizontal scrollable)
        phrases_frame = ctk.CTkFrame(left, fg_color="transparent")
        phrases_frame.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            phrases_frame, text="💡 Sugestões rápidas:",
            font=("Arial", 10, "bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=4, pady=(0, 2))

        self._phrases_scroll = ctk.CTkScrollableFrame(
            phrases_frame, fg_color="transparent",
            height=80, orientation="horizontal",
        )
        self._phrases_scroll.pack(fill="x")

        for icon, text in SUGGESTED_PHRASES:
            btn = SuggestedPhrase(
                self._phrases_scroll, text=text, icon=icon,
                callback=self._on_phrase_click,
            )
            btn.pack(side="left", padx=3, pady=2)

        # Input do chat
        input_frame = ctk.CTkFrame(
            left, fg_color=COLORS["bg_card"],
            corner_radius=12, border_width=1,
            border_color=COLORS["separator"],
        )
        input_frame.pack(fill="x")

        self._chat_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Descreva o problema do carro ou digite um comando...",
            font=("Arial", 12), height=40,
            fg_color=COLORS["bg_input"],
            border_width=0, corner_radius=10,
        )
        self._chat_input.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        self._chat_input.bind("<Return>", self._on_send_message)

        self._btn_send = ctk.CTkButton(
            input_frame, text="📤", width=40, height=40,
            fg_color=COLORS["accent_blue"], hover_color="#3588b8",
            corner_radius=10, font=("Arial", 16),
            command=lambda: self._on_send_message(None),
        )
        self._btn_send.pack(side="right", padx=(0, 8), pady=8)

        # ═══ COLUNA DIREITA: Setup & Sugestões ═══════════
        right = ctk.CTkScrollableFrame(main, fg_color="transparent", width=340)
        right.pack(side="right", fill="y", padx=(4, 0), pady=0)

        # ─── Setup Base Atual ─────────────────
        base_card = Card(right, title="📄 Setup Base")
        base_card.pack(fill="x", pady=(0, 6))

        self._base_info = ctk.CTkLabel(
            base_card, text="Nenhum setup carregado",
            font=("Arial", 11), text_color=COLORS["text_secondary"],
            wraplength=290, justify="left",
        )
        self._base_info.pack(fill="x", padx=14, pady=(0, 6))

        base_btns = ctk.CTkFrame(base_card, fg_color="transparent")
        base_btns.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(
            base_btns, text="📂 Carregar .svm", width=130, height=32,
            fg_color=COLORS["accent_blue"], hover_color="#3588b8",
            font=("Arial", 11), command=self._on_load_base,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            base_btns, text="👁 Ver Detalhes", width=110, height=32,
            fg_color=COLORS["accent_purple"], hover_color="#7a3bb8",
            font=("Arial", 11), command=self._on_view_base,
        ).pack(side="left", padx=(0, 4))

        self._btn_clear = ctk.CTkButton(
            base_btns, text="✕", width=32, height=32,
            fg_color=COLORS["accent_red"], hover_color="#cc3355",
            font=("Arial", 12), command=self._on_clear_base,
        )
        self._btn_clear.pack(side="right")

        # ─── Ações Rápidas ────────────────────
        actions_card = Card(right, title="⚡ Ações Rápidas")
        actions_card.pack(fill="x", pady=(0, 6))

        actions_grid = ctk.CTkFrame(actions_card, fg_color="transparent")
        actions_grid.pack(fill="x", padx=14, pady=(0, 10))
        actions_grid.columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            actions_grid, text="✨ Criar Setup", height=36,
            fg_color=COLORS["accent_green"], hover_color="#009955",
            font=("Arial", 11, "bold"), command=self._on_create_setup,
        ).grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        ctk.CTkButton(
            actions_grid, text="✏️ Editar Setup", height=36,
            fg_color=COLORS["accent_orange"], hover_color="#cc7030",
            font=("Arial", 11), command=self._on_edit_setup,
        ).grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        ctk.CTkButton(
            actions_grid, text="🔄 Pedir Sugestão IA", height=36,
            fg_color=COLORS["accent_blue"], hover_color="#3588b8",
            font=("Arial", 11), command=self._on_request_ai,
        ).grid(row=1, column=0, padx=2, pady=2, sticky="ew")

        ctk.CTkButton(
            actions_grid, text="📐 Usar Heurísticas", height=36,
            fg_color=COLORS["accent_purple"], hover_color="#7a3bb8",
            font=("Arial", 11), command=self._on_request_heuristics,
        ).grid(row=1, column=1, padx=2, pady=2, sticky="ew")

        # ─── Sugestões Atuais ─────────────────
        sug_card = Card(right, title="💡 Sugestões de Ajuste")
        sug_card.pack(fill="both", expand=True, pady=(0, 6))

        # Scrollable frame para todos os parâmetros
        self._sug_scroll = ctk.CTkScrollableFrame(
            sug_card, fg_color="transparent", height=420,
        )
        self._sug_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Todos os parâmetros organizados por categoria e nível IA
        _PARAM_SECTIONS = [
            ("🛩️ Aerodinâmica", [
                ("delta_rw", "Asa Traseira (RW)"),
            ], "basic"),
            ("🔧 Molas", [
                ("delta_spring_f", "Mola Dianteira"),
                ("delta_spring_r", "Mola Traseira"),
            ], "basic"),
            ("📐 Camber", [
                ("delta_camber_f", "Camber Diant."),
                ("delta_camber_r", "Camber Tras."),
            ], "basic"),
            ("🎈 Pressão dos Pneus", [
                ("delta_pressure_f", "Pressão Pneu D."),
                ("delta_pressure_r", "Pressão Pneu T."),
            ], "basic"),
            ("🛑 Freios", [
                ("delta_brake_press", "Pressão Freio"),
                ("delta_rear_brake_bias", "Brake Bias (Balanço)"),
            ], "basic"),
            ("🎮 Eletrônicos (TC / ABS)", [
                ("delta_tc_onboard", "TC Onboard (Liga/Desliga)"),
                ("delta_tc_map", "TC Map"),
                ("delta_tc_power_cut", "TC Power Cut"),
                ("delta_tc_slip_angle", "TC Slip Angle"),
                ("delta_abs_map", "ABS Map"),
            ], "basic"),
            ("🔄 Barra Anti-Rolagem", [
                ("delta_arb_f", "ARB Diant."),
                ("delta_arb_r", "ARB Tras."),
            ], "intermediate"),
            ("🦶 Toe", [
                ("delta_toe_f", "Toe Diant."),
                ("delta_toe_r", "Toe Tras."),
            ], "intermediate"),
            ("📏 Ride Height", [
                ("delta_ride_height_f", "Ride Height D."),
                ("delta_ride_height_r", "Ride Height T."),
            ], "intermediate"),
            ("🔨 Amortecedores (Lento)", [
                ("delta_slow_bump_f", "Bump Lento D."),
                ("delta_slow_bump_r", "Bump Lento T."),
                ("delta_slow_rebound_f", "Rebound Lento D."),
                ("delta_slow_rebound_r", "Rebound Lento T."),
            ], "intermediate"),
            ("⚙️ Diferencial", [
                ("delta_diff_preload", "Pré-carga Diferencial"),
            ], "intermediate"),
            ("🔧 Molas (Per-Roda)", [
                ("delta_spring_fl", "Mola FL"),
                ("delta_spring_fr", "Mola FR"),
                ("delta_spring_rl", "Mola RL"),
                ("delta_spring_rr", "Mola RR"),
            ], "advanced"),
            ("📐 Camber (Per-Roda)", [
                ("delta_camber_fl", "Camber FL"),
                ("delta_camber_fr", "Camber FR"),
                ("delta_camber_rl", "Camber RL"),
                ("delta_camber_rr", "Camber RR"),
            ], "advanced"),
            ("🎈 Pressão (Per-Roda)", [
                ("delta_pressure_fl", "Pressão FL"),
                ("delta_pressure_fr", "Pressão FR"),
                ("delta_pressure_rl", "Pressão RL"),
                ("delta_pressure_rr", "Pressão RR"),
            ], "advanced"),
            ("📏 Ride Height (Per-Roda)", [
                ("delta_ride_height_fl", "Ride Height FL"),
                ("delta_ride_height_fr", "Ride Height FR"),
                ("delta_ride_height_rl", "Ride Height RL"),
                ("delta_ride_height_rr", "Ride Height RR"),
            ], "advanced"),
            ("🔨 Amortecedores (Rápido)", [
                ("delta_fast_bump_f", "Bump Rápido D."),
                ("delta_fast_bump_r", "Bump Rápido T."),
                ("delta_fast_rebound_f", "Rebound Rápido D."),
                ("delta_fast_rebound_r", "Rebound Rápido T."),
            ], "advanced"),
            ("🌀 Dutos de Freio", [
                ("delta_brake_duct_f", "Duto Freio D."),
                ("delta_brake_duct_r", "Duto Freio T."),
            ], "advanced"),
            ("🔥 Motor / Energia", [
                ("delta_radiator", "Radiador"),
                ("delta_engine_mix", "Mix Motor"),
                ("delta_virtual_energy", "Energia Virtual"),
                ("delta_regen_map", "Mapa Regen"),
            ], "advanced"),
        ]

        _LEVEL_ORDER = {"basic": 0, "intermediate": 1, "advanced": 2}
        self._section_frames: list[tuple[ctk.CTkFrame, str]] = []
        self._current_display_level = "basic"

        for category, items, level in _PARAM_SECTIONS:
            sec = ctk.CTkFrame(self._sug_scroll, fg_color="transparent")
            sec.pack(fill="x")

            ctk.CTkLabel(
                sec, text=category, font=("Arial", 11, "bold"),
                text_color=COLORS["accent_cyan"], anchor="w",
            ).pack(fill="x", padx=8, pady=(6, 1))

            for key, label in items:
                w = DeltaDisplay(sec, param_name=label)
                w.pack(fill="x", padx=12, pady=1)
                self._delta_widgets[key] = w

            self._section_frames.append((sec, level))

        self._update_param_visibility()

        # Botão aplicar
        self._btn_apply = ctk.CTkButton(
            sug_card, text="✅ Aplicar Ajustes", height=36,
            fg_color=COLORS["accent_green"], hover_color="#009955",
            font=("Arial", 12, "bold"), state="disabled",
            command=self._on_apply,
        )
        self._btn_apply.pack(fill="x", padx=14, pady=(6, 10))

        # ─── Avaliação ────────────────────────
        rate_card = Card(right, title="⭐ Avaliar Resultado")
        rate_card.pack(fill="x", pady=(0, 6))

        rate_row = ctk.CTkFrame(rate_card, fg_color="transparent")
        rate_row.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(
            rate_row, text="👍 Melhorou", width=90, height=32,
            fg_color="#28703e", hover_color="#1f5530",
            font=("Arial", 10),
            command=lambda: self._on_rate(1.0),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            rate_row, text="😐 Igual", width=70, height=32,
            fg_color="#555555", hover_color="#444444",
            font=("Arial", 10),
            command=lambda: self._on_rate(0.0),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            rate_row, text="👎 Piorou", width=90, height=32,
            fg_color="#703028", hover_color="#551f1a",
            font=("Arial", 10),
            command=lambda: self._on_rate(-1.0),
        ).pack(side="left", padx=2)

        # ─── Avisos ──────────────────────────
        warn_card = Card(right, title="⚠ Avisos de Segurança")
        warn_card.pack(fill="x", pady=(0, 6))
        self._warnings_text = ctk.CTkTextbox(
            warn_card, height=60, state="disabled",
            font=("JetBrains Mono", 10),
            fg_color=COLORS["bg_card"],
            text_color=COLORS["accent_yellow"],
        )
        self._warnings_text.pack(fill="x", padx=12, pady=(0, 10))

        # ─── Auto-Suggest ─────────────────────
        auto_card = Card(right, title="🤖 IA Autônoma")
        auto_card.pack(fill="x", pady=(0, 6))

        auto_row1 = ctk.CTkFrame(auto_card, fg_color="transparent")
        auto_row1.pack(fill="x", padx=14, pady=(0, 4))

        ctk.CTkLabel(
            auto_row1, text="Sugestão automática:",
            font=("Arial", 11), text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self._auto_toggle = ctk.CTkSwitch(
            auto_row1, text="", width=42,
            onvalue=1, offvalue=0,
            command=self._on_toggle_auto_suggest,
        )
        self._auto_toggle.select()  # Habilitado por padrão
        self._auto_toggle.pack(side="right")

        auto_row2 = ctk.CTkFrame(auto_card, fg_color="transparent")
        auto_row2.pack(fill="x", padx=14, pady=(0, 4))

        ctk.CTkLabel(
            auto_row2, text="A cada",
            font=("Arial", 11), text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self._interval_var = ctk.StringVar(value="3")
        self._interval_menu = ctk.CTkOptionMenu(
            auto_row2, values=["2", "3", "5", "10"],
            variable=self._interval_var, width=60, height=28,
            fg_color=COLORS["bg_input"],
            font=("Arial", 11),
            command=self._on_change_interval,
        )
        self._interval_menu.pack(side="left", padx=4)

        ctk.CTkLabel(
            auto_row2, text="voltas",
            font=("Arial", 11), text_color=COLORS["text_secondary"],
        ).pack(side="left")

        # Nível atual da IA
        auto_row3 = ctk.CTkFrame(auto_card, fg_color="transparent")
        auto_row3.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            auto_row3, text="Nível IA:",
            font=("Arial", 11), text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self._level_label = ctk.CTkLabel(
            auto_row3, text="BASIC",
            font=("Arial", 11, "bold"), text_color=COLORS["accent_cyan"],
        )
        self._level_label.pack(side="right")

        # ─── Pré-Carga de Conhecimento ────────
        seed_card = Card(right, title="📚 Base de Conhecimento")
        seed_card.pack(fill="x", pady=(0, 6))

        self._seed_btn = ctk.CTkButton(
            seed_card, text="🧠 Carregar conhecimento inicial",
            fg_color=COLORS.get("accent_green", "#2ecc71"),
            hover_color="#27ae60",
            font=("Arial", 12, "bold"),
            height=34,
            command=self._on_seed_knowledge,
        )
        self._seed_btn.pack(fill="x", padx=14, pady=(4, 4))

        self._learn_setups_btn = ctk.CTkButton(
            seed_card, text="📂 Aprender de todos os setups",
            fg_color=COLORS.get("accent_orange", "#e67e22"),
            hover_color="#d35400",
            font=("Arial", 11, "bold"),
            height=32,
            command=self._on_learn_from_setups,
        )
        self._learn_setups_btn.pack(fill="x", padx=14, pady=(0, 4))

        self._stats_btn = ctk.CTkButton(
            seed_card, text="📊 Ver estatísticas da IA",
            fg_color=COLORS["bg_input"],
            hover_color=COLORS.get("bg_card", "#2a2d31"),
            font=("Arial", 11),
            height=30,
            command=self._on_show_stats,
        )
        self._stats_btn.pack(fill="x", padx=14, pady=(0, 4))

        self._memory_btn = ctk.CTkButton(
            seed_card, text="🧠 Ver memória carro×pista",
            fg_color=COLORS["bg_input"],
            hover_color=COLORS.get("bg_card", "#2a2d31"),
            font=("Arial", 11),
            height=30,
            command=self._on_show_memory,
        )
        self._memory_btn.pack(fill="x", padx=14, pady=(0, 10))

        # ─── API Key (Multi-Provedor LLM) ────────
        llm_card = Card(right, title="🤖 LLM — Aprendizagem Avançada")
        llm_card.pack(fill="x", pady=(0, 6))

        # Provedor de API
        ctk.CTkLabel(
            llm_card, text="Provedor:",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=14, pady=(4, 0))

        from core.llm_advisor import API_PROVIDERS
        provider_names = {
            k: v["name"] for k, v in API_PROVIDERS.items()
        }
        initial_provider = "openrouter"
        if self.engine and hasattr(self.engine, "config"):
            initial_provider = self.engine.config.get(
                "llm_provider", "openrouter"
            )

        self._llm_provider_var = ctk.StringVar(value=initial_provider)
        self._llm_provider_menu = ctk.CTkOptionMenu(
            llm_card,
            values=list(provider_names.keys()),
            variable=self._llm_provider_var, height=28,
            fg_color=COLORS["bg_input"],
            font=("Arial", 10),
            command=self._on_provider_changed,
        )
        self._llm_provider_menu.pack(fill="x", padx=14, pady=(2, 4))

        # URL personalizada (só visível para "custom")
        self._custom_url_frame = ctk.CTkFrame(
            llm_card, fg_color="transparent"
        )
        ctk.CTkLabel(
            self._custom_url_frame, text="URL da API:",
            font=("Arial", 10),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        initial_custom_url = ""
        if self.engine and hasattr(self.engine, "config"):
            initial_custom_url = self.engine.config.get(
                "llm_custom_url", ""
            )

        self._custom_url_entry = ctk.CTkEntry(
            self._custom_url_frame,
            placeholder_text="https://api.exemplo.com/v1/chat/completions",
            font=("JetBrains Mono", 9),
            fg_color=COLORS["bg_input"],
        )
        self._custom_url_entry.pack(fill="x")
        if initial_custom_url:
            self._custom_url_entry.insert(0, initial_custom_url)

        if initial_provider in ("custom", "lmstudio"):
            self._custom_url_frame.pack(
                fill="x", padx=14, pady=(0, 4)
            )
            if initial_provider == "lmstudio" and not initial_custom_url:
                self._custom_url_entry.insert(
                    0, "http://localhost:1234/v1/chat/completions"
                )

        # API Key
        ctk.CTkLabel(
            llm_card, text="API Key:",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=14, pady=(2, 0))

        api_row = ctk.CTkFrame(llm_card, fg_color="transparent")
        api_row.pack(fill="x", padx=14, pady=(2, 4))

        initial_key = ""
        if self.engine and hasattr(self.engine, "config"):
            initial_key = self.engine.config.get("openrouter_api_key", "")

        self._api_key_entry = ctk.CTkEntry(
            api_row, placeholder_text="cole sua API key aqui...",
            font=("JetBrains Mono", 10), show="•",
            fg_color=COLORS["bg_input"],
        )
        self._api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        if initial_key:
            self._api_key_entry.insert(0, initial_key)

        self._api_show_btn = ctk.CTkButton(
            api_row, text="👁", width=30, height=28,
            fg_color=COLORS["bg_input"],
            command=self._toggle_api_key_visibility,
        )
        self._api_show_btn.pack(side="right")

        # Modelo LLM
        ctk.CTkLabel(
            llm_card, text="Modelo:",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=14, pady=(2, 0))

        initial_model = "deepseek/deepseek-chat-v3-0324"
        if self.engine and hasattr(self.engine, "config"):
            initial_model = self.engine.config.get(
                "openrouter_model", initial_model
            )

        # Pegar modelos do provedor selecionado
        prov_info = API_PROVIDERS.get(
            initial_provider, API_PROVIDERS["openrouter"]
        )
        prov_models = prov_info["models"] or [initial_model]

        self._llm_model_var = ctk.StringVar(value=initial_model)
        self._llm_model_menu = ctk.CTkOptionMenu(
            llm_card,
            values=prov_models if prov_models else [initial_model],
            variable=self._llm_model_var, height=28,
            fg_color=COLORS["bg_input"],
            font=("Arial", 10),
        )
        self._llm_model_menu.pack(fill="x", padx=14, pady=(2, 4))

        # Campo de modelo custom (para providers com lista vazia ou custom)
        self._custom_model_frame = ctk.CTkFrame(
            llm_card, fg_color="transparent"
        )
        ctk.CTkLabel(
            self._custom_model_frame, text="Nome do modelo:",
            font=("Arial", 10),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")
        self._custom_model_entry = ctk.CTkEntry(
            self._custom_model_frame,
            placeholder_text="ex: gpt-4o-mini",
            font=("JetBrains Mono", 9),
            fg_color=COLORS["bg_input"],
        )
        self._custom_model_entry.pack(fill="x")
        if initial_provider in ("custom", "lmstudio"):
            self._custom_model_frame.pack(
                fill="x", padx=14, pady=(0, 4)
            )

        btn_row_llm = ctk.CTkFrame(llm_card, fg_color="transparent")
        btn_row_llm.pack(fill="x", padx=14, pady=(0, 4))

        ctk.CTkButton(
            btn_row_llm, text="💾 Salvar", height=28,
            fg_color=COLORS["accent_green"], hover_color="#009955",
            font=("Arial", 11, "bold"),
            command=self._on_save_api_key,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            btn_row_llm, text="🔌 Testar", height=28,
            fg_color=COLORS["accent_blue"], hover_color="#3588b8",
            font=("Arial", 11),
            command=self._on_test_api,
        ).pack(side="right", fill="x", expand=True)

        # Status do LLM
        self._llm_status = ctk.CTkLabel(
            llm_card, text="⚪ Não configurado",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        )
        self._llm_status.pack(anchor="w", padx=14, pady=(0, 4))

        # Checkbox: auto-consultar LLM a cada volta
        self._llm_auto_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            llm_card,
            text="🔄 Auto-analisar telemetria com LLM",
            variable=self._llm_auto_var,
            font=("Arial", 10),
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Atualizar status inicial
        if initial_key:
            self._llm_status.configure(
                text="🟢 API configurada",
                text_color=COLORS["accent_green"],
            )

        # ═══════════════════════════════════════════
        # Card: Autonomia da IA (Destilação)
        # ═══════════════════════════════════════════
        autonomy_card = Card(
            right,
            title="🎓 Autonomia da IA",
        )
        autonomy_card.pack(
            fill="x", padx=6, pady=(0, 6),
        )

        # Barra de progresso de autonomia
        ctk.CTkLabel(
            autonomy_card,
            text="Progresso para IA autônoma:",
            font=("Arial", 10),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=14, pady=(4, 0))

        self._autonomy_bar = ctk.CTkProgressBar(
            autonomy_card,
            height=14,
            corner_radius=4,
        )
        self._autonomy_bar.pack(
            fill="x", padx=14, pady=(2, 0),
        )
        self._autonomy_bar.set(0)

        self._autonomy_label = ctk.CTkLabel(
            autonomy_card,
            text="⚪ Destilação não iniciada",
            font=("Arial", 10),
            text_color=COLORS["text_secondary"],
        )
        self._autonomy_label.pack(
            anchor="w", padx=14, pady=(2, 0),
        )

        # Status de destilação (atualizado durante processo)
        self._distill_status = ctk.CTkLabel(
            autonomy_card,
            text="",
            font=("Arial", 9),
            text_color=COLORS["text_secondary"],
        )
        self._distill_status.pack(
            anchor="w", padx=14, pady=(0, 2),
        )

        # Botão de destilação
        self._distill_btn = ctk.CTkButton(
            autonomy_card,
            text="🧠 Destilar Conhecimento do LLM",
            height=28,
            fg_color=COLORS["accent_blue"],
            hover_color="#3588b8",
            font=("Arial", 11, "bold"),
            command=self._on_start_distillation,
        )
        self._distill_btn.pack(
            fill="x", padx=14, pady=(4, 10),
        )

        # Carregar status de autonomia salvo
        self._update_autonomy_display()

    # ─── Chat: Mensagens ────────────────────────────────

    def _show_welcome(self):
        """Mostra mensagem de boas-vindas no chat."""
        self._add_message(
            "Olá! Sou seu Engenheiro Virtual. 🏁\n\n"
            "Me diga o que está sentindo no carro e eu vou sugerir "
            "ajustes no setup. Você pode:\n\n"
            "• Descrever um problema (ex: 'o carro está com understeer')\n"
            "• Clicar em uma frase sugerida abaixo\n"
            "• Usar os botões de ação ao lado\n\n"
            "Comece carregando um arquivo .svm base no painel à direita!",
            sender="ai",
        )

    def update_phrases(self, car_class: str = "",
                       session_type: str = "", weather: str = ""):
        """Atualiza frases sugeridas com base no contexto atual."""
        # Limpar frases existentes
        for w in self._phrases_scroll.winfo_children():
            w.destroy()

        # Frases base
        phrases = list(SUGGESTED_PHRASES)

        # Adicionar frases por classe de carro
        car_class_lower = car_class.lower() if car_class else ""
        if car_class_lower in _CLASS_PHRASES:
            phrases.extend(_CLASS_PHRASES[car_class_lower])

        # Adicionar frases por tipo de sessão
        session_lower = session_type.lower() if session_type else ""
        if session_lower in _SESSION_PHRASES:
            phrases.extend(_SESSION_PHRASES[session_lower])

        # Adicionar frases por clima
        weather_lower = weather.lower() if weather else ""
        if weather_lower in _WEATHER_PHRASES:
            phrases.extend(_WEATHER_PHRASES[weather_lower])

        for icon, text in phrases:
            btn = SuggestedPhrase(
                self._phrases_scroll, text=text, icon=icon,
                callback=self._on_phrase_click,
            )
            btn.pack(side="left", padx=3, pady=2)

    def add_message(self, text: str, sender: str = "system"):
        """Adiciona uma mensagem ao chat (API pública)."""
        now = datetime.now().strftime("%H:%M")
        msg = {"text": text, "sender": sender, "time": now}
        self._chat_messages.append(msg)

        bubble = ChatBubble(
            self._chat_scroll, message=text,
            sender=sender, timestamp=now,
        )
        bubble.pack(fill="x", padx=4, pady=2)

        # Auto-scroll para o fim
        self._chat_scroll.after(50, lambda: self._chat_scroll._parent_canvas.yview_moveto(1.0))

    # Alias interno para compatibilidade
    _add_message = add_message

    def _on_phrase_click(self, text: str):
        """Processa clique em frase sugerida."""
        self._chat_input.delete(0, "end")
        self._chat_input.insert(0, text)
        self._on_send_message(None)

    def _parse_direct_delta_command(self, text: str) -> dict | None:
        """
        Detecta comandos diretos de ajuste no texto do usuário.
        Ex: "tração +2", "TC power cut -1", "asa traseira +3", "abs +1"
        Retorna dict {delta_name: int_value} ou None.
        """
        import re
        text_lower = text.lower().strip()

        # Mapeamento de palavras-chave → delta_name
        _KEYWORD_MAP = {
            # Aerodinâmica
            "asa": "delta_rw", "asa traseira": "delta_rw",
            "rw": "delta_rw", "rear wing": "delta_rw",
            # Molas
            "mola dianteira": "delta_spring_f", "mola d": "delta_spring_f",
            "mola traseira": "delta_spring_r", "mola t": "delta_spring_r",
            "mola": "delta_spring_f",
            # Camber
            "camber d": "delta_camber_f", "camber dianteiro": "delta_camber_f",
            "camber t": "delta_camber_r", "camber traseiro": "delta_camber_r",
            "camber": "delta_camber_f",
            # Pressão
            "pressão d": "delta_pressure_f", "pressao d": "delta_pressure_f",
            "pressão t": "delta_pressure_r", "pressao t": "delta_pressure_r",
            "pressão": "delta_pressure_f", "pressao": "delta_pressure_f",
            # Freios
            "freio": "delta_brake_press", "brake": "delta_brake_press",
            "brake bias": "delta_rear_brake_bias",
            "balanço freio": "delta_rear_brake_bias",
            "balanco freio": "delta_rear_brake_bias",
            # TC / ABS
            "tc onboard": "delta_tc_onboard",
            "tc map": "delta_tc_map", "tc mapa": "delta_tc_map",
            "tc power cut": "delta_tc_power_cut",
            "tc power": "delta_tc_power_cut",
            "tc slip angle": "delta_tc_slip_angle",
            "tc slip": "delta_tc_slip_angle",
            "tração": "delta_tc_map", "tracao": "delta_tc_map",
            "traction": "delta_tc_map",
            "tc": "delta_tc_map",
            "abs": "delta_abs_map", "abs map": "delta_abs_map",
            # ARB
            "arb d": "delta_arb_f", "arb t": "delta_arb_r",
            "anti rolagem d": "delta_arb_f", "anti rolagem t": "delta_arb_r",
            # Ride Height
            "ride height d": "delta_ride_height_f",
            "ride height t": "delta_ride_height_r",
            "altura d": "delta_ride_height_f",
            "altura t": "delta_ride_height_r",
            # Diferencial
            "diferencial": "delta_diff_preload", "diff": "delta_diff_preload",
        }

        # Tentar encontrar padrão: <keyword> <+/- número>
        # Ordenar keywords por tamanho desc para match mais específico primeiro
        sorted_keys = sorted(_KEYWORD_MAP.keys(), key=len, reverse=True)

        deltas = {}
        for keyword in sorted_keys:
            pattern = re.compile(
                rf'\b{re.escape(keyword)}\b\s*([+-]?\s*\d+)', re.IGNORECASE
            )
            m = pattern.search(text_lower)
            if m:
                delta_name = _KEYWORD_MAP[keyword]
                if delta_name not in deltas:  # Primeiro match vence
                    val_str = m.group(1).replace(" ", "")
                    try:
                        deltas[delta_name] = int(val_str)
                    except ValueError:
                        continue

        # Fallback: padrão genérico "aumentar/diminuir <keyword>"
        if not deltas:
            inc_words = ("aumentar", "subir", "mais", "increase", "up")
            dec_words = ("diminuir", "baixar", "menos", "decrease", "down",
                         "reduzir")
            direction = 0
            for w in inc_words:
                if w in text_lower:
                    direction = 1
                    break
            if not direction:
                for w in dec_words:
                    if w in text_lower:
                        direction = -1
                        break

            if direction:
                for keyword in sorted_keys:
                    if keyword in text_lower:
                        delta_name = _KEYWORD_MAP[keyword]
                        if delta_name not in deltas:
                            deltas[delta_name] = direction
                        break  # Apenas o primeiro match

        return deltas if deltas else None

    def _on_send_message(self, event):
        """Envia mensagem do usuário e processa."""
        text = self._chat_input.get().strip()
        if not text:
            return

        self._chat_input.delete(0, "end")
        self._add_message(text, sender="user")

        # Processar a mensagem
        self._process_user_message(text)

    def _process_user_message(self, text: str):
        """Analisa a mensagem do usuário e gera resposta + sugestões."""
        text_lower = text.lower()

        # ── Detecção de comando direto de ajuste ──
        direct_deltas = self._parse_direct_delta_command(text)
        if direct_deltas:
            # Mostrar deltas imediatamente no painel
            names = ", ".join(
                f"{k.replace('delta_', '')}: {'+' if v > 0 else ''}{v}"
                for k, v in direct_deltas.items()
            )
            self._add_message(
                f"✅ Ajuste direto aplicado na sugestão: {names}",
                sender="ai",
            )
            self.display_suggestions(
                direct_deltas, ["💬 Ajuste direto via chat"],
            )

        # Mapear palavras-chave para feedback da IA
        feedback = self._extract_feedback(text_lower)

        if not self.engine:
            self._add_message(
                "⚠️ Engine não conectada. Conecte-se ao LMU primeiro.",
                sender="system",
            )
            return

        # Verificar se tem setup base
        has_base = (hasattr(self.engine, "get_base_setup")
                    and self.engine.get_base_setup())

        # Tentar enviar feedback extraído
        if feedback and hasattr(self.engine, "telemetry"):
            try:
                self.engine.telemetry.set_user_feedback(
                    bias=feedback.get("bias", 0),
                    entry=feedback.get("entry", 0),
                    mid=feedback.get("mid", 0),
                    exit_=feedback.get("exit", 0),
                    confidence=feedback.get("confidence", 0.7),
                )
            except Exception:
                pass

        # Tentar usar LLM se disponível
        llm = getattr(self.engine, "llm_advisor", None)
        if llm and llm.enabled:
            self._add_message("⏳ Consultando IA...", sender="system")
            telemetry_ctx = self._get_telemetry_context()
            car_class = getattr(self.engine, "_car_class", None) or "hypercar"

            # Timeout visual: avisar se demorar mais de 12s
            self._llm_timeout_id = self.after(
                12000, self._show_llm_timeout_notice,
            )

            def _on_llm_response(response_text: str):
                # Callback executado em thread — usar after() para thread-safety
                self.after(10, self._handle_llm_response, response_text,
                           feedback, has_base)

            llm.chat(
                text, telemetry_context=telemetry_ctx,
                car_class=car_class, callback=_on_llm_response,
            )
        else:
            # Fallback: respostas locais (sem LLM)
            response = self._generate_response(text_lower, feedback, has_base)
            self._add_message(response, sender="ai")

        # Se possível, gerar sugestões
        if has_base and feedback:
            self._auto_suggest(feedback)

    def _show_llm_timeout_notice(self):
        """Mostra aviso se a consulta LLM demorar demais."""
        self._add_message(
            "⏳ A IA ainda está processando... "
            "Pode demorar até 30s na primeira consulta.",
            sender="system",
        )

    def _handle_llm_response(self, response_text: str, feedback: dict,
                              has_base: bool):
        """Processa resposta do LLM na thread principal do Tk."""
        try:
            # Cancelar timeout visual
            if hasattr(self, '_llm_timeout_id') and self._llm_timeout_id:
                self.after_cancel(self._llm_timeout_id)
                self._llm_timeout_id = None

            # Remover mensagens de "Consultando IA..." e timeout
            children = self._chat_scroll.winfo_children()
            for child in reversed(children):
                msg = getattr(child, 'message_text', '')
                if msg and ("Consultando IA" in msg or "ainda está processando" in msg):
                    child.destroy()

            self._add_message(response_text, sender="ai")

            # ── Aprendizagem via chat ──
            # Tentar extrair ajustes JSON da resposta do LLM para
            # alimentar a rede neural (mesmo fora de pilotagem)
            chat_deltas = self._try_learn_from_chat(response_text, feedback)

            # ── Mostrar ajustes do LLM no painel de sugestões ──
            if chat_deltas:
                self.display_suggestions(
                    chat_deltas, ["💬 Sugestão via chat (LLM)"]
                )

        except Exception as e:
            self._add_message(
                f"⚠️ Erro ao exibir resposta: {e}", sender="system",
            )

    def _try_learn_from_chat(self, response_text: str,
                             feedback: dict) -> dict | None:
        """
        Tenta extrair insights da resposta do LLM no chat e salvar
        como dado de treinamento para a rede neural aprender.
        Retorna dict de deltas extraídos ou None.
        """
        if not self.engine:
            return None
        try:
            import json
            # Tentar parsear JSON da resposta (o LLM pode responder
            # com ajustes mesmo em modo chat)
            json_str = None
            if "```json" in response_text:
                start = response_text.index("```json") + 7
                end = response_text.index("```", start)
                json_str = response_text[start:end].strip()
            elif '"adjustments"' in response_text and "{" in response_text:
                start = response_text.index("{")
                end = response_text.rindex("}") + 1
                json_str = response_text[start:end]

            if not json_str:
                return None

            data = json.loads(json_str)
            adjustments = data.get("adjustments", {})
            confidence = float(data.get("confidence", 0.5))

            if not adjustments or confidence < 0.4:
                return None

            # Pedir ao engine para aprender com esses ajustes
            if hasattr(self.engine, '_learn_from_llm_chat'):
                self.engine._learn_from_llm_chat(adjustments, confidence, feedback)

            # Converter adjustments para formato de deltas {delta_name: int}
            deltas = {}
            for key, val in adjustments.items():
                delta_key = key if key.startswith("delta_") else f"delta_{key}"
                try:
                    deltas[delta_key] = int(round(float(val)))
                except (ValueError, TypeError):
                    continue
            return deltas if deltas else None

        except (json.JSONDecodeError, ValueError, KeyError):
            return None  # Resposta não contém JSON — ok, era texto livre
        except Exception:
            return None

    def _get_telemetry_context(self) -> dict | None:
        """Coleta contexto de telemetria para enviar ao LLM."""
        if not self.engine:
            return None
        ctx = {}
        try:
            if hasattr(self.engine, "car_name"):
                ctx["car_name"] = self.engine.car_name
            if hasattr(self.engine, "track_name"):
                ctx["track_name"] = self.engine.track_name
            if hasattr(self.engine, "telemetry") and self.engine.telemetry:
                tele = self.engine.telemetry
                if hasattr(tele, "last_summary") and tele.last_summary:
                    s = tele.last_summary
                    ctx["grip_avg"] = getattr(s, "grip_avg", None)
                    ctx["last_lap_time"] = getattr(s, "lap_time", None)
                    ctx["temp_front"] = getattr(s, "temp_avg_front", None)
                    ctx["temp_rear"] = getattr(s, "temp_avg_rear", None)
                    ctx["rain"] = getattr(s, "rain", 0)
                    ctx["session_type"] = getattr(s, "session_type", "practice")
        except Exception:
            pass
        return ctx if ctx else None

    def _extract_feedback(self, text: str) -> dict:
        """Extrai informações de feedback do texto do usuário."""
        feedback = {"bias": 0.0, "entry": 0, "mid": 0, "exit": 0,
                    "confidence": 0.7}

        # Understeer / Oversteer
        if any(w in text for w in ("understeer", "subesterçar", "subesterça",
                                    "não vira", "empurra", "arrasta dianteira")):
            feedback["bias"] = -0.7
        elif any(w in text for w in ("oversteer", "sobreesterçar", "sobreesterça",
                                      "traseira sai", "roda", "escorrega traseira",
                                      "sai de traseira")):
            feedback["bias"] = 0.7

        # Zonas da curva
        if any(w in text for w in ("entrada", "frenagem", "freada", "freiar",
                                    "antes da curva")):
            feedback["entry"] = 1
        if any(w in text for w in ("meio", "ápice", "durante")):
            feedback["mid"] = 1
        if any(w in text for w in ("saída", "aceleração", "acelerando",
                                    "saindo")):
            feedback["exit"] = 1

        # Se nenhuma zona especificada, marcar "mid" como padrão
        if not any([feedback["entry"], feedback["mid"], feedback["exit"]]):
            feedback["mid"] = 1

        # Pneus
        if any(w in text for w in ("pneu", "pneus", "borracha", "desgaste",
                                    "temperatura", "superaquec", "frio")):
            feedback["confidence"] = 0.8

        # Freios
        if any(w in text for w in ("freio", "freia", "trava", "travar",
                                    "bloqueio")):
            feedback["confidence"] = 0.8

        # Tração
        if any(w in text for w in ("patina", "tração", "aderência",
                                    "grip", "escorreg")):
            feedback["confidence"] = 0.8

        # Clima
        if any(w in text for w in ("chuva", "molhad", "seco", "secando")):
            feedback["confidence"] = 0.6

        # Combustível / Energia
        if any(w in text for w in ("combustível", "combustivel", "gasolina",
                                    "fuel", "gastando", "consumo")):
            feedback["fuel_issue"] = True
            feedback["confidence"] = 0.7

        if any(w in text for w in ("bateria", "energia", "regen",
                                    "híbrido", "hibrido", "deploy")):
            feedback["energy_issue"] = True
            feedback["confidence"] = 0.7

        # Bottoming / rigidez
        if any(w in text for w in ("bottoming", "chão", "bate no chão",
                                    "raspando")):
            feedback["bottoming"] = True
            feedback["confidence"] = 0.8

        # Imprevisibilidade / confiança
        if any(w in text for w in ("imprevisível", "imprevisivel", "não confio",
                                    "inseguro", "confiar")):
            feedback["unpredictable"] = True
            feedback["confidence"] = 0.7

        # Direção pesada/lenta
        if any(w in text for w in ("direção pesada", "direção lenta",
                                    "direcao pesada", "volante pesado")):
            feedback["heavy_steering"] = True
            feedback["confidence"] = 0.7

        # Desgaste
        if any(w in text for w in ("desgaste rápido", "desgaste rapido",
                                    "pneu acabando", "pneu gastando")):
            feedback["tire_wear_high"] = True
            feedback["confidence"] = 0.8

        return feedback

    def _generate_response(self, text: str, feedback: dict,
                           has_base: bool) -> str:
        """Gera resposta contextual baseada no texto do usuário."""
        if not has_base:
            return (
                "📂 Você ainda não carregou um setup base.\n\n"
                "Por favor, clique em 'Carregar .svm' no painel à direita "
                "para selecionar seu arquivo de setup. Depois disso, posso "
                "sugerir ajustes específicos."
            )

        parts = []

        # Diagnóstico baseado no input
        if feedback["bias"] < -0.3:
            parts.append(
                "📋 **Diagnóstico**: Understeer detectado.\n"
                "O carro não responde bem à direção. Vou sugerir:\n"
                "• Reduzir asa dianteira ou aumentar traseira\n"
                "• Amaciar molas/ARB dianteiras\n"
                "• Verificar pressão e camber dianteiros"
            )
        elif feedback["bias"] > 0.3:
            parts.append(
                "📋 **Diagnóstico**: Oversteer detectado.\n"
                "A traseira do carro está escorregando. Vou sugerir:\n"
                "• Aumentar asa traseira\n"
                "• Endurecer ARB traseira ou amaciar dianteira\n"
                "• Verificar camber e pressões traseiros"
            )

        if feedback["entry"]:
            parts.append("📍 Problema na **entrada** da curva — vou focar em freios e aero.")
        if feedback["mid"]:
            parts.append("📍 Problema no **meio** da curva — vou focar em molas e ARB.")
        if feedback["exit"]:
            parts.append("📍 Problema na **saída** da curva — vou focar em tração e diferencial.")

        if any(w in text for w in ("chuva", "molhad")):
            parts.append(
                "🌧️ Condições de chuva detectadas. Vou considerar:\n"
                "• Aumento de ride height\n"
                "• Redução de asa (menos splash)\n"
                "• Pressões mais baixas para mais grip"
            )

        if any(w in text for w in ("pneu", "temperatura", "superaquec")):
            parts.append(
                "🏎️ Problema de pneus detectado. Vou verificar:\n"
                "• Pressões e camber para distribuição de temperatura\n"
                "• Carga aerodinâmica para desgaste"
            )

        if any(w in text for w in ("freio", "trava", "bloqueio")):
            parts.append(
                "🛑 Problema de frenagem detectado. Vou ajustar:\n"
                "• Bias de freio\n"
                "• Pressão de frenagem"
            )

        if not parts:
            parts.append(
                "Entendi sua solicitação. Vou analisar a telemetria atual "
                "e gerar sugestões de ajuste. Use os botões 'Pedir Sugestão IA' "
                "ou 'Usar Heurísticas' para receber as mudanças."
            )

        parts.append("\n🔧 Veja as sugestões no painel à direita →")
        return "\n\n".join(parts)

    def _auto_suggest(self, feedback: dict):
        """Tenta gerar sugestões automáticas baseadas no feedback."""
        if not self.engine:
            return

        try:
            if hasattr(self.engine, "request_heuristic_suggestion"):
                deltas, warnings = self.engine.request_heuristic_suggestion()
                self.display_suggestions(deltas, warnings)
        except Exception as e:
            logger.debug("Auto-sugestão falhou: %s", e)

    # ─── Setup Base ─────────────────────────────────────

    def _on_load_base(self):
        """Carrega um arquivo .svm como base."""
        initial_dir = None
        if self.engine and self.engine.lmu_path:
            settings_dir = (
                self.engine.lmu_path / "UserData" / "player" / "Settings"
            )
            if settings_dir.exists():
                initial_dir = str(settings_dir)

        filepath = filedialog.askopenfilename(
            title="Selecionar Setup Base (.svm)",
            initialdir=initial_dir,
            filetypes=[("Setup files", "*.svm"), ("Todos", "*.*")],
        )
        if not filepath:
            return

        try:
            if self.engine:
                svm = self.engine.load_base_setup(filepath)
                name = Path(filepath).name
                n_params = len(svm.get_adjustable_params()) if hasattr(svm, 'get_adjustable_params') else '?'
                self._base_info.configure(
                    text=f"📄 {name}\n"
                         f"📁 {Path(filepath).parent.name}\n"
                         f"🔧 {n_params} parâmetros ajustáveis",
                    text_color=COLORS["accent_green"],
                )
                self._add_message(
                    f"Setup base carregado: **{name}**\n"
                    f"Agora me diga o que você sente no carro, "
                    f"ou use os botões para gerar sugestões!",
                    sender="ai",
                )

                # Notificar app (para atualizar footer/menu)
                app = self.winfo_toplevel()
                if hasattr(app, "_on_base_loaded"):
                    app._on_base_loaded(filepath)

        except Exception as e:
            messagebox.showerror(
                "Erro ao Carregar",
                f"Não foi possível carregar o arquivo:\n{e}",
            )

    def _on_view_base(self):
        """Mostra detalhes do setup base."""
        if not self.engine or not hasattr(self.engine, "get_base_setup"):
            return
        svm = self.engine.get_base_setup()
        if not svm:
            self._add_message("Nenhum setup base carregado.", sender="system")
            return

        params = svm.get_adjustable_params()
        info = (
            f"Arquivo: {svm.filepath.name}\n"
            f"Diretório: {svm.filepath.parent}\n"
            f"Seções: {', '.join(svm.sections)}\n"
            f"Simétrico: {'Sim' if svm.symmetric else 'Não'}\n"
            f"Parâmetros ajustáveis: {len(params)}\n"
            f"{'─' * 45}\n"
        )
        for p in params:
            info += f"  [{p.section}] {p.name} = {p.index} // {p.description}\n"

        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title(f"Setup Base — {svm.filepath.name}")
        win.geometry("650x500")
        txt = ctk.CTkTextbox(win, font=("Consolas", 11))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("end", info)
        txt.configure(state="disabled")

    def _on_clear_base(self):
        """Limpa o setup base."""
        if self.engine and hasattr(self.engine, "clear_base_setup"):
            self.engine.clear_base_setup()
        self._base_info.configure(
            text="Nenhum setup carregado",
            text_color=COLORS["text_secondary"],
        )
        self._add_message("Setup base removido.", sender="system")

        app = self.winfo_toplevel()
        if hasattr(app, "_on_base_cleared"):
            app._on_base_cleared()

    # ─── Ações ──────────────────────────────────────────

    def _on_create_setup(self):
        """Abre diálogo de criação de novo setup."""
        if not self.engine or not hasattr(self.engine, "get_base_setup"):
            self._add_message(
                "Carregue um setup base primeiro.", sender="system",
            )
            return

        base = self.engine.get_base_setup()
        if not base:
            self._add_message(
                "📂 Carregue um setup base primeiro usando o botão "
                "'Carregar .svm'.",
                sender="ai",
            )
            return

        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("✨ Criar Novo Setup")
        win.geometry("500x420")
        win.grab_set()

        # Modo
        ctk.CTkLabel(
            win, text="Modo de Criação:",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        mode_var = ctk.StringVar(value="ia")
        for label, val in [
            ("🤖 IA + Heurísticas (recomendado)", "ia"),
            ("📐 Apenas Heurísticas", "heuristic"),
            ("📋 Cópia exata (sem mudanças)", "copy"),
        ]:
            ctk.CTkRadioButton(
                win, text=label, variable=mode_var, value=val,
            ).pack(anchor="w", padx=30)

        # Clima
        ctk.CTkLabel(
            win, text="Condição Climática:",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        climate_var = ctk.StringVar(value="seco")
        for label, val in [
            ("☀️ Seco", "seco"),
            ("🌦️ Chuva Leve", "chuva_leve"),
            ("🌧️ Chuva Forte", "chuva_forte"),
            ("💧 Misto (secando)", "misto"),
            ("🔄 Mesclado (50/50)", "mescla"),
        ]:
            ctk.CTkRadioButton(
                win, text=label, variable=climate_var, value=val,
            ).pack(anchor="w", padx=30)

        ctk.CTkLabel(
            win,
            text=f"Base: {base.filepath.name}\n"
                 f"O arquivo base NÃO será modificado.\n"
                 f"Um NOVO arquivo será criado na mesma pasta.",
            font=("Arial", 11), text_color=COLORS["text_secondary"],
            justify="left",
        ).pack(anchor="w", padx=15, pady=(15, 5))

        def _do_create():
            mode = mode_var.get()
            climate = climate_var.get()
            try:
                new_path = self.engine.create_setup_from_base(
                    mode=mode, climate=climate
                )
                win.destroy()
                self._add_message(
                    f"✅ Novo setup criado: **{new_path.name}**\n"
                    f"📁 Salvo em: {new_path.parent}",
                    sender="ai",
                )
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar setup:\n{e}")

        ctk.CTkButton(
            win, text="✨ Criar Novo Setup", command=_do_create,
            fg_color=COLORS["accent_green"], hover_color="#009955",
            height=38, font=("Arial", 12, "bold"),
        ).pack(pady=15)

    def _on_edit_setup(self):
        """Edita um .svm existente."""
        initial_dir = None
        if self.engine and self.engine.lmu_path:
            settings_dir = (
                self.engine.lmu_path / "UserData" / "player" / "Settings"
            )
            if settings_dir.exists():
                initial_dir = str(settings_dir)

        filepath = filedialog.askopenfilename(
            title="Selecionar Setup para Editar (.svm)",
            initialdir=initial_dir,
            filetypes=[("Setup files", "*.svm"), ("Todos", "*.*")],
        )
        if not filepath:
            return

        confirm = messagebox.askyesno(
            "Confirmar Edição",
            f"Arquivo: {Path(filepath).name}\n\n"
            f"Um backup (.svm.bak) será criado.\nDeseja continuar?",
        )
        if not confirm:
            return

        try:
            if self.engine:
                self.engine.load_setup(filepath)
                self._add_message(
                    f"✏️ Editando: **{Path(filepath).name}**\n"
                    f"Backup criado automaticamente.\n"
                    f"Use 'Pedir Sugestão IA' para receber ajustes.",
                    sender="ai",
                )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir setup:\n{e}")

    def _on_request_ai(self):
        """Pede sugestão da IA em background thread."""
        if not self.engine or not hasattr(self.engine, "request_suggestion"):
            self._add_message("Engine não disponível.", sender="system")
            return

        self._add_message("⏳ Pedindo sugestão da IA...", sender="system")
        self._btn_send.configure(state="disabled")

        def _work():
            try:
                deltas, warnings = self.engine.request_suggestion()
                display_deltas = getattr(self.engine, '_last_display_deltas', {})
                self.after(0, lambda: self._finish_suggestion(
                    display_deltas, warnings, "🧠 Sugestões da IA geradas! "
                    "Veja o painel à direita.\nClique em 'Aplicar Ajustes' "
                    "quando estiver satisfeito."))
            except Exception as e:
                self.after(0, lambda: self._add_message(f"Erro: {e}", sender="system"))
            finally:
                self.after(0, lambda: self._btn_send.configure(state="normal"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_request_heuristics(self):
        """Pede sugestão das heurísticas em background thread."""
        if not self.engine or not hasattr(self.engine, "request_heuristic_suggestion"):
            self._add_message("Engine não disponível.", sender="system")
            return

        self._add_message("⏳ Calculando heurísticas...", sender="system")
        self._btn_send.configure(state="disabled")

        def _work():
            try:
                deltas, warnings = self.engine.request_heuristic_suggestion()
                display_deltas = getattr(self.engine, '_last_display_deltas', {})
                self.after(0, lambda: self._finish_suggestion(
                    display_deltas, warnings, "📐 Sugestões heurísticas geradas! "
                    "Veja o painel à direita.\nSão baseadas em regras de "
                    "engenharia veicular."))
            except Exception as e:
                self.after(0, lambda: self._add_message(f"Erro: {e}", sender="system"))
            finally:
                self.after(0, lambda: self._btn_send.configure(state="normal"))

        threading.Thread(target=_work, daemon=True).start()

    def _finish_suggestion(self, display_deltas, warnings, msg):
        """Callback na main thread após sugestão calculada."""
        self.display_suggestions(display_deltas, warnings)
        self._add_message(msg, sender="ai")

    def _on_apply(self):
        """Aplica as sugestões — pergunta qual arquivo usar como destino."""
        if not self.engine or not hasattr(self.engine, "apply_suggestions"):
            return
        if not self.engine._last_deltas:
            self._add_message("Nenhuma sugestão para aplicar.", sender="system")
            return

        base = self.engine.get_base_setup() if hasattr(self.engine, 'get_base_setup') else None

        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("📝 Aplicar Mudanças — Escolher Destino")
        win.geometry("550x520")
        win.minsize(550, 400)
        win.grab_set()

        # --- Frame de botões fixo no rodapé (pack PRIMEIRO = sempre visível) ---
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=15, pady=(5, 15))

        mode_var = ctk.StringVar(value="edit_base")
        use_as_base_var = ctk.BooleanVar(value=True)

        def _do_apply():
            mode = mode_var.get()
            use_as_base = use_as_base_var.get()

            try:
                if mode == "edit_base":
                    if not base:
                        messagebox.showerror("Erro", "Nenhum setup base carregado.")
                        return
                    from data.svm_parser import parse_svm, apply_deltas, save_svm
                    svm = parse_svm(str(base.filepath))
                    apply_deltas(svm, self.engine._last_deltas)
                    save_svm(svm, backup_dir=str(self.engine.config.get(
                        "backup_dir", Path(base.filepath).parent / "backups"
                    )))
                    win.destroy()
                    self._btn_apply.configure(state="disabled")
                    self._add_message(
                        f"✅ Mudanças aplicadas em: **{base.filepath.name}**\n"
                        f"📂 Backup criado automaticamente.\n"
                        f"Volte para a pista e me diga como ficou!",
                        sender="ai",
                    )
                    if use_as_base:
                        self.engine.load_base_setup(str(base.filepath))
                        self._update_base_info(base.filepath)

                elif mode == "new_file":
                    if not base:
                        messagebox.showerror("Erro", "Nenhum setup base carregado para usar de referência.")
                        return
                    from data.svm_parser import parse_svm, apply_deltas, save_svm
                    svm = parse_svm(str(base.filepath))
                    apply_deltas(svm, self.engine._last_deltas)
                    new_path = self.engine._generate_setorflow_path("ajustado")
                    save_svm(svm, output_path=new_path, backup=False)
                    win.destroy()
                    self._btn_apply.configure(state="disabled")
                    self._add_message(
                        f"✅ Novo setup criado: **{new_path.name}**\n"
                        f"📁 Salvo em: {new_path.parent}\n"
                        f"O arquivo base original NÃO foi alterado.",
                        sender="ai",
                    )
                    if use_as_base:
                        self.engine.load_base_setup(str(new_path))
                        self._update_base_info(new_path)

                elif mode == "choose_other":
                    initial_dir = None
                    if self.engine and self.engine.lmu_path:
                        settings_dir = (
                            self.engine.lmu_path / "UserData" / "player" / "Settings"
                        )
                        if settings_dir.exists():
                            initial_dir = str(settings_dir)

                    filepath = filedialog.askopenfilename(
                        title="Escolher arquivo .svm para aplicar mudanças",
                        initialdir=initial_dir,
                        filetypes=[("Setup files", "*.svm"), ("Todos", "*.*")],
                    )
                    if not filepath:
                        return

                    from data.svm_parser import parse_svm, apply_deltas, save_svm
                    svm = parse_svm(filepath)
                    apply_deltas(svm, self.engine._last_deltas)
                    save_svm(svm, backup_dir=str(
                        Path(filepath).parent / "backups"
                    ))
                    win.destroy()
                    self._btn_apply.configure(state="disabled")
                    self._add_message(
                        f"✅ Mudanças aplicadas em: **{Path(filepath).name}**\n"
                        f"📂 Backup criado automaticamente.",
                        sender="ai",
                    )
                    if use_as_base:
                        self.engine.load_base_setup(filepath)
                        self._update_base_info(Path(filepath))

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao aplicar mudanças:\n{e}")

        ctk.CTkButton(
            btn_frame, text="✅ Aplicar Mudanças", command=_do_apply,
            fg_color=COLORS["accent_green"], hover_color="#009955",
            height=42, font=("Arial", 13, "bold"),
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            btn_frame, text="Cancelar", command=win.destroy,
            fg_color="#555555", hover_color="#444444",
            height=32, font=("Arial", 11),
        ).pack(fill="x")

        # --- Conteúdo rolável acima dos botões ---
        content_scroll = ctk.CTkScrollableFrame(
            win, fg_color="transparent",
        )
        content_scroll.pack(side="top", fill="both", expand=True, padx=5, pady=(5, 0))

        ctk.CTkLabel(
            content_scroll, text="Onde aplicar as mudanças?",
            font=("Arial", 15, "bold"),
            text_color=COLORS["accent_blue"],
        ).pack(anchor="w", padx=10, pady=(10, 10))

        # Opção 1: Editar o arquivo base carregado
        base_name = base.filepath.name if base else "Nenhum carregado"
        r1 = ctk.CTkRadioButton(
            content_scroll,
            text=f"✏️ Editar arquivo base atual: {base_name}",
            variable=mode_var, value="edit_base",
            font=("Arial", 12),
        )
        r1.pack(anchor="w", padx=25, pady=3)
        if not base:
            r1.configure(state="disabled")

        ctk.CTkLabel(
            content_scroll,
            text="     O arquivo base será modificado (backup automático criado).",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=25)

        # Opção 2: Criar novo arquivo com as mudanças
        ctk.CTkRadioButton(
            content_scroll,
            text="✨ Criar NOVO arquivo com as mudanças",
            variable=mode_var, value="new_file",
            font=("Arial", 12),
        ).pack(anchor="w", padx=25, pady=(10, 3))

        ctk.CTkLabel(
            content_scroll,
            text="     Um novo .svm será criado, o arquivo base NÃO muda.",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=25)

        # Opção 3: Escolher outro arquivo
        ctk.CTkRadioButton(
            content_scroll,
            text="📂 Escolher OUTRO arquivo .svm para editar",
            variable=mode_var, value="choose_other",
            font=("Arial", 12),
        ).pack(anchor="w", padx=25, pady=(10, 3))

        ctk.CTkLabel(
            content_scroll,
            text="     Selecione um arquivo diferente para aplicar as mudanças.",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=25)

        # Separador
        ctk.CTkFrame(content_scroll, height=2, fg_color=COLORS["separator"]).pack(
            fill="x", padx=10, pady=15
        )

        # Checkbox: usar o arquivo escolhido como nova base
        ctk.CTkCheckBox(
            content_scroll,
            text="🔄 Após aplicar, usar o arquivo resultante como nova base de referência",
            variable=use_as_base_var,
            font=("Arial", 11),
        ).pack(anchor="w", padx=25, pady=(0, 5))

        # Checkbox: manter/pagar o arquivo base atual
        keep_base_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            content_scroll,
            text="📄 Manter o arquivo base original (não apagar)",
            variable=keep_base_var,
            font=("Arial", 11),
        ).pack(anchor="w", padx=25, pady=(0, 15))

        # Preview das mudanças
        if self.engine._last_display_deltas:
            preview_card = Card(content_scroll, title="📋 Resumo das Mudanças")
            preview_card.pack(fill="x", padx=10, pady=(0, 10))

            preview_inner = ctk.CTkFrame(
                preview_card, fg_color="transparent",
            )
            preview_inner.pack(fill="x", padx=10, pady=(0, 8))

            from core.brain import DELTA_TO_SVM
            for delta_name, delta_val in self.engine._last_display_deltas.items():
                if delta_val == 0:
                    continue
                svm_keys = DELTA_TO_SVM.get(delta_name, [delta_name])
                arrow = "▲" if delta_val > 0 else "▼"
                color = COLORS["accent_green"] if delta_val > 0 else COLORS["accent_red"]

                # Mostrar valor atual se base carregado
                current_str = ""
                if base:
                    for sk in svm_keys:
                        param = base.get_param(sk)
                        if param and param.adjustable:
                            new_idx = max(0, param.index + delta_val)
                            current_str = f"  [{param.index}] → [{new_idx}]"
                            break

                ctk.CTkLabel(
                    preview_inner,
                    text=f"  {arrow} {delta_name}: {delta_val:+d}{current_str}",
                    font=("JetBrains Mono", 10),
                    text_color=color,
                    anchor="w",
                ).pack(anchor="w")

    def _update_base_info(self, filepath):
        """Atualiza o label de info do setup base."""
        svm = self.engine.get_base_setup()
        if svm:
            n_params = len(svm.get_adjustable_params())
            self._base_info.configure(
                text=f"📄 {filepath.name if hasattr(filepath, 'name') else Path(filepath).name}\n"
                     f"📁 {filepath.parent if hasattr(filepath, 'parent') else Path(filepath).parent.name}\n"
                     f"🔧 {n_params} parâmetros ajustáveis",
                text_color=COLORS["accent_green"],
            )

    def _on_rate(self, score: float):
        """Avalia o resultado da última sugestão."""
        if not self.engine or not hasattr(self.engine, "rate_last_suggestion"):
            return
        self.engine.rate_last_suggestion(score)

        labels = {1.0: "👍 Melhorou", 0.0: "😐 Igual", -1.0: "👎 Piorou"}
        self._add_message(
            f"Avaliação registrada: {labels.get(score, '?')}\n"
            f"Isso ajuda a IA a aprender suas preferências!",
            sender="system",
        )

    # ─── Display ────────────────────────────────────────

    def _update_param_visibility(self):
        """Mostra/esconde seções de parâmetros conforme nível da IA."""
        _LEVEL_ORDER = {"basic": 0, "intermediate": 1, "advanced": 2}
        current = _LEVEL_ORDER.get(self._current_display_level, 0)
        for frame, level in self._section_frames:
            frame.pack_forget()
        for frame, level in self._section_frames:
            if _LEVEL_ORDER.get(level, 0) <= current:
                frame.pack(fill="x")

    def display_suggestions(self, deltas: dict[str, int],
                            warnings: list[str] | None = None):
        """Atualiza o display de sugestões com valores atuais → novos."""
        # Obter índices atuais do setup base para mostrar valor atual → novo
        current_indices = {}
        if self.engine and hasattr(self.engine, 'get_base_setup'):
            base_svm = self.engine.get_base_setup()
            if base_svm:
                from core.brain import DELTA_TO_SVM
                for delta_name, svm_keys in DELTA_TO_SVM.items():
                    for svm_key in svm_keys:
                        param = base_svm.get_param(svm_key)
                        if param and param.adjustable:
                            current_indices[delta_name] = (param.index, param.description)
                            break  # Pegar apenas o primeiro (FL para F/R)

        for key, widget in self._delta_widgets.items():
            delta = deltas.get(key, 0)
            idx_info = current_indices.get(key)
            if idx_info:
                widget.set_delta(delta, current_index=idx_info[0],
                                 current_desc=idx_info[1])
            else:
                widget.set_delta(delta)

        has = any(v != 0 for v in deltas.values())
        self._btn_apply.configure(state="normal" if has else "disabled")

        self._warnings_text.configure(state="normal")
        self._warnings_text.delete("1.0", "end")
        self._warnings_text.insert(
            "end", "\n".join(warnings) if warnings else "Nenhum aviso.",
        )
        self._warnings_text.configure(state="disabled")

    def refresh(self):
        """Atualiza dados dinâmicos e sugestões em tempo real."""
        if not self.engine:
            return
        if hasattr(self.engine, "ai_confidence") and hasattr(self.engine, "total_samples"):
            self._confidence.set_confidence(
                self.engine.ai_confidence(), self.engine.total_samples()
            )
        # Atualizar indicador de nível e visibilidade das seções
        if hasattr(self.engine, "_current_level"):
            level = self.engine._current_level
            level_upper = level.upper()
            level_colors = {
                "BASIC": COLORS["accent_yellow"],
                "INTERMEDIATE": COLORS["accent_cyan"],
                "ADVANCED": COLORS["accent_green"],
            }
            self._level_label.configure(
                text=level_upper,
                text_color=level_colors.get(level_upper, COLORS["text_secondary"]),
            )
            # Expandir seções visíveis quando IA sobe de nível
            if level != self._current_display_level:
                self._current_display_level = level
                self._update_param_visibility()

        # Atualizar deltas em tempo real a partir da última sugestão
        display_deltas = getattr(self.engine, '_last_display_deltas', None)
        if display_deltas:
            # Obter índices atuais para exibição
            current_indices = {}
            base_svm = self.engine.get_base_setup() if hasattr(self.engine, 'get_base_setup') else None
            if base_svm:
                from core.brain import DELTA_TO_SVM
                for delta_name, svm_keys in DELTA_TO_SVM.items():
                    for svm_key in svm_keys:
                        param = base_svm.get_param(svm_key)
                        if param and param.adjustable:
                            current_indices[delta_name] = param.index
                            break
            for key, widget in self._delta_widgets.items():
                delta = display_deltas.get(key, 0)
                idx = current_indices.get(key)
                widget.set_delta(delta, current_index=idx)

    # ─── Auto-suggest callbacks ─────────────────────────

    def _on_toggle_auto_suggest(self):
        """Habilita/desabilita auto-sugestão."""
        if self.engine and hasattr(self.engine, "set_auto_suggest_enabled"):
            enabled = self._auto_toggle.get() == 1
            self.engine.set_auto_suggest_enabled(enabled)
            state = "habilitada" if enabled else "desabilitada"
            self._add_message(
                f"🤖 IA autônoma **{state}**.",
                sender="system",
            )

    def _on_change_interval(self, value: str):
        """Muda o intervalo de auto-sugestão."""
        if self.engine and hasattr(self.engine, "set_auto_suggest_interval"):
            self.engine.set_auto_suggest_interval(int(value))
            self._add_message(
                f"🤖 Auto-sugestão agora a cada **{value}** voltas.",
                sender="system",
            )

    # ─── API Key / LLM ─────────────────────────────────

    def _toggle_api_key_visibility(self):
        """Mostra/esconde a API key no campo."""
        current = self._api_key_entry.cget("show")
        if current == "•":
            self._api_key_entry.configure(show="")
            self._api_show_btn.configure(text="🔒")
        else:
            self._api_key_entry.configure(show="•")
            self._api_show_btn.configure(text="👁")

    def _toggle_api_key_visibility(self):
        """Mostra/esconde a API key no campo."""
        current = self._api_key_entry.cget("show")
        if current == "•":
            self._api_key_entry.configure(show="")
            self._api_show_btn.configure(text="🔒")
        else:
            self._api_key_entry.configure(show="•")
            self._api_show_btn.configure(text="👁")

    # ─── Destilação de Conhecimento ─────────────────────

    def _on_start_distillation(self):
        """Inicia o processo de destilação do LLM → rede neural."""
        if not self.engine:
            return

        # Verificar se API está configurada
        key = self._api_key_entry.get().strip()
        if not key:
            messagebox.showwarning(
                "API necessária",
                "Configure a API key primeiro.\n"
                "A destilação usa a API como professor "
                "para treinar a rede neural.",
            )
            return

        # Verificar se já está rodando
        if (hasattr(self.engine, 'distiller')
                and self.engine.distiller.progress.is_running):
            messagebox.showinfo(
                "Em andamento",
                "A destilação já está em andamento.",
            )
            return

        # Confirmar com o usuário
        car_class = ""
        if hasattr(self.engine, '_car_class'):
            car_class = self.engine._car_class
        if not car_class:
            car_class = "hypercar"

        ok = messagebox.askyesno(
            "Destilar Conhecimento",
            f"Isso vai gerar 60 cenários para '{car_class}' "
            f"e consultar a API para cada um.\n\n"
            f"A rede neural vai APRENDER com cada resposta "
            f"do LLM, ficando mais autônoma.\n\n"
            f"Isso usa ~60 chamadas à API (pode levar "
            f"alguns minutos).\n\nContinuar?",
        )
        if not ok:
            return

        self._distill_btn.configure(
            state="disabled",
            text="⏳ Destilando...",
        )
        self._distill_status.configure(
            text="Iniciando destilação...",
        )

        # Iniciar destilação em background
        self.engine.start_knowledge_distillation(
            car_class=car_class,
            n_scenarios=60,
            callback=self._on_distill_progress,
        )

    def _on_distill_progress(self, progress):
        """
        Callback chamado a cada cenário da destilação.
        Atualiza a barra de progresso e status na GUI.
        """
        def _update():
            try:
                # Barra de progresso
                if progress.total_scenarios > 0:
                    pct = (
                        progress.completed
                        / progress.total_scenarios
                    )
                    self._autonomy_bar.set(pct)

                # Status
                self._distill_status.configure(
                    text=progress.message,
                )

                # Quando terminar
                if progress.phase in ("done", "error"):
                    self._distill_btn.configure(
                        state="normal",
                        text="🧠 Destilar Conhecimento do LLM",
                    )
                    self._update_autonomy_display()

                    if progress.phase == "done":
                        self._add_message(
                            f"🎓 **Destilação concluída!**\n\n"
                            f"{progress.message}\n\n"
                            f"A rede neural incorporou o "
                            f"conhecimento do LLM.",
                            is_user=False,
                        )
            except Exception:
                pass

        self.after(0, _update)

    def _update_autonomy_display(self):
        """Atualiza a exibição de autonomia com dados salvos."""
        if not self.engine or not hasattr(
                self.engine, 'distiller'):
            return

        try:
            status = self.engine.get_autonomy_status()
            score = status["score"]

            self._autonomy_bar.set(score)
            self._autonomy_label.configure(
                text=status["status_text"],
            )

            # Cor da barra pelo nível
            if score >= 0.90:
                self._autonomy_bar.configure(
                    progress_color=COLORS["accent_green"],
                )
            elif score >= 0.70:
                self._autonomy_bar.configure(
                    progress_color="#FFA500",
                )
            elif score >= 0.40:
                self._autonomy_bar.configure(
                    progress_color=COLORS["accent_blue"],
                )
            else:
                self._autonomy_bar.configure(
                    progress_color=COLORS["text_secondary"],
                )
        except Exception:
            pass

    def _on_save_api_key(self):
        """Salva a API key, provedor e modelo nas configurações."""
        key = self._api_key_entry.get().strip()
        provider = self._llm_provider_var.get()
        custom_url = self._custom_url_entry.get().strip()

        # Modelo: usar custom entry se provedor é custom ou lmstudio, senão dropdown
        if provider in ("custom", "lmstudio"):
            model = self._custom_model_entry.get().strip()
            if not model:
                model = self._llm_model_var.get()
        else:
            model = self._llm_model_var.get()

        if self.engine and hasattr(self.engine, "config"):
            self.engine.config.set("openrouter_api_key", key)
            self.engine.config.set("openrouter_model", model)
            self.engine.config.set("llm_provider", provider)
            self.engine.config.set("llm_custom_url", custom_url)

        if self.engine and hasattr(self.engine, "llm_advisor"):
            self.engine.llm_advisor.set_api_key(key)
            self.engine.llm_advisor.set_model(model)
            self.engine.llm_advisor.set_provider(provider, custom_url)

        from core.llm_advisor import API_PROVIDERS
        prov_name = API_PROVIDERS.get(
            provider, {}
        ).get("name", provider)

        if key:
            self._llm_status.configure(
                text=f"🟢 {prov_name} configurado",
                text_color=COLORS["accent_green"],
            )
            self._add_message(
                f"🤖 LLM configurado: **{prov_name}** / "
                f"**{model.split('/')[-1]}**\n"
                "Agora suas perguntas serão respondidas "
                "pela IA avançada!",
                sender="system",
            )
        else:
            self._llm_status.configure(
                text="⚪ Não configurado",
                text_color=COLORS["text_secondary"],
            )
            self._add_message(
                "🤖 LLM desativado. O chat voltará a usar "
                "respostas locais.",
                sender="system",
            )

    def _on_provider_changed(self, provider: str):
        """Atualiza modelos e campos quando o provedor muda."""
        from core.llm_advisor import API_PROVIDERS

        prov_info = API_PROVIDERS.get(
            provider, API_PROVIDERS["openrouter"]
        )

        # Mostrar/esconder campo de URL custom
        if provider in ("custom", "lmstudio"):
            self._custom_url_frame.pack(
                fill="x", padx=14, pady=(0, 4),
                after=self._llm_provider_menu,
            )
            self._custom_model_frame.pack(
                fill="x", padx=14, pady=(0, 4),
                after=self._llm_model_menu,
            )
            # Preencher URL padrão do LM Studio se estiver vazio
            if provider == "lmstudio":
                current_url = self._custom_url_entry.get().strip()
                if not current_url:
                    self._custom_url_entry.insert(
                        0, "http://localhost:1234/v1/chat/completions"
                    )
        else:
            self._custom_url_frame.pack_forget()
            self._custom_model_frame.pack_forget()

        # Atualizar dropdown de modelos
        models = prov_info["models"]
        if models:
            self._llm_model_menu.configure(values=models)
            self._llm_model_var.set(prov_info["default_model"])
        else:
            self._llm_model_menu.configure(
                values=["(digite no campo abaixo)"]
            )
            self._llm_model_var.set("(digite no campo abaixo)")

        # Atualizar placeholder do API key
        prefix = prov_info.get("key_prefix", "")
        if provider == "lmstudio":
            self._api_key_entry.configure(
                placeholder_text="opcional (LM Studio local)"
            )
        elif prefix:
            self._api_key_entry.configure(
                placeholder_text=f"{prefix}..."
            )
        else:
            self._api_key_entry.configure(
                placeholder_text="cole sua API key aqui..."
            )

        # Auto-detectar provedor se a key já está preenchida
        key = self._api_key_entry.get().strip()
        if key:
            self._llm_status.configure(
                text=f"⚡ Provedor: {prov_info['name']}",
                text_color=COLORS["accent_cyan"],
            )

    def _on_test_api(self):
        """Testa a conexão com a API do provedor selecionado."""
        key = self._api_key_entry.get().strip()
        provider = self._llm_provider_var.get()
        if not key and provider != "lmstudio":
            self._llm_status.configure(
                text="❌ Insira uma API key primeiro",
                text_color=COLORS["accent_red"],
            )
            return

        self._llm_status.configure(
            text="⏳ Testando...",
            text_color=COLORS["accent_cyan"],
        )
        model = self._llm_model_var.get()
        custom_url = self._custom_url_entry.get().strip()

        if provider in ("custom", "lmstudio"):
            custom_model = self._custom_model_entry.get().strip()
            if custom_model:
                model = custom_model

        from core.llm_advisor import LLMAdvisor
        test_advisor = LLMAdvisor(
            api_key=key, model=model,
            provider=provider, custom_url=custom_url,
        )

        def _on_result(success: bool, message: str):
            self.after(0, self._handle_test_result, success, message)

        test_advisor.test_connection(callback=_on_result)

    def _handle_test_result(self, success: bool, message: str):
        """Processa resultado do teste de conexão."""
        if success:
            self._llm_status.configure(
                text="🟢 " + message.replace("✅ ", ""),
                text_color=COLORS["accent_green"],
            )
            self._add_message(
                f"✅ Conexão com LLM OK!\n{message}",
                sender="system",
            )
        else:
            self._llm_status.configure(
                text="🔴 Falha na conexão",
                text_color=COLORS["accent_red"],
            )
            self._add_message(
                f"❌ Teste falhou: {message}",
                sender="system",
            )

    # ─── Pré-carga de conhecimento ─────────────────────

    def _on_seed_knowledge(self):
        """Carrega a base de conhecimento inicial na IA."""
        if not self.engine:
            return

        # Verificar se já tem regras seed
        stats = self.engine.get_knowledge_stats()
        if stats.get("seed_rules", 0) > 0:
            confirm = messagebox.askyesno(
                "Base já carregada",
                f"A base de conhecimento já tem {stats['seed_rules']} regras seed.\n"
                "Deseja recarregar? (regras existentes serão atualizadas)",
            )
            if not confirm:
                return

        self._add_message(
            "⏳ Carregando base de conhecimento inicial...\n"
            "Isso vai dar à IA uma base sobre como ajustar setups "
            "de GT3, LMP2 e Hypercar.",
            sender="system",
        )

        # Executar seed
        result = self.engine.seed_knowledge_base()
        added = result.get("rules_added", 0)
        skipped = result.get("rules_skipped", 0)

        self._add_message(
            f"✅ **Base de conhecimento carregada!**\n\n"
            f"📝 **{added}** regras adicionadas\n"
            f"⏭️ **{skipped}** regras já existentes (atualizadas)\n\n"
            f"A IA agora sabe como reagir a:\n"
            f"• Understeer/Oversteer → ajustes de barras e asa\n"
            f"• Temperatura dos pneus → camber e pressão\n"
            f"• Bottoming → ride height e molas\n"
            f"• Chuva → molas macias + mais asa + altura\n"
            f"• Zebras → fast bump mais suave\n"
            f"• Frenagem → bias e dutos de freio\n\n"
            f"Regras específicas para GT3, LMP2 e Hypercar incluídas.\n"
            f"Quanto mais voltas você der, mais ela aprende sobre **seu estilo**!",
            sender="ai",
        )

    def _on_show_stats(self):
        """Mostra estatísticas atuais da IA no chat."""
        if not self.engine:
            return

        stats = self.engine.get_knowledge_stats()
        conf = stats["confidence"]

        # Barra visual de confiança
        filled = int(conf * 10)
        bar = "█" * filled + "░" * (10 - filled)

        self._add_message(
            f"📊 **Estatísticas da IA**\n\n"
            f"🧠 Regras aprendidas: **{stats['total_rules']}**\n"
            f"📝 Regras seedadas: **{stats['seed_rules']}**\n"
            f"✅ Regras efetivas (>60%): **{stats['effective_rules']}**\n"
            f"📦 Amostras de treino: **{stats['total_samples']}**\n"
            f"🏎️ Classes cobertas: **{stats['classes_covered']}**\n"
            f"📈 Confiança: [{bar}] **{conf*100:.0f}%**",
            sender="ai",
        )

    def _on_learn_from_setups(self):
        """Escaneia todos os .svm disponíveis para aprendizagem."""
        if not self.engine:
            return

        self._add_message("📂 Escaneando todos os setups disponíveis...", sender="system")

        try:
            result = self.engine.learn_from_all_setups()
            self._add_message(
                f"✅ **Biblioteca de setups atualizada!**\n\n"
                f"📁 Pistas encontradas: **{result['tracks']}**\n"
                f"📄 Setups escaneados: **{result['scanned']}**\n"
                f"🆕 Setups processados: **{result['new']}**\n\n"
                f"A IA agora pode comparar setups e aprender padrões "
                f"para cada pista. Ao entrar na pista, os setups "
                f"disponíveis serão usados como referência.",
                sender="ai",
            )
        except Exception as e:
            self._add_message(f"Erro ao escanear setups: {e}", sender="system")

    def _on_show_memory(self):
        """Mostra a memória persistente do carro×pista atual."""
        if not self.engine:
            return

        summary = self.engine.get_knowledge_summary()

        msg = f"🧠 **Memória Persistente da IA**\n\n"
        msg += f"📂 Setups na biblioteca: **{summary['library_setups']}**\n"
        msg += f"📦 Amostras de treino: **{summary['total_samples']}**\n\n"

        mem = summary.get("active_memory")
        if mem:
            msg += f"**Carro × Pista atual:**\n"
            msg += f"  📊 Sessões anteriores: **{mem['sessions']}**\n"
            msg += f"  🏁 Voltas registradas: **{mem['laps']}**\n"
            if mem.get("best_lap"):
                msg += f"  🏆 Melhor volta: **{mem['best_lap']:.3f}s**\n"
            conf = mem.get("confidence", 0)
            filled = int(conf * 10)
            bar = "█" * filled + "░" * (10 - filled)
            msg += f"  📈 Confiança memória: [{bar}] **{conf*100:.0f}%**\n"
        else:
            msg += "ℹ️ Nenhuma memória para o carro × pista atual.\n"
            msg += "Entre na pista e complete voltas para a IA começar a lembrar."

        self._add_message(msg, sender="ai")
