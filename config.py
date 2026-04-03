"""
config.py — Configurações globais do LMU Virtual Engineer.

Gerencia caminhos, preferências do usuário e detecção automática
da instalação do Le Mans Ultimate. Todas as configurações são
salvas em um arquivo JSON local para persistência entre sessões.

Preparado para empacotamento .exe (PyInstaller):
- Usa sys._MEIPASS para detectar se está rodando como .exe
- Caminhos relativos ao executável quando empacotado
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import winreg
from pathlib import Path

logger = logging.getLogger("LMU_VE")

# ============================================================
# VERSÃO DO SOFTWARE
# ============================================================
APP_NAME = "LMU Virtual Engineer"
APP_VERSION = "1.0.0"
APP_AUTHOR = "LMU Virtual Engineer Team"

# ============================================================
# DETECÇÃO DE AMBIENTE (normal vs .exe empacotado)
# ============================================================
if getattr(sys, "frozen", False):
    # Rodando como .exe (PyInstaller)
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).parent
else:
    # Rodando como script Python normal
    BASE_DIR = Path(__file__).parent
    APP_DIR = BASE_DIR

# ============================================================
# DIRETÓRIOS DO APP
# ============================================================
# Dados do usuário ficam em AppData (não dentro do .exe)
USER_DATA_DIR = Path(os.environ.get("APPDATA", APP_DIR)) / "LMU_Virtual_Engineer"
DB_DIR = USER_DATA_DIR / "db"
MODELS_DIR = USER_DATA_DIR / "models"
SHARED_MODELS_DIR = MODELS_DIR / "_shared"
PROFILES_DIR = USER_DATA_DIR / "profiles"
BACKUPS_DIR = USER_DATA_DIR / "backups"
LOGS_DIR = USER_DATA_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"

# Arquivo de configuração do usuário
CONFIG_FILE = USER_DATA_DIR / "settings.json"
DB_FILE = DB_DIR / "lmu_engineer.db"

# ============================================================
# CAMINHOS PADRÃO DO STEAM / LMU
# ============================================================
STEAM_REGISTRY_KEY = r"SOFTWARE\Valve\Steam"
STEAM_REGISTRY_KEY_WOW64 = r"SOFTWARE\WOW6432Node\Valve\Steam"
LMU_STEAM_APP_ID = "2394510"
LMU_FOLDER_NAME = "Le Mans Ultimate"

# Caminhos comuns de instalação do Steam
STEAM_DEFAULT_PATHS = [
    Path("C:/Program Files (x86)/Steam"),
    Path("C:/Program Files/Steam"),
    Path("D:/Steam"),
    Path("D:/SteamLibrary"),
    Path("E:/Steam"),
    Path("E:/SteamLibrary"),
]


def _find_steam_path() -> Path | None:
    """Tenta encontrar o caminho do Steam via registro do Windows."""
    if platform.system() != "Windows":
        return None
    for key_path in (STEAM_REGISTRY_KEY, STEAM_REGISTRY_KEY_WOW64):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            steam = Path(install_path)
            if steam.exists():
                return steam
        except (OSError, FileNotFoundError):
            continue
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
            install_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
            steam = Path(install_path)
            if steam.exists():
                return steam
        except (OSError, FileNotFoundError):
            continue
    return None


def _find_steam_library_folders(steam_path: Path) -> list[Path]:
    """Lê libraryfolders.vdf para encontrar todas as pastas de bibliotecas Steam."""
    folders = [steam_path]
    vdf_file = steam_path / "steamapps" / "libraryfolders.vdf"
    if not vdf_file.exists():
        return folders
    try:
        content = vdf_file.read_text(encoding="utf-8")
        # Parser simplificado de VDF — busca linhas com "path"
        for line in content.splitlines():
            line = line.strip()
            if '"path"' in line.lower():
                parts = line.split('"')
                if len(parts) >= 4:
                    lib_path = Path(parts[3].replace("\\\\", "\\"))
                    if lib_path.exists() and lib_path not in folders:
                        folders.append(lib_path)
    except Exception:
        pass
    return folders


def detect_lmu_path() -> Path | None:
    """
    Detecta automaticamente o caminho de instalação do Le Mans Ultimate.
    Procura no registro do Windows, pastas padrão do Steam e bibliotecas.

    Returns:
        Path para a pasta raiz do LMU, ou None se não encontrado.
    """
    search_roots = []

    # 1. Tentar via registro do Windows
    steam_path = _find_steam_path()
    if steam_path:
        search_roots.extend(_find_steam_library_folders(steam_path))

    # 2. Adicionar caminhos padrão
    for default in STEAM_DEFAULT_PATHS:
        if default.exists() and default not in search_roots:
            search_roots.append(default)

    # 3. Procurar o LMU em cada biblioteca
    for root in search_roots:
        lmu_path = root / "steamapps" / "common" / LMU_FOLDER_NAME
        if lmu_path.exists():
            return lmu_path

    return None


def get_lmu_userdata_path(lmu_path: Path | None = None) -> Path | None:
    """
    Retorna o caminho da pasta UserData do LMU.
    É onde ficam os setups (.svm) e telemetria gravada.
    """
    if lmu_path is None:
        lmu_path = detect_lmu_path()
    if lmu_path is None:
        return None
    userdata = lmu_path / "UserData"
    if userdata.exists():
        return userdata
    return None


def get_setups_path(lmu_path: Path | None = None) -> Path | None:
    """Caminho da pasta de setups: UserData/player/Settings/"""
    userdata = get_lmu_userdata_path(lmu_path)
    if userdata is None:
        return None
    setups = userdata / "player" / "Settings"
    if setups.exists():
        return setups
    return None


def get_telemetry_path(lmu_path: Path | None = None) -> Path | None:
    """Caminho da pasta de telemetria gravada: UserData/Telemetry/"""
    userdata = get_lmu_userdata_path(lmu_path)
    if userdata is None:
        return None
    telemetry = userdata / "Telemetry"
    if telemetry.exists():
        return telemetry
    return None


# ============================================================
# CLASSE DE CONFIGURAÇÃO
# ============================================================
class AppConfig:
    """
    Gerenciador de configurações do aplicativo.
    Carrega/salva preferências em JSON.
    Preparado para acesso por múltiplos módulos.
    """

    _defaults = {
        "lmu_path": "",
        "setup_level": "basic",       # "basic", "intermediate", "advanced"
        "learning_laps": 10,          # Voltas mínimas antes da IA sugerir
        "auto_backup": True,          # Backup automático do .svm ao modificar
        "auto_backup_db": True,       # Backup do banco ao abrir o programa
        "telemetry_hz": 10,           # Frequência de leitura da telemetria (Hz)
        "training_interval": 5,       # Treinar IA a cada N voltas
        "training_batch_size": 16,    # Tamanho do batch de treinamento
        "training_epochs_online": 3,  # Épocas por treino online
        "training_epochs_offline": 50,# Épocas por treino offline
        "max_delta_per_adjust": 3,    # Máximo ±N índices por ajuste
        "transfer_learning": True,    # Usar Transfer Learning automático
        "compound_as_input": True,    # Compound de pneu como input da rede
        "dark_mode": True,            # Tema escuro
        "language": "pt-br",          # Idioma
        "driver_name": "Piloto",      # Nome do perfil do piloto
        "last_car": "",
        "last_track": "",
        "window_width": 1280,
        "window_height": 800,
        "openrouter_api_key": "",
        "openrouter_model": "deepseek/deepseek-chat-v3-0324",
        "llm_provider": "openrouter",
        "llm_custom_url": "",
    }

    def __init__(self):
        self._data: dict = {}
        self._ensure_dirs()
        self.load()

    def _ensure_dirs(self):
        """Cria os diretórios necessários se não existirem."""
        for d in (USER_DATA_DIR, DB_DIR, MODELS_DIR, SHARED_MODELS_DIR,
                  PROFILES_DIR, BACKUPS_DIR, LOGS_DIR):
            d.mkdir(parents=True, exist_ok=True)

    def load(self):
        """Carrega configurações do arquivo JSON."""
        self._data = dict(self._defaults)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Erro ao carregar config: %s. Usando padrões.", e)

        # Auto-detectar LMU se não configurado
        if not self._data["lmu_path"]:
            detected = detect_lmu_path()
            if detected:
                self._data["lmu_path"] = str(detected)
                logger.info("LMU detectado automaticamente: %s", detected)

    def save(self):
        """Salva configurações no arquivo JSON."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Erro ao salvar config: %s", e)

    def get(self, key: str, default=None):
        """Obtém uma configuração."""
        return self._data.get(key, default)

    def set(self, key: str, value):
        """Define uma configuração e salva automaticamente."""
        self._data[key] = value
        self.save()

    @property
    def lmu_path(self) -> Path | None:
        p = self._data.get("lmu_path", "")
        return Path(p) if p else None

    @property
    def setups_path(self) -> Path | None:
        return get_setups_path(self.lmu_path)

    @property
    def telemetry_path(self) -> Path | None:
        return get_telemetry_path(self.lmu_path)

    @property
    def setup_level(self) -> str:
        return self._data.get("setup_level", "basic")

    @property
    def max_delta(self) -> int:
        return self._data.get("max_delta_per_adjust", 3)
