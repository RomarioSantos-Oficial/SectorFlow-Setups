"""
tab_telemetry.py — Aba de Telemetria em tempo real.

Exibe dados ao vivo dos pneus, freios, dinâmica do veículo,
combustível, condições climáticas e tempos de volta.
"""

from __future__ import annotations

import math

import customtkinter as ctk

from gui.widgets import (
    Card,
    LabeledValue,
    SectionHeader,
    TyreWidget,
    COLORS,
)
from gui.i18n import _


class TelemetryTab(ctk.CTkFrame):
    """Aba de telemetria ao vivo com layout em cards."""

    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ─── Tempos (card horizontal) ──────────────────────
        times_card = Card(scroll, title=f"⏱ {_('times')}")
        times_card.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(times_card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))

        self.val_lap = LabeledValue(row, label=_("lap"), value="0")
        self.val_lap.pack(side="left", padx=10)
        self.val_current = LabeledValue(row, label=_("current"), value="--:--.---")
        self.val_current.pack(side="left", padx=10)
        self.val_last = LabeledValue(row, label=_("last"), value="--:--.---")
        self.val_last.pack(side="left", padx=10)
        self.val_best = LabeledValue(row, label=_("best"), value="--:--.---")
        self.val_best.pack(side="left", padx=10)
        self.val_delta = LabeledValue(row, label=_("delta"), value="+0.000")
        self.val_delta.pack(side="left", padx=10)

        # ─── Pneus (card 2×2) ─────────────────────────────
        tyre_card = Card(scroll, title=f"🏎 {_('tires')}")
        tyre_card.pack(fill="x", pady=(0, 8))

        top = ctk.CTkFrame(tyre_card, fg_color="transparent")
        top.pack(fill="x", padx=12)
        self.tyre_fl = TyreWidget(top, position=_("front_left"))
        self.tyre_fl.pack(side="left", padx=8, pady=5, expand=True, fill="x")
        self.tyre_fr = TyreWidget(top, position=_("front_right"))
        self.tyre_fr.pack(side="left", padx=8, pady=5, expand=True, fill="x")

        bot = ctk.CTkFrame(tyre_card, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(0, 10))
        self.tyre_rl = TyreWidget(bot, position=_("rear_left"))
        self.tyre_rl.pack(side="left", padx=8, pady=5, expand=True, fill="x")
        self.tyre_rr = TyreWidget(bot, position=_("rear_right"))
        self.tyre_rr.pack(side="left", padx=8, pady=5, expand=True, fill="x")

        # ─── Veículo + Aero (lado a lado) ─────────────────
        mid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        mid_frame.pack(fill="x", pady=(0, 8))

        # Veículo
        veh_card = Card(mid_frame, title=f"🚗 {_('vehicle')}")
        veh_card.pack(side="left", fill="both", expand=True, padx=(0, 4))

        vrow = ctk.CTkFrame(veh_card, fg_color="transparent")
        vrow.pack(fill="x", padx=12, pady=(0, 10))
        self.val_speed = LabeledValue(vrow, label=_("vel"), value="0", unit="km/h")
        self.val_speed.pack(side="left", padx=8)
        self.val_gear = LabeledValue(vrow, label=_("gear"), value="N")
        self.val_gear.pack(side="left", padx=8)
        self.val_rpm = LabeledValue(vrow, label=_("rpm"), value="0")
        self.val_rpm.pack(side="left", padx=8)
        self.val_fuel = LabeledValue(vrow, label=_("comb"), value="0.0", unit="L")
        self.val_fuel.pack(side="left", padx=8)

        # Aero + Freios
        aero_card = Card(mid_frame, title=f"🌀 {_('aero_brakes')}")
        aero_card.pack(side="left", fill="both", expand=True, padx=(4, 0))

        arow = ctk.CTkFrame(aero_card, fg_color="transparent")
        arow.pack(fill="x", padx=12, pady=(0, 10))
        self.val_df_f = LabeledValue(arow, label=_("df_front"), value="0", unit="N")
        self.val_df_f.pack(side="left", padx=8)
        self.val_df_r = LabeledValue(arow, label=_("df_rear"), value="0", unit="N")
        self.val_df_r.pack(side="left", padx=8)
        self.val_drag = LabeledValue(arow, label=_("drag"), value="0", unit="N")
        self.val_drag.pack(side="left", padx=8)
        self.val_brake_bias = LabeledValue(arow, label=_("brake"), value="--%")
        self.val_brake_bias.pack(side="left", padx=8)

        # ─── Condições climáticas ──────────────────────────
        cond_card = Card(scroll, title=f"🌤 {_('conditions')}")
        cond_card.pack(fill="x", pady=(0, 8))

        crow = ctk.CTkFrame(cond_card, fg_color="transparent")
        crow.pack(fill="x", padx=12, pady=(0, 10))
        self.val_track_temp = LabeledValue(crow, label=_("track"), value="--", unit="°C")
        self.val_track_temp.pack(side="left", padx=8)
        self.val_ambient_temp = LabeledValue(crow, label=_("air"), value="--", unit="°C")
        self.val_ambient_temp.pack(side="left", padx=8)
        self.val_rain = LabeledValue(crow, label=_("rain"), value="0%")
        self.val_rain.pack(side="left", padx=8)
        self.val_wetness = LabeledValue(crow, label=_("wet_track"), value="0%")
        self.val_wetness.pack(side="left", padx=8)
        self.val_compound = LabeledValue(crow, label=_("compound"), value="---")
        self.val_compound.pack(side="left", padx=8)

        # ─── Combustível e Energia ─────────────────────────
        fuel_card = Card(scroll, title=f"⛽ {_('fuel_energy')}")
        fuel_card.pack(fill="x", pady=(0, 8))

        frow1 = ctk.CTkFrame(fuel_card, fg_color="transparent")
        frow1.pack(fill="x", padx=12, pady=(0, 4))
        self.val_fuel_per_lap = LabeledValue(frow1, label=_("consumption_lap"), value="--", unit="L")
        self.val_fuel_per_lap.pack(side="left", padx=8)
        self.val_laps_remaining = LabeledValue(frow1, label=_("laps_left"), value="--")
        self.val_laps_remaining.pack(side="left", padx=8)
        self.val_fuel_ratio = LabeledValue(frow1, label=_("fuel_ratio"), value="---")
        self.val_fuel_ratio.pack(side="left", padx=8)

        frow2 = ctk.CTkFrame(fuel_card, fg_color="transparent")
        frow2.pack(fill="x", padx=12, pady=(0, 10))
        self.val_battery = LabeledValue(frow2, label=_("battery"), value="N/A")
        self.val_battery.pack(side="left", padx=8)
        self.val_energy_balance = LabeledValue(frow2, label=_("energy"), value="---")
        self.val_energy_balance.pack(side="left", padx=8)
        self.val_energy_rec = LabeledValue(frow2, label=_("recommendation"), value="---")
        self.val_energy_rec.pack(side="left", padx=8)

        # ─── Estratégia de Sessão ──────────────────────────
        strat_card = Card(scroll, title=f"🏁 {_('session_strategy')}")
        strat_card.pack(fill="x", pady=(0, 8))

        # Tipo de sessão
        srow1 = ctk.CTkFrame(strat_card, fg_color="transparent")
        srow1.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(srow1, text=_("type"), width=50).pack(side="left", padx=(0, 4))
        self._strat_mode = ctk.StringVar(value="quali")
        ctk.CTkRadioButton(
            srow1, text=_("qualification"), variable=self._strat_mode, value="quali"
        ).pack(side="left", padx=4)
        ctk.CTkRadioButton(
            srow1, text=_("race"), variable=self._strat_mode, value="race"
        ).pack(side="left", padx=4)

        # Duração
        srow2 = ctk.CTkFrame(strat_card, fg_color="transparent")
        srow2.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(srow2, text=_("duration_min"), width=100).pack(side="left", padx=(0, 4))
        self._strat_duration = ctk.CTkEntry(srow2, width=60, placeholder_text="10")
        self._strat_duration.pack(side="left", padx=4)
        self._strat_duration.insert(0, "10")

        # Multiplicadores
        srow3 = ctk.CTkFrame(strat_card, fg_color="transparent")
        srow3.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(srow3, text=f"⛽ {_('fuel_stops')}", width=100).pack(side="left", padx=(0, 4))
        self._strat_fuel_mult = ctk.StringVar(value="1")
        for val, label in [("1", "1x"), ("2", "2x"), ("3", "3x")]:
            ctk.CTkRadioButton(
                srow3, text=label, variable=self._strat_fuel_mult, value=val, width=50
            ).pack(side="left", padx=4)

        srow4 = ctk.CTkFrame(strat_card, fg_color="transparent")
        srow4.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(srow4, text=f"🏎 {_('tire_stops')}", width=100).pack(side="left", padx=(0, 4))
        self._strat_tire_mult = ctk.StringVar(value="1")
        for val, label in [("1", "1x"), ("2", "2x"), ("3", "3x")]:
            ctk.CTkRadioButton(
                srow4, text=label, variable=self._strat_tire_mult, value=val, width=50
            ).pack(side="left", padx=4)

        # Botão calcular
        srow5 = ctk.CTkFrame(strat_card, fg_color="transparent")
        srow5.pack(fill="x", padx=12, pady=(4, 4))
        ctk.CTkButton(
            srow5, text=_("calculate_strategy"),
            command=self._calculate_strategy, width=200,
        ).pack(side="left", padx=4)

        # Área de resultado
        self._strat_result = ctk.CTkTextbox(
            strat_card, height=200, state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self._strat_result.pack(fill="x", padx=12, pady=(4, 10))

        # Botão aplicar deltas (inicialmente desabilitado)
        srow6 = ctk.CTkFrame(strat_card, fg_color="transparent")
        srow6.pack(fill="x", padx=12, pady=(0, 10))
        self._strat_apply_btn = ctk.CTkButton(
            srow6, text="🔧 Aplicar Deltas ao Setup",
            command=self._apply_strategy_deltas, width=200, state="disabled",
        )
        self._strat_apply_btn.pack(side="left", padx=4)

        # Cache do último resultado
        self._last_strategy: dict | None = None

    def refresh(self):
        """Atualiza com dados da telemetria."""
        if not self.engine or not hasattr(self.engine, "telemetry"):
            return

        data = self.engine.telemetry.get_live_telemetry()
        if not data:
            return

        # Tempos
        self.val_lap.set_value(str(data.get("lap_number", 0)))
        self.val_current.set_value(self._fmt(data.get("lap_time", 0)))
        self.val_last.set_value(self._fmt(data.get("last_lap_time", 0)))
        self.val_best.set_value(self._fmt(data.get("best_lap_time", 0)))

        delta = data.get("delta_best", 0)
        if delta > 0:
            self.val_delta.set_value(f"+{delta:.3f}", COLORS["accent_red"])
        elif delta < 0:
            self.val_delta.set_value(f"{delta:.3f}", COLORS["accent_green"])
        else:
            self.val_delta.set_value("+0.000")

        # Pneus
        temps = data.get("tyre_temps_ico", (0,) * 12)
        press = data.get("tyre_pressure", (0,) * 4)
        wear = data.get("tyre_wear", (1,) * 4)
        grip = data.get("tyre_grip", (-1,) * 4)

        self.tyre_fl.update_data(
            temp=(temps[0] + temps[1] + temps[2]) / 3,
            pressure=press[0], wear=wear[0],
            grip=grip[0] if len(grip) > 0 else -1,
        )
        self.tyre_fr.update_data(
            temp=(temps[3] + temps[4] + temps[5]) / 3,
            pressure=press[1], wear=wear[1],
            grip=grip[1] if len(grip) > 1 else -1,
        )
        self.tyre_rl.update_data(
            temp=(temps[6] + temps[7] + temps[8]) / 3,
            pressure=press[2], wear=wear[2],
            grip=grip[2] if len(grip) > 2 else -1,
        )
        self.tyre_rr.update_data(
            temp=(temps[9] + temps[10] + temps[11]) / 3,
            pressure=press[3], wear=wear[3],
            grip=grip[3] if len(grip) > 3 else -1,
        )

        # Veículo
        self.val_speed.set_value(f"{data.get('speed', 0):.0f}")
        gear = data.get("gear", 0)
        self.val_gear.set_value("R" if gear < 0 else "N" if gear == 0 else str(gear))
        self.val_rpm.set_value(f"{data.get('rpm', 0):.0f}")
        self.val_fuel.set_value(f"{data.get('fuel', 0):.1f}")

        # Aero
        self.val_df_f.set_value(f"{data.get('downforce_f', 0):.0f}")
        self.val_df_r.set_value(f"{data.get('downforce_r', 0):.0f}")
        self.val_drag.set_value(f"{data.get('drag', 0):.0f}")
        bb = data.get("rear_brake_bias", 0)
        if bb > 0:
            self.val_brake_bias.set_value(f"{(1 - bb) * 100:.1f}:{bb * 100:.1f}")

        # Condições
        self.val_track_temp.set_value(f"{data.get('track_temp', 0):.1f}")
        self.val_ambient_temp.set_value(f"{data.get('ambient_temp', 0):.1f}")
        rain = data.get("rain", 0) * 100
        self.val_rain.set_value(f"{rain:.0f}%")
        wet = data.get("avg_wetness", 0) * 100
        self.val_wetness.set_value(f"{wet:.0f}%")
        self.val_compound.set_value(data.get("compound", "---"))

        # Combustível e Energia
        if hasattr(self.engine, "calculate_fuel_strategy"):
            try:
                fs = self.engine.calculate_fuel_strategy()
                if fs["fuel_per_lap"] > 0:
                    self.val_fuel_per_lap.set_value(f"{fs['fuel_per_lap']:.2f}")
                    self.val_laps_remaining.set_value(str(fs["laps_remaining"]))
                    self.val_fuel_ratio.set_value(fs["recommended_fuel_ratio"])
                    # Cor do fuel ratio
                    if "Crítico" in fs["recommended_fuel_ratio"]:
                        self.val_fuel_ratio.set_value(
                            fs["recommended_fuel_ratio"], COLORS["accent_red"])
                    elif "Alto" in fs["recommended_fuel_ratio"]:
                        self.val_fuel_ratio.set_value(
                            fs["recommended_fuel_ratio"], COLORS["accent_yellow"])
                    elif "Equilibrado" in fs["recommended_fuel_ratio"]:
                        self.val_fuel_ratio.set_value(
                            fs["recommended_fuel_ratio"], COLORS["accent_green"])

                if fs["has_regen"]:
                    bat = fs["battery_charge"]
                    if bat >= 0:
                        bat_pct = f"{bat * 100:.0f}%"
                        if bat < 0.2:
                            self.val_battery.set_value(bat_pct, COLORS["accent_red"])
                        elif bat < 0.4:
                            self.val_battery.set_value(bat_pct, COLORS["accent_yellow"])
                        else:
                            self.val_battery.set_value(bat_pct, COLORS["accent_green"])
                    self.val_energy_balance.set_value(fs["energy_balance"])
                    self.val_energy_rec.set_value(fs["virtual_energy_recommendation"])
                else:
                    self.val_battery.set_value("N/A")
                    self.val_energy_balance.set_value("Sem híbrido")
                    self.val_energy_rec.set_value("---")
            except Exception:
                pass

    @staticmethod
    def _fmt(seconds: float) -> str:
        if seconds <= 0 or seconds > 3600:
            return "--:--.---"
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:06.3f}"

    # ─── Estratégia de Sessão ───────────────────────

    def _calculate_strategy(self):
        """Calcula e exibe a estratégia de sessão."""
        if not self.engine:
            return

        try:
            duration = float(self._strat_duration.get() or "10")
        except ValueError:
            duration = 10.0

        mode = self._strat_mode.get()
        fuel_mult = float(self._strat_fuel_mult.get())
        tire_mult = float(self._strat_tire_mult.get())

        result = self.engine.calculate_session_strategy(
            mode=mode,
            duration_min=duration,
            fuel_mult=fuel_mult,
            tire_mult=tire_mult,
        )
        self._last_strategy = result
        # Persistir alvo de combustível para aplicação posterior no fluxo de setup.
        if self.engine and result.get("fuel_recommended", 0) > 0:
            self.engine._pending_fuel_target_liters = int(
                math.ceil(float(result["fuel_recommended"]))
            )

        # Formatar resultado
        lines = []
        mode_label = "QUALIFICAÇÃO" if mode == "quali" else "CORRIDA"
        lines.append(f"🏁 {mode_label} — {duration:.0f} minutos")
        lines.append(f"   Fonte de dados: {result['data_source']}")
        lines.append("")

        if not result["has_data"]:
            lines.append("⚠️ Sem dados suficientes para estimar.")
            lines.append("   Complete pelo menos 1 volta para calcular.")
        else:
            # Estimativas
            lines.append("📊 Estimativas:")
            lines.append(f"   Tempo médio de volta: {self._fmt(result['avg_lap_time'])}")
            lines.append(f"   Voltas estimadas: {result['estimated_laps']}")

            if result["fuel_per_lap"] > 0:
                lines.append("")
                lines.append("⛽ Combustível:")
                lines.append(
                    f"   Consumo/volta: {result['fuel_per_lap']:.2f} L"
                    f" (× {fuel_mult:.0f}x = {result['fuel_per_lap_adjusted']:.2f} L)"
                )
                lines.append(f"   Total necessário: {result['fuel_total_needed']:.1f} L")
                lines.append(f"   Recomendado: {result['fuel_recommended']:.1f} L")
                if result["fuel_capacity"] > 0:
                    lines.append(
                        f"   Tanque: {result['fuel_capacity']:.0f} L "
                        f"(usando {result['fuel_tank_pct']:.0f}%)"
                    )
                lines.append(f"   Peso combustível: {result['fuel_weight_kg']:.1f} kg")

            # Stints
            if result["total_pits"] > 0:
                lines.append("")
                lines.append(f"🔧 PIT STOPS: {result['total_pits']} parada(s)")
                for stint in result["stints"]:
                    pit = " → PIT" if stint["pit_after"] else " → 🏁"
                    lines.append(
                        f"   Stint {stint['stint']}: "
                        f"{stint['fuel_load']:.1f} L → "
                        f"{stint['laps']} voltas{pit}"
                    )

            # Desgaste
            if result["wear_per_lap"] > 0:
                lines.append("")
                lines.append("🏎 Desgaste de Pneu:")
                lines.append(
                    f"   Por volta: {result['wear_per_lap']:.1f}%"
                    f" (× {tire_mult:.0f}x = {result['wear_per_lap_adjusted']:.1f}%)"
                )
                lines.append(f"   Total previsto: {result['wear_total_pct']:.1f}%")
                if result["needs_tire_pit"]:
                    lines.append("   ⚠️ Trocar pneus no pit!")
                else:
                    lines.append("   ✅ Sem necessidade de troca")

            # Deltas recomendados
            if result["deltas"]:
                lines.append("")
                lines.append(f"⚙️ Deltas Recomendados ({mode_label}):")
                for exp in result["delta_explanations"]:
                    lines.append(f"   • {exp}")

                # Habilitar botão de aplicar
                self._strat_apply_btn.configure(state="normal")
            else:
                self._strat_apply_btn.configure(state="disabled")

        # Atualizar textbox
        self._strat_result.configure(state="normal")
        self._strat_result.delete("1.0", "end")
        self._strat_result.insert("1.0", "\n".join(lines))
        self._strat_result.configure(state="disabled")

    def _apply_strategy_deltas(self):
        """Aplica os deltas da estratégia ao setup carregado."""
        if not self._last_strategy or not self._last_strategy.get("deltas"):
            return
        if not self.engine:
            return

        from core.brain import deltas_to_svm

        deltas = self._last_strategy["deltas"]
        svm_deltas = deltas_to_svm(deltas)

        if self.engine._current_svm:
            from data.svm_parser import apply_deltas, save_svm
            from config import BACKUPS_DIR

            apply_deltas(self.engine._current_svm, svm_deltas)

            # Aplicar combustível recomendado como alvo absoluto (litros),
            # não apenas como delta genérico.
            fuel_note = ""
            try:
                fuel_target = float(self._last_strategy.get("fuel_recommended", 0.0) or 0.0)
                if fuel_target > 0:
                    fuel_param = None
                    for p in self.engine._current_svm.params.values():
                        if p.name == "FuelSetting" and p.adjustable:
                            fuel_param = p
                            break

                    if fuel_param is not None:
                        target_index = max(0, min(int(math.ceil(fuel_target)), 200))
                        old_index = fuel_param.index
                        if target_index != old_index:
                            fuel_param.index = target_index
                            old_line = self.engine._current_svm.raw_lines[fuel_param.line_number]
                            import re
                            new_line = re.sub(
                                r"^(\w+Setting\s*=\s*)\d+(\s*//.*)$",
                                rf"\g<1>{target_index}\2",
                                old_line,
                            )
                            self.engine._current_svm.raw_lines[fuel_param.line_number] = new_line
                        fuel_note = (
                            f"\n⛽ FuelSetting ajustado: {old_index} → {target_index} L"
                        )
                    else:
                        fuel_note = (
                            "\n⚠️ FuelSetting não encontrado neste setup; "
                            "aplique o combustível manualmente na garagem."
                        )
            except Exception as e:
                fuel_note = f"\n⚠️ Falha ao aplicar combustível automático: {e}"

            save_svm(self.engine._current_svm, backup_dir=str(BACKUPS_DIR))

            # Feedback visual
            self._strat_result.configure(state="normal")
            self._strat_result.insert(
                "end", f"\n\n✅ Deltas aplicados e setup salvo!{fuel_note}"
            )
            self._strat_result.configure(state="disabled")
            self._strat_apply_btn.configure(state="disabled")
        else:
            self._strat_result.configure(state="normal")
            self._strat_result.insert(
                "end", "\n\n⚠️ Nenhum setup carregado. Carregue um .svm primeiro."
            )
            self._strat_result.configure(state="disabled")
