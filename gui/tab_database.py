"""
tab_database.py — Aba de Banco de Dados.

Estatísticas, histórico de sessões, modelos IA e exportação.
"""

from __future__ import annotations

import logging

import customtkinter as ctk

from gui.widgets import Card, LabeledValue, COLORS

logger = logging.getLogger("LMU_VE.gui.database")


class DatabaseTab(ctk.CTkFrame):
    """Aba do banco de dados com cards."""

    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ─── Estatísticas ─────────────────────────────────
        stats_card = Card(scroll, title="📊 Estatísticas")
        stats_card.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(stats_card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))

        self.val_cars = LabeledValue(row, label="Carros", value="0")
        self.val_cars.pack(side="left", padx=8)
        self.val_tracks = LabeledValue(row, label="Pistas", value="0")
        self.val_tracks.pack(side="left", padx=8)
        self.val_sessions = LabeledValue(row, label="Sessões", value="0")
        self.val_sessions.pack(side="left", padx=8)
        self.val_laps = LabeledValue(row, label="Voltas", value="0")
        self.val_laps.pack(side="left", padx=8)
        self.val_suggestions = LabeledValue(row, label="Sugestões", value="0")
        self.val_suggestions.pack(side="left", padx=8)
        self.val_training = LabeledValue(row, label="Treino", value="0")
        self.val_training.pack(side="left", padx=8)

        # Botões
        btn_row = ctk.CTkFrame(stats_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="🔄 Atualizar", width=110,
            command=self._on_refresh,
            fg_color=COLORS["accent_blue"], hover_color="#3588b8",
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row, text="📤 Exportar JSON", width=130,
            command=self._on_export,
            fg_color=COLORS["accent_purple"], hover_color="#7a3bb8",
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row, text="🧹 Otimizar DB", width=120,
            command=self._on_vacuum,
            fg_color="#555555", hover_color="#444444",
        ).pack(side="left", padx=4)

        # ─── Sessões ──────────────────────────────────────
        sess_card = Card(scroll, title="📅 Últimas Sessões")
        sess_card.pack(fill="x", pady=(0, 8))

        self._sessions_list = ctk.CTkTextbox(
            sess_card, height=150, font=("JetBrains Mono", 10),
            state="disabled", fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
        )
        self._sessions_list.pack(fill="x", padx=12, pady=(0, 10))

        # ─── Modelos IA ───────────────────────────────────
        model_card = Card(scroll, title="🧠 Modelos IA Salvos")
        model_card.pack(fill="x", pady=(0, 8))

        self._models_list = ctk.CTkTextbox(
            model_card, height=120, font=("JetBrains Mono", 10),
            state="disabled", fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
        )
        self._models_list.pack(fill="x", padx=12, pady=(0, 10))

    def _on_refresh(self):
        if not self.engine or not hasattr(self.engine, "db"):
            return
        db = self.engine.db
        if not db:
            return
        try:
            cursor = db.conn.cursor()
            counts = {}
            allowed_tables = ("cars", "tracks", "sessions", "laps",
                              "ai_suggestions", "training_data")
            for table in allowed_tables:
                cursor.execute(f"SELECT COUNT(*) FROM [{table}]")  # noqa: S608
                counts[table] = cursor.fetchone()[0]

            self.val_cars.set_value(str(counts.get("cars", 0)))
            self.val_tracks.set_value(str(counts.get("tracks", 0)))
            self.val_sessions.set_value(str(counts.get("sessions", 0)))
            self.val_laps.set_value(str(counts.get("laps", 0)))
            self.val_suggestions.set_value(str(counts.get("ai_suggestions", 0)))
            self.val_training.set_value(str(counts.get("training_data", 0)))

            # Sessões
            cursor.execute("""
                SELECT s.started_at, c.car_name, t.track_name, s.session_type
                FROM sessions s
                LEFT JOIN cars c ON c.car_id = s.car_id
                LEFT JOIN tracks t ON t.track_id = s.track_id
                ORDER BY s.started_at DESC LIMIT 10
            """)
            rows = cursor.fetchall()
            self._sessions_list.configure(state="normal")
            self._sessions_list.delete("1.0", "end")
            if rows:
                for r in rows:
                    self._sessions_list.insert(
                        "end", f"  {r[0]}  |  {r[1] or '?'}  |  {r[2] or '?'}  |  {r[3] or '?'}\n"
                    )
            else:
                self._sessions_list.insert("end", "  Nenhuma sessão registrada.")
            self._sessions_list.configure(state="disabled")

            # Modelos
            cursor.execute("""
                SELECT c.car_name, t.track_name, mc.saved_at, mc.total_samples
                FROM model_checkpoints mc
                LEFT JOIN cars c ON c.car_id = mc.car_id
                LEFT JOIN tracks t ON t.track_id = mc.track_id
                ORDER BY mc.saved_at DESC LIMIT 10
            """)
            models = cursor.fetchall()
            self._models_list.configure(state="normal")
            self._models_list.delete("1.0", "end")
            if models:
                for m in models:
                    self._models_list.insert(
                        "end", f"  {m[0] or '?'} @ {m[1] or '?'}  |  {m[2]}  |  {m[3]} amostras\n"
                    )
            else:
                self._models_list.insert("end", "  Nenhum modelo salvo.")
            self._models_list.configure(state="disabled")

        except Exception as e:
            logger.error("Erro ao atualizar estatísticas: %s", e)

    def _on_export(self):
        if not self.engine or not hasattr(self.engine, "export_data"):
            return
        try:
            path = self.engine.export_data()
            logger.info("Dados exportados para: %s", path)
        except Exception as e:
            logger.error("Erro ao exportar: %s", e)

    def _on_vacuum(self):
        if not self.engine or not hasattr(self.engine, "db"):
            return
        try:
            self.engine.db.conn.execute("VACUUM")
            logger.info("Banco otimizado (VACUUM).")
        except Exception as e:
            logger.error("Erro ao otimizar DB: %s", e)
