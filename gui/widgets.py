"""
widgets.py — Widgets reutilizáveis para a GUI do Sector Flow Setups.

Componentes visuais customizados construídos sobre CustomTkinter.
Estilo moderno com cards, cores vibrantes e layout limpo.
"""

from __future__ import annotations

import customtkinter as ctk


# ─── Paleta de cores global ────────────────────────────
COLORS = {
    "bg_dark": "#0f0f1a",
    "bg_card": "#1a1a2e",
    "bg_card_hover": "#252545",
    "bg_input": "#16162b",
    "accent_blue": "#4ea8de",
    "accent_green": "#00cc66",
    "accent_yellow": "#ffc857",
    "accent_red": "#ff4d6d",
    "accent_purple": "#9d4edd",
    "accent_orange": "#ff8c42",
    "accent_cyan": "#00d4ff",
    "text_primary": "#e8e8f0",
    "text_secondary": "#8888aa",
    "separator": "#2a2a4a",
    "cold": "#4cc9f0",
    "ideal": "#06d6a0",
    "warm": "#ffd166",
    "hot": "#ef476f",
    "chat_user": "#2a2a5e",
    "chat_ai": "#1e3a2e",
    "chat_system": "#2e2a1e",
}


# ─── Componentes Base ──────────────────────────────────

class StatusIndicator(ctk.CTkFrame):
    """LED + label de status."""

    def __init__(self, master, label: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._led = ctk.CTkLabel(self, text="●", font=("Arial", 14),
                                 width=18, text_color="gray")
        self._led.pack(side="left", padx=(0, 4))
        self._label = ctk.CTkLabel(self, text=label,
                                   font=("Arial", 11, "bold"),
                                   text_color=COLORS["text_secondary"])
        self._label.pack(side="left")

    _STATUS_COLORS = {
        "ok": "accent_green", "warning": "accent_yellow",
        "error": "accent_red", "off": None, "active": "accent_blue",
    }

    def set_status(self, status: str):
        key = self._STATUS_COLORS.get(status)
        self._led.configure(text_color=COLORS.get(key, "gray") if key else "gray")


class Card(ctk.CTkFrame):
    """Card com bordas arredondadas e título opcional."""

    def __init__(self, master, title: str = "", **kwargs):
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("fg_color", COLORS["bg_card"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["separator"])
        super().__init__(master, **kwargs)
        if title:
            ctk.CTkLabel(self, text=title, font=("Arial", 13, "bold"),
                         text_color=COLORS["accent_blue"],
                         anchor="w").pack(fill="x", padx=14, pady=(12, 4))


class SectionHeader(ctk.CTkFrame):
    """Cabeçalho de seção com linha colorida."""

    def __init__(self, master, text: str = "", icon: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        display = f"{icon} {text}" if icon else text
        ctk.CTkLabel(self, text=display, font=("Arial", 13, "bold"),
                     text_color=COLORS["accent_blue"]).pack(anchor="w", pady=(12, 3))
        ctk.CTkFrame(self, height=2,
                     fg_color=COLORS["accent_blue"]).pack(fill="x")


# ─── Dados ─────────────────────────────────────────────

class LabeledValue(ctk.CTkFrame):
    """Label + valor numérico grande."""

    def __init__(self, master, label: str = "", value: str = "---",
                 unit: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=label, font=("Arial", 10),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        val_frame = ctk.CTkFrame(self, fg_color="transparent")
        val_frame.pack(anchor="w")
        self._value = ctk.CTkLabel(val_frame, text=value,
                                   font=("JetBrains Mono", 17, "bold"),
                                   text_color=COLORS["text_primary"])
        self._value.pack(side="left")
        if unit:
            ctk.CTkLabel(val_frame, text=unit, font=("Arial", 10),
                         text_color=COLORS["text_secondary"]).pack(
                side="left", padx=(3, 0), anchor="s", pady=(0, 2))

    def set_value(self, value: str, color: str | None = None):
        self._value.configure(text=value)
        if color:
            self._value.configure(text_color=color)


class DeltaDisplay(ctk.CTkFrame):
    """Delta de ajuste sugerido pela IA com visual moderno.
    Mostra: nome | valor_atual → valor_novo | delta | botões +/- | descrição
    O usuário pode ajustar manualmente o delta usando os botões +/-.
    """

    def __init__(self, master, param_name: str = "",
                 on_change: callable = None,
                 param_key: str = "",
                 max_delta: int = 5,
                 **kwargs):
        super().__init__(master, corner_radius=8,
                         fg_color=COLORS["bg_card"],
                         border_width=1, border_color=COLORS["separator"],
                         **kwargs)
        self._param_key = param_key or param_name
        self._on_change = on_change
        self._max_delta = max_delta
        self._current_delta = 0
        self._current_index: int | None = None

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=6)

        self._name = ctk.CTkLabel(inner, text=param_name, font=("Arial", 11),
                                  text_color=COLORS["text_primary"])
        self._name.pack(side="left")

        right_frame = ctk.CTkFrame(inner, fg_color="transparent")
        right_frame.pack(side="right")

        # Valores: atual → novo
        self._current_val = ctk.CTkLabel(right_frame, text="",
                                         font=("JetBrains Mono", 10),
                                         text_color=COLORS["text_secondary"])
        self._current_val.pack(side="left")

        self._arrow = ctk.CTkLabel(right_frame, text="",
                                   font=("Arial", 10),
                                   text_color=COLORS["text_secondary"])
        self._arrow.pack(side="left", padx=(2, 2))

        self._new_val = ctk.CTkLabel(right_frame, text="",
                                     font=("JetBrains Mono", 10, "bold"),
                                     text_color=COLORS["text_primary"])
        self._new_val.pack(side="left")

        # Botão - (diminuir)
        self._btn_minus = ctk.CTkButton(
            right_frame, text="−", width=28, height=28,
            font=("Arial", 14, "bold"),
            fg_color=COLORS["accent_red"], hover_color="#cc3355",
            corner_radius=6,
            command=self._on_minus,
        )
        self._btn_minus.pack(side="left", padx=(8, 2))

        # Delta label
        self._delta = ctk.CTkLabel(right_frame, text="─ 0",
                                   font=("JetBrains Mono", 14, "bold"),
                                   text_color=COLORS["text_secondary"],
                                   width=60)
        self._delta.pack(side="left", padx=(2, 2))

        # Botão + (aumentar)
        self._btn_plus = ctk.CTkButton(
            right_frame, text="+", width=28, height=28,
            font=("Arial", 14, "bold"),
            fg_color=COLORS["accent_green"], hover_color="#009955",
            corner_radius=6,
            command=self._on_plus,
        )
        self._btn_plus.pack(side="left", padx=(2, 0))

        self._desc = ctk.CTkLabel(right_frame, text="", font=("Arial", 9),
                                  text_color=COLORS["text_secondary"])
        self._desc.pack(side="left", padx=(8, 0))

    def _on_minus(self):
        """Diminui o delta em 1 índice."""
        new_delta = max(-self._max_delta, self._current_delta - 1)
        if new_delta != self._current_delta:
            self._current_delta = new_delta
            self._update_display()
            if self._on_change:
                self._on_change(self._param_key, self._current_delta)

    def _on_plus(self):
        """Aumenta o delta em 1 índice."""
        new_delta = min(self._max_delta, self._current_delta + 1)
        if new_delta != self._current_delta:
            self._current_delta = new_delta
            self._update_display()
            if self._on_change:
                self._on_change(self._param_key, self._current_delta)

    def _update_display(self):
        """Atualiza a exibição do delta e valores."""
        delta = self._current_delta
        if delta > 0:
            text, color = f"▲ +{delta}", COLORS["accent_green"]
        elif delta < 0:
            text, color = f"▼ {delta}", COLORS["accent_red"]
        else:
            text, color = "─ 0", COLORS["text_secondary"]
        self._delta.configure(text=text, text_color=color)

        # Mostrar valor atual → novo quando disponível
        if self._current_index is not None and delta != 0:
            new_index = max(0, self._current_index + delta)
            self._current_val.configure(text=f"[{self._current_index}]")
            self._arrow.configure(text="→")
            self._new_val.configure(text=f"[{new_index}]", text_color=color)
        elif self._current_index is not None:
            self._current_val.configure(text=f"[{self._current_index}]")
            self._arrow.configure(text="")
            self._new_val.configure(text="")
        else:
            self._current_val.configure(text="")
            self._arrow.configure(text="")
            self._new_val.configure(text="")

    def set_delta(self, delta: int, description: str = "",
                  current_index: int | None = None,
                  current_desc: str = ""):
        """Define o delta (chamado pela IA ou heurísticas)."""
        self._current_delta = delta
        self._current_index = current_index
        info_text = description or (f"Atual: {current_desc}" if current_desc else "")
        self._desc.configure(text=info_text)
        self._update_display()

    def get_delta(self) -> int:
        """Retorna o delta atual (pode ter sido modificado pelo usuário)."""
        return self._current_delta

    def reset(self):
        """Reseta o delta para 0."""
        self._current_delta = 0
        self._current_index = None
        self._desc.configure(text="")
        self._update_display()


# ─── Chat / Conversação ───────────────────────────────

class ChatBubble(ctk.CTkFrame):
    """Balão de chat para a interface conversacional."""

    def __init__(self, master, message: str, sender: str = "user",
                 timestamp: str = "", **kwargs):
        """
        sender: "user", "ai", "system"
        """
        self.message_text = message  # Guardar texto para busca/remoção
        bg_map = {
            "user": COLORS["chat_user"],
            "ai": COLORS["chat_ai"],
            "system": COLORS["chat_system"],
        }
        icon_map = {"user": "👤", "ai": "🤖", "system": "ℹ️"}
        align = "e" if sender == "user" else "w"

        super().__init__(master, fg_color="transparent", **kwargs)

        # Container do balão
        bubble = ctk.CTkFrame(
            self, corner_radius=12,
            fg_color=bg_map.get(sender, COLORS["bg_card"]),
            border_width=1, border_color=COLORS["separator"],
        )
        bubble.pack(anchor=align, padx=(40 if sender == "user" else 8,
                                        8 if sender == "user" else 40),
                    pady=3, fill="x")

        # Header com ícone e timestamp
        header = ctk.CTkFrame(bubble, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        icon = icon_map.get(sender, "💬")
        name_map = {"user": "Você", "ai": "Engenheiro Virtual", "system": "Sistema"}
        ctk.CTkLabel(
            header, text=f"{icon} {name_map.get(sender, sender)}",
            font=("Arial", 10, "bold"),
            text_color=COLORS["accent_blue"] if sender == "ai" else COLORS["text_secondary"],
        ).pack(side="left")

        if timestamp:
            ctk.CTkLabel(
                header, text=timestamp, font=("Arial", 8),
                text_color=COLORS["text_secondary"],
            ).pack(side="right")

        # Texto da mensagem
        msg_label = ctk.CTkLabel(
            bubble, text=message, font=("Arial", 11),
            text_color=COLORS["text_primary"],
            wraplength=450, justify="left", anchor="w",
        )
        msg_label.pack(fill="x", padx=12, pady=(2, 10))


class SuggestedPhrase(ctk.CTkButton):
    """Botão de frase sugerida para o chat conversacional."""

    def __init__(self, master, text: str, icon: str = "💬",
                 callback=None, **kwargs):
        display = f"{icon} {text}"
        super().__init__(
            master, text=display, font=("Arial", 11),
            fg_color=COLORS["bg_card"], text_color=COLORS["text_primary"],
            hover_color=COLORS["bg_card_hover"],
            border_width=1, border_color=COLORS["accent_blue"],
            corner_radius=20, height=36, anchor="w",
            command=lambda: callback(text) if callback else None,
            **kwargs,
        )


class SetupFileCard(ctk.CTkFrame):
    """Card compacto representando um arquivo .svm."""

    def __init__(self, master, filename: str, folder: str = "",
                 is_setorflow: bool = False,
                 on_select=None, on_view=None, **kwargs):
        super().__init__(
            master, corner_radius=10,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["accent_blue"] if is_setorflow else COLORS["separator"],
            **kwargs,
        )

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=8)

        icon = "⚡" if is_setorflow else "📄"
        ctk.CTkLabel(
            content, text=icon, font=("Arial", 18),
        ).pack(side="left", padx=(0, 8))

        info = ctk.CTkFrame(content, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info, text=filename, font=("Arial", 12, "bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).pack(anchor="w")

        if folder:
            ctk.CTkLabel(
                info, text=folder, font=("Arial", 9),
                text_color=COLORS["text_secondary"], anchor="w",
            ).pack(anchor="w")

        btns = ctk.CTkFrame(content, fg_color="transparent")
        btns.pack(side="right")

        if on_select:
            ctk.CTkButton(
                btns, text="Usar", width=60, height=28,
                fg_color=COLORS["accent_blue"], hover_color="#3588b8",
                font=("Arial", 10), command=on_select,
            ).pack(side="left", padx=2)

        if on_view:
            ctk.CTkButton(
                btns, text="Ver", width=50, height=28,
                fg_color=COLORS["accent_purple"], hover_color="#7a3bb8",
                font=("Arial", 10), command=on_view,
            ).pack(side="left", padx=2)


# ─── Pneu ──────────────────────────────────────────────

class TyreWidget(ctk.CTkFrame):
    """Widget de pneu com temp, pressão, desgaste e grip."""

    def __init__(self, master, position: str = "FL", **kwargs):
        super().__init__(master, corner_radius=10,
                         fg_color=COLORS["bg_card"],
                         border_width=1, border_color=COLORS["separator"],
                         **kwargs)
        self._pos = ctk.CTkLabel(self, text=position,
                                 font=("Arial", 13, "bold"),
                                 text_color=COLORS["accent_blue"])
        self._pos.pack(pady=(8, 2))

        self._temp = ctk.CTkLabel(self, text="--- °C",
                                  font=("JetBrains Mono", 16, "bold"),
                                  text_color=COLORS["text_primary"])
        self._temp.pack()

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(2, 0))
        self._pressure = ctk.CTkLabel(row, text="--- kPa",
                                      font=("Arial", 10),
                                      text_color=COLORS["text_secondary"])
        self._pressure.pack(side="left")
        self._wear_text = ctk.CTkLabel(row, text="100%",
                                       font=("Arial", 10, "bold"),
                                       text_color=COLORS["accent_green"])
        self._wear_text.pack(side="right")

        self._wear_bar = ctk.CTkProgressBar(self, width=100, height=6,
                                            corner_radius=3,
                                            progress_color=COLORS["accent_green"],
                                            fg_color=COLORS["separator"])
        self._wear_bar.pack(pady=(2, 4), padx=10)
        self._wear_bar.set(1.0)

        # Grip
        grip_row = ctk.CTkFrame(self, fg_color="transparent")
        grip_row.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(grip_row, text="Grip:", font=("Arial", 9),
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._grip = ctk.CTkLabel(grip_row, text="---%",
                                  font=("Arial", 9, "bold"),
                                  text_color=COLORS["text_secondary"])
        self._grip.pack(side="left", padx=3)

    def update_data(self, temp: float, pressure: float, wear: float,
                    grip: float = -1.0):
        """Atualiza dados do pneu."""
        if temp < 70:
            tc = COLORS["cold"]
        elif temp < 90:
            tc = COLORS["ideal"]
        elif temp < 110:
            tc = COLORS["warm"]
        else:
            tc = COLORS["hot"]
        self._temp.configure(text=f"{temp:.0f} °C", text_color=tc)
        self._pressure.configure(text=f"{pressure:.0f} kPa")

        wf = max(0.0, min(1.0, wear))
        self._wear_bar.set(wf)
        self._wear_text.configure(text=f"{int(wf * 100)}%")
        if wf > 0.7:
            wc = COLORS["accent_green"]
        elif wf > 0.3:
            wc = COLORS["accent_yellow"]
        else:
            wc = COLORS["accent_red"]
        self._wear_bar.configure(progress_color=wc)
        self._wear_text.configure(text_color=wc)

        if grip >= 0:
            gp = int(grip * 100)
            self._grip.configure(text=f"{gp}%")
            if grip > 0.85:
                self._grip.configure(text_color=COLORS["accent_green"])
            elif grip > 0.6:
                self._grip.configure(text_color=COLORS["accent_yellow"])
            else:
                self._grip.configure(text_color=COLORS["accent_red"])


# ─── Feedback ──────────────────────────────────────────

class FeedbackSlider(ctk.CTkFrame):
    """Slider para feedback do usuário."""

    def __init__(self, master, label: str = "",
                 left_text: str = "", right_text: str = "",
                 from_: float = -1.0, to: float = 1.0,
                 **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        title = ctk.CTkLabel(
            self, text=label, font=("Arial", 11, "bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(anchor="w")

        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.pack(fill="x")

        left = ctk.CTkLabel(
            slider_frame, text=left_text, font=("Arial", 9),
            text_color=COLORS["text_secondary"]
        )
        left.pack(side="left")

        self._slider = ctk.CTkSlider(
            slider_frame, from_=from_, to=to,
            number_of_steps=20, width=200,
            button_color=COLORS["accent_blue"],
            button_hover_color=COLORS["accent_purple"],
            progress_color=COLORS["accent_blue"]
        )
        self._slider.pack(side="left", expand=True, fill="x", padx=5)
        self._slider.set(0)

        right = ctk.CTkLabel(
            slider_frame, text=right_text, font=("Arial", 9),
            text_color=COLORS["text_secondary"]
        )
        right.pack(side="left")

    @property
    def value(self) -> float:
        return self._slider.get()

    def reset(self):
        self._slider.set(0)


class ConfidenceBar(ctk.CTkFrame):
    """Barra de confiança da IA com visual moderno."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x")

        ctk.CTkLabel(
            header, text="🧠 Confiança da IA", font=("Arial", 11, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        self._pct_label = ctk.CTkLabel(
            header, text="0%", font=("JetBrains Mono", 11, "bold"),
            text_color=COLORS["accent_blue"]
        )
        self._pct_label.pack(side="right")

        self._bar = ctk.CTkProgressBar(
            self, height=8, corner_radius=4,
            progress_color=COLORS["accent_blue"],
            fg_color=COLORS["separator"]
        )
        self._bar.pack(fill="x", pady=(3, 0))
        self._bar.set(0)

        self._info = ctk.CTkLabel(
            self, text="Coletando dados...",
            font=("Arial", 9), text_color=COLORS["text_secondary"]
        )
        self._info.pack(anchor="w")

    def set_confidence(self, value: float, samples: int):
        """Atualiza a confiança (0.0-1.0)."""
        self._bar.set(max(0.0, min(1.0, value)))
        pct = int(value * 100)
        self._pct_label.configure(text=f"{pct}%")

        if value < 0.2:
            self._info.configure(text=f"Aprendendo... ({samples} amostras)")
            self._bar.configure(progress_color=COLORS["accent_red"])
            self._pct_label.configure(text_color=COLORS["accent_red"])
        elif value < 0.5:
            self._info.configure(text=f"Progredindo ({samples} amostras)")
            self._bar.configure(progress_color=COLORS["accent_yellow"])
            self._pct_label.configure(text_color=COLORS["accent_yellow"])
        elif value < 0.7:
            self._info.configure(text=f"Confiável ({samples} amostras)")
            self._bar.configure(progress_color=COLORS["accent_blue"])
            self._pct_label.configure(text_color=COLORS["accent_blue"])
        else:
            self._info.configure(text=f"Avançada ({samples} amostras)")
            self._bar.configure(progress_color=COLORS["accent_green"])
            self._pct_label.configure(text_color=COLORS["accent_green"])


class WeatherIndicator(ctk.CTkFrame):
    """Indicador visual de condições climáticas."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master, corner_radius=8,
            fg_color=COLORS["bg_card"],
            border_width=1, border_color=COLORS["separator"],
            **kwargs
        )

        self._icon = ctk.CTkLabel(
            self, text="☀️", font=("Arial", 20)
        )
        self._icon.pack(side="left", padx=(10, 5))

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", padx=(0, 10), pady=5)

        self._status = ctk.CTkLabel(
            info, text="Seco", font=("Arial", 12, "bold"),
            text_color=COLORS["text_primary"]
        )
        self._status.pack(anchor="w")

        self._details = ctk.CTkLabel(
            info, text="Pista: -- °C  |  Ar: -- °C",
            font=("Arial", 9), text_color=COLORS["text_secondary"]
        )
        self._details.pack(anchor="w")

    def update_weather(self, rain: float, track_temp: float,
                       ambient_temp: float, wetness: float = 0.0):
        """Atualiza o indicador de clima."""
        if rain > 0.5:
            icon, status = "🌧️", "Chuva Forte"
            color = COLORS["accent_blue"]
        elif rain > 0.2:
            icon, status = "🌦️", "Chuva Leve"
            color = COLORS["accent_blue"]
        elif wetness > 0.3:
            icon, status = "💧", "Pista Molhada"
            color = COLORS["accent_yellow"]
        elif rain > 0.05:
            icon, status = "⛅", "Nublado"
            color = COLORS["text_secondary"]
        else:
            icon, status = "☀️", "Seco"
            color = COLORS["accent_yellow"]

        self._icon.configure(text=icon)
        self._status.configure(text=status, text_color=color)
        self._details.configure(
            text=f"Pista: {track_temp:.0f}°C  |  Ar: {ambient_temp:.0f}°C"
        )
