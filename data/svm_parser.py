"""
svm_parser.py — Parser/Writer para arquivos .svm do rFactor 2 / Le Mans Ultimate.

Formato .svm:
  - Seções delimitadas por [NOME_SECAO]
  - Linhas de parâmetros: NomeSetting=INDICE//DESCRICAO
  - Linhas "Non-adjustable", "N/A", "Fixed", "Detached" são preservadas mas ignoradas
  - Symmetric=1 indica que L/R são simétricos
  - Seção [BASIC] contém sliders normalizados (0.0–1.0) — preservada intacta

Regras do parser:
  1. Formato: NomeSetting=INDICE//DESCRICAO
  2. Ignorar linhas com Non-adjustable, N/A, Fixed, Detached
  3. INDICE é sempre inteiro
  4. DESCRICAO é informativa; o valor salvo é o INDICE
  5. Seções entre [] são preservadas exatamente como estão
  6. Ao salvar, manter TODAS as linhas do arquivo original
  7. Fazer backup antes de salvar
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("LMU_VE.svm_parser")

# Palavras que indicam parâmetro não-ajustável
NON_ADJUSTABLE_MARKERS = frozenset({
    "non-adjustable", "n/a", "fixed", "detached",
})

# Regex para linhas de setting: NomeSetting=INDICE//DESCRICAO
SETTING_RE = re.compile(
    r"^(\w+Setting)\s*=\s*(\d+)\s*//\s*(.+)$",
    re.IGNORECASE,
)

# Regex para seções: [NOME]
SECTION_RE = re.compile(r"^\[(.+)]$")


@dataclass
class SetupParam:
    """Um parâmetro de setup ajustável."""
    section: str         # Ex: "FRONTLEFT", "REARWING"
    name: str            # Ex: "CamberSetting", "RWSetting"
    index: int           # Valor inteiro do índice atual
    description: str     # Texto descritivo (ex: "-2.2 deg")
    adjustable: bool     # Se é ajustável ou fixo
    line_number: int     # Linha no arquivo original (para substituição)

    @property
    def full_key(self) -> str:
        """Chave completa: SECAO.NomeSetting"""
        return f"{self.section}.{self.name}"


@dataclass
class SVMFile:
    """Representação completa de um arquivo .svm parseado."""
    filepath: Path
    raw_lines: list[str] = field(default_factory=list)
    params: dict[str, SetupParam] = field(default_factory=dict)  # chave = full_key
    sections: list[str] = field(default_factory=list)
    symmetric: bool = False

    def get_param(self, full_key: str) -> SetupParam | None:
        """Obtém parâmetro por chave completa (ex: 'FRONTLEFT.CamberSetting')."""
        return self.params.get(full_key)

    def get_section_params(self, section: str) -> list[SetupParam]:
        """Obtém todos os parâmetros de uma seção."""
        return [p for p in self.params.values() if p.section == section]

    def get_adjustable_params(self) -> list[SetupParam]:
        """Retorna apenas parâmetros ajustáveis."""
        return [p for p in self.params.values() if p.adjustable]

    def get_all_indices(self) -> dict[str, int]:
        """Retorna dict {full_key: index} de todos os parâmetros ajustáveis."""
        return {p.full_key: p.index for p in self.params.values() if p.adjustable}


def parse_svm(filepath: str | Path) -> SVMFile:
    """
    Lê e parseia um arquivo .svm.

    Args:
        filepath: Caminho para o arquivo .svm.

    Returns:
        SVMFile com todos os parâmetros parseados.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o formato for inválido.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Arquivo .svm não encontrado: {filepath}")

    raw_lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()

    svm = SVMFile(filepath=filepath, raw_lines=list(raw_lines))
    current_section = ""

    for line_num, line in enumerate(raw_lines):
        stripped = line.strip()

        # Detectar seção
        section_match = SECTION_RE.match(stripped)
        if section_match:
            current_section = section_match.group(1)
            if current_section not in svm.sections:
                svm.sections.append(current_section)
            continue

        # Ignorar linhas vazias e comentários
        if not stripped or stripped.startswith("//") or stripped.startswith("#"):
            continue

        # Detectar Symmetric
        if stripped.lower().startswith("symmetric"):
            if "=1" in stripped or "= 1" in stripped:
                svm.symmetric = True
            continue

        # Tentar parsear como setting
        setting_match = SETTING_RE.match(stripped)
        if setting_match:
            name = setting_match.group(1)
            index = int(setting_match.group(2))
            description = setting_match.group(3).strip()

            # Verificar se é ajustável
            desc_lower = description.lower()
            adjustable = not any(marker in desc_lower for marker in NON_ADJUSTABLE_MARKERS)

            param = SetupParam(
                section=current_section,
                name=name,
                index=index,
                description=description,
                adjustable=adjustable,
                line_number=line_num,
            )

            full_key = param.full_key
            svm.params[full_key] = param

    logger.info(
        "Parsed %s: %d seções, %d parâmetros (%d ajustáveis)",
        filepath.name,
        len(svm.sections),
        len(svm.params),
        len(svm.get_adjustable_params()),
    )
    return svm


def apply_deltas(svm: SVMFile, deltas: dict[str, int]) -> SVMFile:
    """
    Aplica deltas de ajuste ao setup.

    Args:
        svm: SVMFile parseado.
        deltas: Dict {full_key: delta_index}.
                Ex: {"REARWING.RWSetting": +2, "FRONTLEFT.CamberSetting": -1}

    Returns:
        SVMFile com os índices atualizados (modifica in-place e retorna).
    """
    for full_key, delta in deltas.items():
        param = svm.params.get(full_key)
        if param is None:
            logger.warning("Parâmetro não encontrado: %s", full_key)
            continue
        if not param.adjustable:
            logger.warning("Parâmetro não ajustável, ignorado: %s", full_key)
            continue
        if delta == 0:
            continue

        old_index = param.index
        new_index = old_index + delta
        # Limitar ao mínimo de 0 (índices SVM nunca são negativos)
        new_index = max(0, new_index)
        # Limitar ao máximo razoável por tipo de parâmetro
        # Parâmetros típicos: pressão ~60, mola ~40, camber ~30, asa ~20
        # Usar fator conservador: 3× o valor original ou 50, o que for maior
        max_reasonable = max(old_index * 3, 50) if old_index > 0 else 50
        new_index = min(new_index, max_reasonable)
        param.index = new_index

        # Atualizar a linha raw — substitui apenas o índice, preserva a descrição
        old_line = svm.raw_lines[param.line_number]
        new_line = re.sub(
            r"^(\w+Setting\s*=\s*)\d+(\s*//.*)$",
            rf"\g<1>{new_index}\2",
            old_line,
        )
        svm.raw_lines[param.line_number] = new_line

        logger.debug(
            "Delta aplicado: %s = %d → %d (Δ%+d)",
            full_key, old_index, new_index, delta,
        )

    return svm


def save_svm(svm: SVMFile, output_path: str | Path | None = None,
             backup: bool = True, backup_dir: str | Path | None = None) -> Path:
    """
    Salva o arquivo .svm (com backup automático do original).

    Args:
        svm: SVMFile com os dados a salvar.
        output_path: Caminho de saída. Se None, sobrescreve o original.
        backup: Se True, faz backup do arquivo original antes de salvar.
        backup_dir: Diretório para backups. Se None, usa a pasta do arquivo.

    Returns:
        Path do arquivo salvo.
    """
    output = Path(output_path) if output_path else svm.filepath

    # Backup
    if backup and output.exists():
        if backup_dir:
            bk_dir = Path(backup_dir)
            bk_dir.mkdir(parents=True, exist_ok=True)
        else:
            bk_dir = output.parent

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{output.stem}_backup_{timestamp}{output.suffix}"
        backup_path = bk_dir / backup_name
        shutil.copy2(output, backup_path)
        logger.info("Backup criado: %s", backup_path)

    # Salvar
    output.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(svm.raw_lines) + "\n"
    output.write_text(content, encoding="utf-8")
    logger.info("Setup salvo: %s", output)

    return output


def list_setup_files(setups_dir: str | Path) -> list[Path]:
    """
    Lista todos os arquivos .svm em uma pasta (e subpastas de pistas).

    Args:
        setups_dir: Diretório raiz dos setups.

    Returns:
        Lista de caminhos para arquivos .svm encontrados.
    """
    setups_dir = Path(setups_dir)
    if not setups_dir.exists():
        return []
    return sorted(setups_dir.rglob("*.svm"))


def list_track_folders(setups_dir: str | Path) -> list[Path]:
    """
    Lista as pastas de pista dentro do diretório de setups.

    A estrutura do LMU organiza setups por pista:
    Settings/<NomeDaPista>/*.svm

    Returns:
        Lista de caminhos para pastas de pista.
    """
    setups_dir = Path(setups_dir)
    if not setups_dir.exists():
        return []
    return sorted(
        p for p in setups_dir.iterdir()
        if p.is_dir() and any(p.glob("*.svm"))
    )


def build_param_conversion_table(svm: SVMFile) -> dict[str, dict]:
    """
    Constrói tabela de conversão índice→valor físico a partir das descrições.

    Tenta extrair o valor numérico da descrição (ex: "33//-2.2 deg" → -2.2).
    Útil para exibir na GUI o significado real de cada índice.

    Returns:
        Dict {full_key: {"index": int, "physical_value": float|None, "unit": str, "description": str}}
    """
    table = {}
    for param in svm.params.values():
        if not param.adjustable:
            continue

        entry = {
            "index": param.index,
            "physical_value": None,
            "unit": "",
            "description": param.description,
        }

        # Tentar extrair valor numérico e unidade da descrição
        # Exemplos: "-2.2 deg", "136 kPa", "110 kgf (92%)", "6.0 deg"
        num_match = re.search(r"(-?\d+\.?\d*)\s*(\w+)", param.description)
        if num_match:
            try:
                entry["physical_value"] = float(num_match.group(1))
                entry["unit"] = num_match.group(2)
            except (ValueError, IndexError):
                pass

        table[param.full_key] = entry

    return table
