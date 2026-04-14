"""
tab_files.py — Aba de gerenciamento de Setups.

Lista setups, exibe detalhes, compara arquivos .svm.
Ações de criar/editar são feitas pelo menu Setup (sem duplicação).
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from gui.widgets import Card, SectionHeader, LabeledValue, COLORS

logger = logging.getLogger("LMU_VE.gui.files")


class FilesTab(ctk.CTkFrame):
    """Aba de gerenciamento de arquivos .svm com cards."""

    def __init__(self, master, engine=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.engine = engine
        self._current_files: list[Path] = []
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ─── Toolbar ──────────────────────────────────────
        tb_card = Card(scroll, title="🔍 Buscar Setups")
        tb_card.pack(fill="x", pady=(0, 8))

        btn_row = ctk.CTkFrame(tb_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="🔍 Escanear Pasta", width=140,
            command=self._on_scan,
            fg_color=COLORS["accent_blue"], hover_color="#3588b8",
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_row, text="📂 Abrir .svm", width=120,
            command=self._on_open_file,
            fg_color=COLORS["accent_purple"], hover_color="#7a3bb8",
        ).pack(side="left", padx=4)

        # Estatísticas rápidas
        stats_row = ctk.CTkFrame(tb_card, fg_color="transparent")
        stats_row.pack(fill="x", padx=12, pady=(0, 10))

        self._val_total = LabeledValue(stats_row, label="Total", value="0")
        self._val_total.pack(side="left", padx=8)
        self._val_setorflow = LabeledValue(stats_row, label="SetorFlow", value="0")
        self._val_setorflow.pack(side="left", padx=8)
        self._val_folder = LabeledValue(stats_row, label="Pasta", value="---")
        self._val_folder.pack(side="left", padx=8)

        # ─── Lista de arquivos ────────────────────────────
        list_card = Card(scroll, title="📁 Setups Encontrados")
        list_card.pack(fill="both", expand=True, pady=(0, 8))

        self._file_list = ctk.CTkTextbox(
            list_card, font=("JetBrains Mono", 11), state="disabled",
            fg_color=COLORS["bg_card"], text_color=COLORS["text_primary"],
            height=200,
        )
        self._file_list.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # ─── Detalhes do setup selecionado ────────────────
        detail_card = Card(scroll, title="📋 Detalhes do Setup")
        detail_card.pack(fill="x", pady=(0, 8))

        self._details = ctk.CTkTextbox(
            detail_card, height=180, font=("JetBrains Mono", 10),
            state="disabled", fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
        )
        self._details.pack(fill="x", padx=12, pady=(0, 10))

    def _on_scan(self):
        if not self.engine or not hasattr(self.engine, "scan_setup_files"):
            return
        try:
            files = self.engine.scan_setup_files()
            self._current_files = files
            self._display_file_list(files)
        except Exception as e:
            logger.error("Erro ao escanear setups: %s", e)

    def _on_open_file(self):
        filepath = filedialog.askopenfilename(
            title="Abrir Setup (.svm)",
            filetypes=[("Setup files", "*.svm"), ("Todos", "*.*")],
        )
        if not filepath:
            return
        try:
            if self.engine and hasattr(self.engine, "load_setup"):
                svm = self.engine.load_setup(filepath)
                self._display_setup_details(svm)
        except Exception as e:
            logger.error("Erro ao abrir .svm: %s", e)

    def _display_file_list(self, files: list[Path]):
        self._file_list.configure(state="normal")
        self._file_list.delete("1.0", "end")

        setorflow_count = 0
        if not files:
            self._file_list.insert("end", "Nenhum setup encontrado.\n"
                                          "Use 'Escanear Pasta' ou o menu Setup.")
        else:
            for f in files:
                prefix = "⚡" if f.name.startswith("SetorFlow") else "📄"
                if f.name.startswith("SetorFlow"):
                    setorflow_count += 1
                self._file_list.insert("end", f" {prefix} {f.parent.name}/{f.name}\n")

        self._file_list.configure(state="disabled")
        self._val_total.set_value(str(len(files)))
        self._val_setorflow.set_value(str(setorflow_count))
        if files:
            self._val_folder.set_value(files[0].parent.name)

    def _display_setup_details(self, svm):
        self._details.configure(state="normal")
        self._details.delete("1.0", "end")
        if not svm:
            self._details.insert("end", "Nenhum setup carregado.")
            self._details.configure(state="disabled")
            return

        self._details.insert("end", f"Arquivo: {svm.filepath.name}\n")
        self._details.insert("end", f"Seções: {', '.join(svm.sections)}\n")
        self._details.insert("end", f"Simétrico: {'Sim' if svm.symmetric else 'Não'}\n")
        self._details.insert("end", f"Parâmetros: {len(svm.get_adjustable_params())}\n")
        self._details.insert("end", "─" * 45 + "\n")
        for p in svm.get_adjustable_params():
            self._details.insert(
                "end", f"  [{p.section}] {p.name} = {p.index} // {p.description}\n"
            )
        self._details.configure(state="disabled")
