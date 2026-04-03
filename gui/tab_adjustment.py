"""
tab_adjustment.py — Aba de Feedback Detalhado.

Feedback avançado do piloto: sliders de balanço, zonas de curva,
sensações do carro e visualização avançada de deltas.
A aba de Setup agora cuida das sugestões/ações — esta aba foca
na comunicação detalhada entre piloto e IA.
"""

from __future__ import annotations

import logging

import customtkinter as ctk

from gui.widgets import (
    Card,
    FeedbackSlider,
    COLORS,
)

logger = logging.getLogger("LMU_VE.gui.adjustment")


class AdjustmentTab(ctk.CTkFrame):
    """Aba de feedback detalhado do piloto."""

    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Layout em duas colunas
        cols = ctk.CTkFrame(scroll, fg_color="transparent")
        cols.pack(fill="both", expand=True)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # ═══ COLUNA ESQUERDA ═══════════════════════════════

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # ─── Balanço do Carro ─────────────────
        bal_card = Card(left, title="🔄 Balanço do Carro")
        bal_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            bal_card, text="Como o carro se comporta nas curvas?",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=14, pady=(0, 5))

        self._fb_bias = FeedbackSlider(
            bal_card, label="Balanço Geral",
            left_text="◀ Understeer", right_text="Oversteer ▶",
        )
        self._fb_bias.pack(fill="x", padx=14, pady=3)

        self._fb_low_speed = FeedbackSlider(
            bal_card, label="Curvas Lentas",
            left_text="◀ Sub", right_text="Sobre ▶",
        )
        self._fb_low_speed.pack(fill="x", padx=14, pady=3)

        self._fb_high_speed = FeedbackSlider(
            bal_card, label="Curvas Rápidas",
            left_text="◀ Sub", right_text="Sobre ▶",
        )
        self._fb_high_speed.pack(fill="x", padx=14, pady=(3, 12))

        # ─── Zona do Problema ─────────────────
        zone_card = Card(left, title="📍 Zona do Problema na Curva")
        zone_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            zone_card, text="Onde o problema acontece?",
            font=("Arial", 10), text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=14, pady=(0, 5))

        zones = ctk.CTkFrame(zone_card, fg_color="transparent")
        zones.pack(fill="x", padx=14, pady=(0, 10))
        zones.columnconfigure((0, 1, 2), weight=1)

        self._cb_entry = ctk.CTkCheckBox(
            zones, text="🔴 Entrada\n(frenagem)",
            font=("Arial", 10), checkbox_width=20, checkbox_height=20,
        )
        self._cb_entry.grid(row=0, column=0, padx=4, pady=4, sticky="w")

        self._cb_mid = ctk.CTkCheckBox(
            zones, text="🟡 Meio\n(ápice)",
            font=("Arial", 10), checkbox_width=20, checkbox_height=20,
        )
        self._cb_mid.grid(row=0, column=1, padx=4, pady=4, sticky="w")

        self._cb_exit = ctk.CTkCheckBox(
            zones, text="🟢 Saída\n(aceleração)",
            font=("Arial", 10), checkbox_width=20, checkbox_height=20,
        )
        self._cb_exit.grid(row=0, column=2, padx=4, pady=4, sticky="w")

        # ─── Sensações Específicas ────────────
        feel_card = Card(left, title="🎯 Sensações do Carro")
        feel_card.pack(fill="x", pady=(0, 8))

        self._fb_stability = FeedbackSlider(
            feel_card, label="Estabilidade",
            left_text="Instável", right_text="Estável",
        )
        self._fb_stability.pack(fill="x", padx=14, pady=3)

        self._fb_responsive = FeedbackSlider(
            feel_card, label="Resposta da Direção",
            left_text="Lento", right_text="Nervoso",
        )
        self._fb_responsive.pack(fill="x", padx=14, pady=3)

        self._fb_traction = FeedbackSlider(
            feel_card, label="Tração na Saída",
            left_text="Patina", right_text="Boa",
            from_=-1.0, to=1.0,
        )
        self._fb_traction.pack(fill="x", padx=14, pady=3)

        self._fb_predictability = FeedbackSlider(
            feel_card, label="Previsibilidade",
            left_text="Imprevisível", right_text="Confiável",
            from_=-1.0, to=1.0,
        )
        self._fb_predictability.pack(fill="x", padx=14, pady=3)

        self._fb_confidence_feel = FeedbackSlider(
            feel_card, label="Confiança ao Pilotar",
            left_text="Inseguro", right_text="Confiante",
            from_=-1.0, to=1.0,
        )
        self._fb_confidence_feel.pack(fill="x", padx=14, pady=(3, 12))

        # ─── Velocidade e Potência ────────────
        speed_card = Card(left, title="⚡ Velocidade / Potência")
        speed_card.pack(fill="x", pady=(0, 8))

        self._fb_top_speed = FeedbackSlider(
            speed_card, label="Velocidade nas Retas",
            left_text="Falta velocidade", right_text="Boa",
            from_=-1.0, to=1.0,
        )
        self._fb_top_speed.pack(fill="x", padx=14, pady=3)

        self._fb_accel = FeedbackSlider(
            speed_card, label="Aceleração na Saída de Curva",
            left_text="Lenta", right_text="Forte",
            from_=-1.0, to=1.0,
        )
        self._fb_accel.pack(fill="x", padx=14, pady=(3, 12))

        # ═══ COLUNA DIREITA ════════════════════════════════

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # ─── Frenagem ─────────────────────────
        brake_card = Card(right, title="🛑 Frenagem")
        brake_card.pack(fill="x", pady=(0, 8))

        self._fb_brake = FeedbackSlider(
            brake_card, label="Potência do Freio",
            left_text="Fraco", right_text="Muito forte",
        )
        self._fb_brake.pack(fill="x", padx=14, pady=3)

        self._fb_brake_bal = FeedbackSlider(
            brake_card, label="Balanço de Freio",
            left_text="◀ Dianteiro", right_text="Traseiro ▶",
        )
        self._fb_brake_bal.pack(fill="x", padx=14, pady=3)

        self._fb_lockup = FeedbackSlider(
            brake_card, label="Travamento de Rodas",
            left_text="Nunca trava", right_text="Trava muito",
            from_=0.0, to=1.0,
        )
        self._fb_lockup.pack(fill="x", padx=14, pady=(3, 12))

        # ─── Conforto / Rigidez ───────────────
        comfort_card = Card(right, title="🛞 Conforto")
        comfort_card.pack(fill="x", pady=(0, 8))

        self._fb_stiffness = FeedbackSlider(
            comfort_card, label="Rigidez Geral",
            left_text="Macio demais", right_text="Duro demais",
        )
        self._fb_stiffness.pack(fill="x", padx=14, pady=3)

        self._fb_curbs = FeedbackSlider(
            comfort_card, label="Comportamento nos Meios-fios",
            left_text="Desestabiliza", right_text="Estável",
        )
        self._fb_curbs.pack(fill="x", padx=14, pady=3)

        self._fb_bottoming = FeedbackSlider(
            comfort_card, label="Batendo no Chão (Bottoming)",
            left_text="Nunca", right_text="Sempre",
            from_=0.0, to=1.0,
        )
        self._fb_bottoming.pack(fill="x", padx=14, pady=(3, 12))

        # ─── Pneus ───────────────────────────
        tire_card = Card(right, title="🏎️ Pneus")
        tire_card.pack(fill="x", pady=(0, 8))

        self._fb_tire_wear = FeedbackSlider(
            tire_card, label="Desgaste dos Pneus",
            left_text="Normal", right_text="Desgasta rápido",
            from_=0.0, to=1.0,
        )
        self._fb_tire_wear.pack(fill="x", padx=14, pady=3)

        self._fb_tire_grip = FeedbackSlider(
            tire_card, label="Grip Geral",
            left_text="Pouco grip", right_text="Bom grip",
            from_=-1.0, to=1.0,
        )
        self._fb_tire_grip.pack(fill="x", padx=14, pady=(3, 12))

        # ─── Confiança ────────────────────────
        conf_card = Card(right, title="📊 Certeza do Feedback")
        conf_card.pack(fill="x", pady=(0, 8))

        self._fb_confidence = FeedbackSlider(
            conf_card, label="Quão certo você está?",
            left_text="Pouco", right_text="Muito",
            from_=0.0, to=1.0,
        )
        self._fb_confidence.pack(fill="x", padx=14, pady=(3, 6))

        # ─── Botão Enviar ─────────────────────
        btn_send = ctk.CTkButton(
            right, text="📤 Enviar Feedback Detalhado",
            command=self._on_send_feedback,
            fg_color=COLORS["accent_blue"], hover_color="#3588b8",
            height=42, font=("Arial", 13, "bold"),
            corner_radius=10,
        )
        btn_send.pack(fill="x", pady=(0, 8))

        # Botão reset
        ctk.CTkButton(
            right, text="🔄 Limpar Tudo", command=self._on_reset,
            fg_color="#555555", hover_color="#444444",
            height=32, font=("Arial", 10),
            corner_radius=8,
        ).pack(fill="x", pady=(0, 8))

    # ─── Callbacks ─────────────────────────────────────

    def _on_send_feedback(self):
        if not self.engine or not hasattr(self.engine, "telemetry"):
            return
        try:
            self.engine.telemetry.set_user_feedback(
                bias=self._fb_bias.value,
                entry=self._cb_entry.get(),
                mid=self._cb_mid.get(),
                exit_=self._cb_exit.get(),
                confidence=self._fb_confidence.value,
            )

            # Construir resumo das sensações do piloto
            sensations = []
            if self._fb_bias.value < -0.3:
                sensations.append("Understeer (carro não vira)")
            elif self._fb_bias.value > 0.3:
                sensations.append("Oversteer (traseira sai)")

            if self._fb_low_speed.value < -0.3:
                sensations.append("Understeer em curvas lentas")
            elif self._fb_low_speed.value > 0.3:
                sensations.append("Oversteer em curvas lentas")

            if self._fb_high_speed.value < -0.3:
                sensations.append("Understeer em curvas rápidas")
            elif self._fb_high_speed.value > 0.3:
                sensations.append("Oversteer em curvas rápidas")

            zones = []
            if self._cb_entry.get():
                zones.append("entrada (frenagem)")
            if self._cb_mid.get():
                zones.append("meio (ápice)")
            if self._cb_exit.get():
                zones.append("saída (aceleração)")

            if self._fb_stability.value < -0.3:
                sensations.append("Carro instável")
            if self._fb_responsive.value > 0.5:
                sensations.append("Direção nervosa demais")
            elif self._fb_responsive.value < -0.3:
                sensations.append("Direção lenta/pesada")
            if self._fb_traction.value < -0.3:
                sensations.append("Patinando na saída")
            if self._fb_predictability.value < -0.3:
                sensations.append("Carro imprevisível")
            if self._fb_confidence_feel.value < -0.3:
                sensations.append("Piloto inseguro com o carro")
            if self._fb_top_speed.value < -0.3:
                sensations.append("Falta velocidade nas retas")
            if self._fb_accel.value < -0.3:
                sensations.append("Aceleração fraca na saída")
            if self._fb_brake.value > 0.4:
                sensations.append("Freio forte demais")
            elif self._fb_brake.value < -0.4:
                sensations.append("Freio fraco")
            if self._fb_lockup.value > 0.5:
                sensations.append("Rodas travando muito")
            if self._fb_stiffness.value > 0.4:
                sensations.append("Carro duro demais")
            elif self._fb_stiffness.value < -0.4:
                sensations.append("Carro macio demais")
            if self._fb_curbs.value < -0.3:
                sensations.append("Instável nos meios-fios")
            if self._fb_bottoming.value > 0.5:
                sensations.append("Carro batendo no chão")
            if self._fb_tire_wear.value > 0.5:
                sensations.append("Desgaste de pneu alto")
            if self._fb_tire_grip.value < -0.3:
                sensations.append("Pouco grip geral")

            # Montar mensagem detalhada
            msg = "📥 **Feedback detalhado recebido do piloto.**\n\n"
            if sensations:
                msg += "🎯 **Sensações reportadas:**\n"
                for s in sensations:
                    msg += f"  • {s}\n"
            if zones:
                msg += f"\n📍 **Zonas problemáticas:** {', '.join(zones)}\n"

            conf_pct = int(self._fb_confidence.value * 100)
            msg += f"\n📊 Certeza do piloto: **{conf_pct}%**\n"
            msg += "\nAnalisando para ajustar as sugestões..."

            # Enviar ao chat
            app = self.winfo_toplevel()
            if hasattr(app, "tab_setup"):
                app.tab_setup._add_message(msg, sender="system")

                # Auto-gerar sugestão após feedback detalhado
                if hasattr(app.tab_setup, 'engine') and app.tab_setup.engine:
                    try:
                        deltas, warnings = app.tab_setup.engine.request_heuristic_suggestion()
                        display_deltas = getattr(app.tab_setup.engine, '_last_display_deltas', {})
                        app.tab_setup.display_suggestions(display_deltas, warnings)
                    except Exception:
                        pass
        except Exception as e:
            logger.error("Erro ao enviar feedback: %s", e)

    def _on_reset(self):
        """Reseta todos os sliders e checkboxes."""
        for slider in (self._fb_bias, self._fb_low_speed, self._fb_high_speed,
                       self._fb_stability, self._fb_responsive, self._fb_traction,
                       self._fb_predictability, self._fb_confidence_feel,
                       self._fb_top_speed, self._fb_accel,
                       self._fb_brake, self._fb_brake_bal, self._fb_lockup,
                       self._fb_stiffness, self._fb_curbs, self._fb_bottoming,
                       self._fb_tire_wear, self._fb_tire_grip,
                       self._fb_confidence):
            slider.reset()
        self._cb_entry.deselect()
        self._cb_mid.deselect()
        self._cb_exit.deselect()

    def refresh(self):
        pass
