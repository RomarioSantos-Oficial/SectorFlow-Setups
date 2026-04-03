"""
i18n.py — Sistema de internacionalização do Sector Flow Setups.

Gerencia traduções para múltiplos idiomas.
Idiomas suportados: pt-br, en, es, ja, zh
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger("SectorFlow.i18n")

# Idiomas disponíveis
AVAILABLE_LANGUAGES = {
    "pt-br": "Português (Brasil)",
    "en": "English",
    "es": "Español",
    "ja": "日本語",
    "zh": "中文",
}

# Traduções
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ═══════════════════════════════════════════════════════
    # PORTUGUÊS (padrão)
    # ═══════════════════════════════════════════════════════
    "pt-br": {
        # Geral
        "app_title": "Sector Flow Setups",
        "version": "Versão",
        "loading": "Carregando...",
        "save": "Salvar",
        "cancel": "Cancelar",
        "close": "Fechar",
        "apply": "Aplicar",
        "reset": "Resetar",
        "ok": "OK",
        "yes": "Sim",
        "no": "Não",
        "error": "Erro",
        "warning": "Aviso",
        "success": "Sucesso",
        "info": "Informação",
        
        # Abas principais
        "tab_setup": "Setup",
        "tab_telemetry": "Telemetria",
        "tab_feedback": "Feedback",
        "tab_data": "Dados",
        
        # Cabeçalho
        "weather_dry": "Seco",
        "weather_wet": "Molhado",
        "weather_mixed": "Misto",
        "track_temp": "Pista",
        "air_temp": "Ar",
        "lmu_status": "LMU",
        "ia_status": "IA",
        "waiting_connection": "Aguardando conexão com LMU...",
        "connected": "Conectado",
        "disconnected": "Desconectado",
        
        # Aba Setup - Chat
        "virtual_engineer": "Engenheiro Virtual",
        "ia_confidence": "Confiança da IA",
        "learning": "Aprendendo...",
        "samples": "amostras",
        "welcome_message": "Olá! Sou seu Engenheiro Virtual. 🏎",
        "welcome_description": "Me diga o que está sentindo no carro e eu vou sugerir ajustes no setup. Você pode:",
        "welcome_step1": "• Descrever um problema (ex: 'o carro está com understeer')",
        "welcome_step2": "• Clicar em uma frase sugerida abaixo",
        "welcome_step3": "• Usar os botões de ação ao lado",
        "welcome_start": "Comece carregando um arquivo .svm base no painel à direita!",
        "quick_suggestions": "Sugestões rápidas:",
        "input_placeholder": "Descreva o problema do carro ou digite um comando...",
        
        # Frases sugeridas
        "phrase_understeer_entry": "O carro está com understeer na entrada da curva",
        "phrase_oversteer_exit": "O carro está com oversteer na saída da curva",
        "phrase_slides_mid": "O carro escorrega muito no meio da curva",
        "phrase_unstable_high": "O carro está instável em alta velocidade",
        "phrase_front_overheat": "Os pneus dianteiros superaquecem rápido",
        "phrase_rear_cold": "Os pneus traseiros não chegam na temperatura",
        "phrase_tire_wear": "O desgaste dos pneus está muito alto",
        "phrase_wheel_lock": "O carro trava as rodas ao frear",
        "phrase_brakes_weak": "Os freios não estão parando o carro",
        "phrase_brake_pull": "O carro puxa para um lado ao frear",
        "phrase_spin_slow": "O carro patina na saída das curvas lentas",
        "phrase_traction_high": "Perco tração em curvas de alta velocidade",
        "phrase_rain_setup": "Preciso de um setup para chuva",
        "phrase_drying_track": "A pista está secando, quero ajustar",
        "phrase_more_speed": "Quero mais velocidade nas retas",
        "phrase_kerb_harsh": "O carro está muito duro nos meios-fios",
        "phrase_stable_setup": "Quero um setup mais estável e previsível",
        "phrase_fuel_high": "Estou gastando muito combustível",
        "phrase_bottoming": "O carro bate no chão (bottoming)",
        "phrase_wear_fast": "O desgaste dos pneus está muito rápido",
        
        # Setup Base
        "setup_base": "Setup Base",
        "no_setup_loaded": "Nenhum setup carregado",
        "load_svm": "Carregar .svm",
        "view_details": "Ver Detalhes",
        
        # Ações rápidas
        "quick_actions": "Ações Rápidas",
        "create_setup": "Criar Setup",
        "edit_setup": "Editar Setup",
        "ask_ia": "Pedir Sugestão IA",
        "use_heuristics": "Usar Heurísticas",
        
        # Sugestões de ajuste
        "adjustment_suggestions": "Sugestões de Ajuste",
        "aero": "Aerodinâmica",
        "rear_wing": "Asa Traseira (RW)",
        "springs": "Molas",
        "front_spring": "Mola Dianteira",
        "rear_spring": "Mola Traseira",
        "camber": "Camber",
        "front_camber": "Camber Diant.",
        "rear_camber": "Camber Tras.",
        "tire_pressure": "Pressão dos Pneus",
        "front_pressure": "Pressão Pneu D.",
        "rear_pressure": "Pressão Pneu T.",
        "apply_adjustments": "Aplicar Ajustes",
        
        # Telemetria
        "live_telemetry": "Telemetria Ao Vivo",
        "speed": "Velocidade",
        "rpm": "RPM",
        "gear": "Marcha",
        "throttle": "Acelerador",
        "brake": "Freio",
        "steering": "Volante",
        "lap_time": "Tempo de Volta",
        "best_lap": "Melhor Volta",
        "current_lap": "Volta Atual",
        "lap": "Volta",
        "sector": "Setor",
        "delta": "Delta",
        "fuel": "Combustível",
        "fuel_per_lap": "Comb./Volta",
        "laps_remaining": "Voltas Rest.",
        
        # Pneus
        "tires": "Pneus",
        "tire_temp": "Temperatura dos Pneus",
        "tire_wear": "Desgaste dos Pneus",
        "tire_pressure_live": "Pressão dos Pneus",
        "front_left": "DE",
        "front_right": "DD",
        "rear_left": "TE",
        "rear_right": "TD",
        "inner": "Int",
        "middle": "Med",
        "outer": "Ext",
        
        # Feedback
        "car_balance": "Balanço do Carro",
        "balance_desc": "Como o carro se comporta nas curvas?",
        "general_balance": "Balanço Geral",
        "understeer": "Understeer",
        "oversteer": "Oversteer",
        "slow_corners": "Curvas Lentas",
        "fast_corners": "Curvas Rápidas",
        "sub": "Sub",
        "over": "Sobre",
        "problem_zone": "Zona do Problema na Curva",
        "where_problem": "Onde o problema acontece?",
        "entry": "Entrada",
        "braking": "frenagem",
        "mid": "Meio",
        "apex": "ápice",
        "exit": "Saída",
        "acceleration": "aceleração",
        "car_feeling": "Sensação do Carro",
        "how_car_feels": "Como está se sentindo o carro?",
        "grip": "Grip",
        "low_grip": "Baixo",
        "high_grip": "Alto",
        "predictability": "Previsibilidade",
        "unpredictable": "Imprevisível",
        "predictable": "Previsível",
        "confidence": "Confiança",
        "not_confident": "Não confio",
        "confident": "Confio",
        "send_feedback": "Enviar Feedback",
        
        # Dados
        "database": "Banco de Dados",
        "sessions": "Sessões",
        "statistics": "Estatísticas",
        "export": "Exportar",
        "import": "Importar",
        "clear_data": "Limpar Dados",
        "total_laps": "Total de Voltas",
        "total_sessions": "Total de Sessões",
        "cars_driven": "Carros Pilotados",
        "tracks_driven": "Pistas",
        "models_trained": "Modelos Treinados",
        
        # Configurações
        "settings": "Configurações",
        "language": "Idioma",
        "theme": "Tema",
        "dark_mode": "Modo Escuro",
        "light_mode": "Modo Claro",
        "lmu_path": "Caminho do LMU",
        "detect_auto": "Detectar Automaticamente",
        "driver_name": "Nome do Piloto",
        "ia_settings": "Configurações da IA",
        "learning_laps": "Voltas para Aprender",
        "training_interval": "Intervalo de Treino",
        "auto_backup": "Backup Automático",
        
        # Mensagens
        "msg_setup_loaded": "Setup carregado com sucesso!",
        "msg_setup_created": "Novo setup criado!",
        "msg_setup_saved": "Setup salvo!",
        "msg_no_data": "Sem dados suficientes para sugestão.",
        "msg_need_laps": "Complete mais voltas para melhorar as sugestões.",
        "msg_ia_thinking": "A IA está analisando...",
        "msg_ia_ready": "Sugestões prontas!",
        "msg_feedback_sent": "Feedback registrado!",
        "msg_language_changed": "Idioma alterado! Reinicie o programa para aplicar.",
        "msg_restart_required": "Reinício necessário para aplicar as alterações.",
    },
    
    # ═══════════════════════════════════════════════════════
    # ENGLISH
    # ═══════════════════════════════════════════════════════
    "en": {
        # General
        "app_title": "Sector Flow Setups",
        "version": "Version",
        "loading": "Loading...",
        "save": "Save",
        "cancel": "Cancel",
        "close": "Close",
        "apply": "Apply",
        "reset": "Reset",
        "ok": "OK",
        "yes": "Yes",
        "no": "No",
        "error": "Error",
        "warning": "Warning",
        "success": "Success",
        "info": "Info",
        
        # Main tabs
        "tab_setup": "Setup",
        "tab_telemetry": "Telemetry",
        "tab_feedback": "Feedback",
        "tab_data": "Data",
        
        # Header
        "weather_dry": "Dry",
        "weather_wet": "Wet",
        "weather_mixed": "Mixed",
        "track_temp": "Track",
        "air_temp": "Air",
        "lmu_status": "LMU",
        "ia_status": "AI",
        "waiting_connection": "Waiting for LMU connection...",
        "connected": "Connected",
        "disconnected": "Disconnected",
        
        # Setup Tab - Chat
        "virtual_engineer": "Virtual Engineer",
        "ia_confidence": "AI Confidence",
        "learning": "Learning...",
        "samples": "samples",
        "welcome_message": "Hello! I'm your Virtual Engineer. 🏎",
        "welcome_description": "Tell me what you're feeling in the car and I'll suggest setup changes. You can:",
        "welcome_step1": "• Describe a problem (e.g., 'the car has understeer')",
        "welcome_step2": "• Click on a suggested phrase below",
        "welcome_step3": "• Use the action buttons on the side",
        "welcome_start": "Start by loading a base .svm file in the panel on the right!",
        "quick_suggestions": "Quick suggestions:",
        "input_placeholder": "Describe the car problem or type a command...",
        
        # Suggested phrases
        "phrase_understeer_entry": "The car has understeer on corner entry",
        "phrase_oversteer_exit": "The car has oversteer on corner exit",
        "phrase_slides_mid": "The car slides too much mid-corner",
        "phrase_unstable_high": "The car is unstable at high speed",
        "phrase_front_overheat": "The front tires overheat quickly",
        "phrase_rear_cold": "The rear tires don't reach temperature",
        "phrase_tire_wear": "Tire wear is too high",
        "phrase_wheel_lock": "The wheels lock up under braking",
        "phrase_brakes_weak": "The brakes aren't stopping the car",
        "phrase_brake_pull": "The car pulls to one side under braking",
        "phrase_spin_slow": "The car spins out of slow corners",
        "phrase_traction_high": "I lose traction in high-speed corners",
        "phrase_rain_setup": "I need a setup for rain",
        "phrase_drying_track": "The track is drying, I want to adjust",
        "phrase_more_speed": "I want more straight-line speed",
        "phrase_kerb_harsh": "The car is too harsh over kerbs",
        "phrase_stable_setup": "I want a more stable and predictable setup",
        "phrase_fuel_high": "I'm using too much fuel",
        "phrase_bottoming": "The car is bottoming out",
        "phrase_wear_fast": "Tire wear is too fast",
        
        # Base Setup
        "setup_base": "Base Setup",
        "no_setup_loaded": "No setup loaded",
        "load_svm": "Load .svm",
        "view_details": "View Details",
        
        # Quick actions
        "quick_actions": "Quick Actions",
        "create_setup": "Create Setup",
        "edit_setup": "Edit Setup",
        "ask_ia": "Ask AI Suggestion",
        "use_heuristics": "Use Heuristics",
        
        # Adjustment suggestions
        "adjustment_suggestions": "Adjustment Suggestions",
        "aero": "Aerodynamics",
        "rear_wing": "Rear Wing (RW)",
        "springs": "Springs",
        "front_spring": "Front Spring",
        "rear_spring": "Rear Spring",
        "camber": "Camber",
        "front_camber": "Front Camber",
        "rear_camber": "Rear Camber",
        "tire_pressure": "Tire Pressure",
        "front_pressure": "Front Pressure",
        "rear_pressure": "Rear Pressure",
        "apply_adjustments": "Apply Adjustments",
        
        # Telemetry
        "live_telemetry": "Live Telemetry",
        "speed": "Speed",
        "rpm": "RPM",
        "gear": "Gear",
        "throttle": "Throttle",
        "brake": "Brake",
        "steering": "Steering",
        "lap_time": "Lap Time",
        "best_lap": "Best Lap",
        "current_lap": "Current Lap",
        "lap": "Lap",
        "sector": "Sector",
        "delta": "Delta",
        "fuel": "Fuel",
        "fuel_per_lap": "Fuel/Lap",
        "laps_remaining": "Laps Rem.",
        
        # Tires
        "tires": "Tires",
        "tire_temp": "Tire Temperature",
        "tire_wear": "Tire Wear",
        "tire_pressure_live": "Tire Pressure",
        "front_left": "FL",
        "front_right": "FR",
        "rear_left": "RL",
        "rear_right": "RR",
        "inner": "In",
        "middle": "Mid",
        "outer": "Out",
        
        # Feedback
        "car_balance": "Car Balance",
        "balance_desc": "How does the car behave in corners?",
        "general_balance": "General Balance",
        "understeer": "Understeer",
        "oversteer": "Oversteer",
        "slow_corners": "Slow Corners",
        "fast_corners": "Fast Corners",
        "sub": "Under",
        "over": "Over",
        "problem_zone": "Problem Zone in Corner",
        "where_problem": "Where does the problem occur?",
        "entry": "Entry",
        "braking": "braking",
        "mid": "Mid",
        "apex": "apex",
        "exit": "Exit",
        "acceleration": "acceleration",
        "car_feeling": "Car Feeling",
        "how_car_feels": "How does the car feel?",
        "grip": "Grip",
        "low_grip": "Low",
        "high_grip": "High",
        "predictability": "Predictability",
        "unpredictable": "Unpredictable",
        "predictable": "Predictable",
        "confidence": "Confidence",
        "not_confident": "Not confident",
        "confident": "Confident",
        "send_feedback": "Send Feedback",
        
        # Data
        "database": "Database",
        "sessions": "Sessions",
        "statistics": "Statistics",
        "export": "Export",
        "import": "Import",
        "clear_data": "Clear Data",
        "total_laps": "Total Laps",
        "total_sessions": "Total Sessions",
        "cars_driven": "Cars Driven",
        "tracks_driven": "Tracks",
        "models_trained": "Models Trained",
        
        # Settings
        "settings": "Settings",
        "language": "Language",
        "theme": "Theme",
        "dark_mode": "Dark Mode",
        "light_mode": "Light Mode",
        "lmu_path": "LMU Path",
        "detect_auto": "Detect Automatically",
        "driver_name": "Driver Name",
        "ia_settings": "AI Settings",
        "learning_laps": "Learning Laps",
        "training_interval": "Training Interval",
        "auto_backup": "Auto Backup",
        
        # Messages
        "msg_setup_loaded": "Setup loaded successfully!",
        "msg_setup_created": "New setup created!",
        "msg_setup_saved": "Setup saved!",
        "msg_no_data": "Not enough data for suggestion.",
        "msg_need_laps": "Complete more laps to improve suggestions.",
        "msg_ia_thinking": "AI is analyzing...",
        "msg_ia_ready": "Suggestions ready!",
        "msg_feedback_sent": "Feedback recorded!",
        "msg_language_changed": "Language changed! Restart the program to apply.",
        "msg_restart_required": "Restart required to apply changes.",
    },
    
    # ═══════════════════════════════════════════════════════
    # ESPAÑOL
    # ═══════════════════════════════════════════════════════
    "es": {
        # General
        "app_title": "Sector Flow Setups",
        "version": "Versión",
        "loading": "Cargando...",
        "save": "Guardar",
        "cancel": "Cancelar",
        "close": "Cerrar",
        "apply": "Aplicar",
        "reset": "Reiniciar",
        "ok": "OK",
        "yes": "Sí",
        "no": "No",
        "error": "Error",
        "warning": "Advertencia",
        "success": "Éxito",
        "info": "Información",
        
        # Main tabs
        "tab_setup": "Setup",
        "tab_telemetry": "Telemetría",
        "tab_feedback": "Feedback",
        "tab_data": "Datos",
        
        # Header
        "weather_dry": "Seco",
        "weather_wet": "Mojado",
        "weather_mixed": "Mixto",
        "track_temp": "Pista",
        "air_temp": "Aire",
        "lmu_status": "LMU",
        "ia_status": "IA",
        "waiting_connection": "Esperando conexión con LMU...",
        "connected": "Conectado",
        "disconnected": "Desconectado",
        
        # Setup Tab - Chat
        "virtual_engineer": "Ingeniero Virtual",
        "ia_confidence": "Confianza de la IA",
        "learning": "Aprendiendo...",
        "samples": "muestras",
        "welcome_message": "¡Hola! Soy tu Ingeniero Virtual. 🏎",
        "welcome_description": "Dime lo que sientes en el coche y te sugeriré cambios de setup. Puedes:",
        "welcome_step1": "• Describir un problema (ej: 'el coche tiene subviraje')",
        "welcome_step2": "• Hacer clic en una frase sugerida abajo",
        "welcome_step3": "• Usar los botones de acción al lado",
        "welcome_start": "¡Empieza cargando un archivo .svm base en el panel de la derecha!",
        "quick_suggestions": "Sugerencias rápidas:",
        "input_placeholder": "Describe el problema del coche o escribe un comando...",
        
        # Suggested phrases
        "phrase_understeer_entry": "El coche tiene subviraje en la entrada de curva",
        "phrase_oversteer_exit": "El coche tiene sobreviraje a la salida de curva",
        "phrase_slides_mid": "El coche desliza mucho en el medio de la curva",
        "phrase_unstable_high": "El coche está inestable a alta velocidad",
        "phrase_front_overheat": "Los neumáticos delanteros se sobrecalientan rápido",
        "phrase_rear_cold": "Los neumáticos traseros no llegan a temperatura",
        "phrase_tire_wear": "El desgaste de neumáticos es muy alto",
        "phrase_wheel_lock": "Las ruedas se bloquean al frenar",
        "phrase_brakes_weak": "Los frenos no están parando el coche",
        "phrase_brake_pull": "El coche tira hacia un lado al frenar",
        "phrase_spin_slow": "El coche patina en la salida de curvas lentas",
        "phrase_traction_high": "Pierdo tracción en curvas de alta velocidad",
        "phrase_rain_setup": "Necesito un setup para lluvia",
        "phrase_drying_track": "La pista se está secando, quiero ajustar",
        "phrase_more_speed": "Quiero más velocidad en rectas",
        "phrase_kerb_harsh": "El coche es muy duro en los bordillos",
        "phrase_stable_setup": "Quiero un setup más estable y predecible",
        "phrase_fuel_high": "Estoy gastando mucho combustible",
        "phrase_bottoming": "El coche toca el suelo (bottoming)",
        "phrase_wear_fast": "El desgaste de neumáticos es muy rápido",
        
        # Base Setup
        "setup_base": "Setup Base",
        "no_setup_loaded": "Ningún setup cargado",
        "load_svm": "Cargar .svm",
        "view_details": "Ver Detalles",
        
        # Quick actions
        "quick_actions": "Acciones Rápidas",
        "create_setup": "Crear Setup",
        "edit_setup": "Editar Setup",
        "ask_ia": "Pedir Sugerencia IA",
        "use_heuristics": "Usar Heurísticas",
        
        # Adjustment suggestions
        "adjustment_suggestions": "Sugerencias de Ajuste",
        "aero": "Aerodinámica",
        "rear_wing": "Alerón Trasero (RW)",
        "springs": "Muelles",
        "front_spring": "Muelle Delantero",
        "rear_spring": "Muelle Trasero",
        "camber": "Camber",
        "front_camber": "Camber Del.",
        "rear_camber": "Camber Tras.",
        "tire_pressure": "Presión de Neumáticos",
        "front_pressure": "Presión Del.",
        "rear_pressure": "Presión Tras.",
        "apply_adjustments": "Aplicar Ajustes",
        
        # Telemetry
        "live_telemetry": "Telemetría en Vivo",
        "speed": "Velocidad",
        "rpm": "RPM",
        "gear": "Marcha",
        "throttle": "Acelerador",
        "brake": "Freno",
        "steering": "Volante",
        "lap_time": "Tiempo de Vuelta",
        "best_lap": "Mejor Vuelta",
        "current_lap": "Vuelta Actual",
        "lap": "Vuelta",
        "sector": "Sector",
        "delta": "Delta",
        "fuel": "Combustible",
        "fuel_per_lap": "Comb./Vuelta",
        "laps_remaining": "Vueltas Rest.",
        
        # Tires
        "tires": "Neumáticos",
        "tire_temp": "Temperatura de Neumáticos",
        "tire_wear": "Desgaste de Neumáticos",
        "tire_pressure_live": "Presión de Neumáticos",
        "front_left": "DI",
        "front_right": "DD",
        "rear_left": "TI",
        "rear_right": "TD",
        "inner": "Int",
        "middle": "Med",
        "outer": "Ext",
        
        # Feedback
        "car_balance": "Balance del Coche",
        "balance_desc": "¿Cómo se comporta el coche en las curvas?",
        "general_balance": "Balance General",
        "understeer": "Subviraje",
        "oversteer": "Sobreviraje",
        "slow_corners": "Curvas Lentas",
        "fast_corners": "Curvas Rápidas",
        "sub": "Sub",
        "over": "Sobre",
        "problem_zone": "Zona del Problema en Curva",
        "where_problem": "¿Dónde ocurre el problema?",
        "entry": "Entrada",
        "braking": "frenada",
        "mid": "Medio",
        "apex": "ápice",
        "exit": "Salida",
        "acceleration": "aceleración",
        "car_feeling": "Sensación del Coche",
        "how_car_feels": "¿Cómo se siente el coche?",
        "grip": "Agarre",
        "low_grip": "Bajo",
        "high_grip": "Alto",
        "predictability": "Predictibilidad",
        "unpredictable": "Impredecible",
        "predictable": "Predecible",
        "confidence": "Confianza",
        "not_confident": "No confío",
        "confident": "Confío",
        "send_feedback": "Enviar Feedback",
        
        # Data
        "database": "Base de Datos",
        "sessions": "Sesiones",
        "statistics": "Estadísticas",
        "export": "Exportar",
        "import": "Importar",
        "clear_data": "Limpiar Datos",
        "total_laps": "Total de Vueltas",
        "total_sessions": "Total de Sesiones",
        "cars_driven": "Coches Conducidos",
        "tracks_driven": "Circuitos",
        "models_trained": "Modelos Entrenados",
        
        # Settings
        "settings": "Configuración",
        "language": "Idioma",
        "theme": "Tema",
        "dark_mode": "Modo Oscuro",
        "light_mode": "Modo Claro",
        "lmu_path": "Ruta del LMU",
        "detect_auto": "Detectar Automáticamente",
        "driver_name": "Nombre del Piloto",
        "ia_settings": "Configuración de IA",
        "learning_laps": "Vueltas para Aprender",
        "training_interval": "Intervalo de Entrenamiento",
        "auto_backup": "Copia de Seguridad Auto",
        
        # Messages
        "msg_setup_loaded": "¡Setup cargado con éxito!",
        "msg_setup_created": "¡Nuevo setup creado!",
        "msg_setup_saved": "¡Setup guardado!",
        "msg_no_data": "Datos insuficientes para sugerencia.",
        "msg_need_laps": "Completa más vueltas para mejorar las sugerencias.",
        "msg_ia_thinking": "La IA está analizando...",
        "msg_ia_ready": "¡Sugerencias listas!",
        "msg_feedback_sent": "¡Feedback registrado!",
        "msg_language_changed": "¡Idioma cambiado! Reinicia el programa para aplicar.",
        "msg_restart_required": "Reinicio necesario para aplicar cambios.",
    },
    
    # ═══════════════════════════════════════════════════════
    # 日本語 (JAPANESE)
    # ═══════════════════════════════════════════════════════
    "ja": {
        # General
        "app_title": "Sector Flow Setups",
        "version": "バージョン",
        "loading": "読み込み中...",
        "save": "保存",
        "cancel": "キャンセル",
        "close": "閉じる",
        "apply": "適用",
        "reset": "リセット",
        "ok": "OK",
        "yes": "はい",
        "no": "いいえ",
        "error": "エラー",
        "warning": "警告",
        "success": "成功",
        "info": "情報",
        
        # Main tabs
        "tab_setup": "セットアップ",
        "tab_telemetry": "テレメトリ",
        "tab_feedback": "フィードバック",
        "tab_data": "データ",
        
        # Header
        "weather_dry": "ドライ",
        "weather_wet": "ウェット",
        "weather_mixed": "ミックス",
        "track_temp": "路面温度",
        "air_temp": "気温",
        "lmu_status": "LMU",
        "ia_status": "AI",
        "waiting_connection": "LMUへの接続を待機中...",
        "connected": "接続済み",
        "disconnected": "未接続",
        
        # Setup Tab - Chat
        "virtual_engineer": "バーチャルエンジニア",
        "ia_confidence": "AIの信頼度",
        "learning": "学習中...",
        "samples": "サンプル",
        "welcome_message": "こんにちは！私はあなたのバーチャルエンジニアです。🏎",
        "welcome_description": "車の感触を教えてください。セットアップの調整を提案します。次のことができます：",
        "welcome_step1": "• 問題を説明する（例：「車がアンダーステアです」）",
        "welcome_step2": "• 下の提案フレーズをクリックする",
        "welcome_step3": "• 横のアクションボタンを使用する",
        "welcome_start": "右側のパネルでベース.svmファイルを読み込んで開始してください！",
        "quick_suggestions": "クイック提案：",
        "input_placeholder": "車の問題を説明するか、コマンドを入力してください...",
        
        # Suggested phrases
        "phrase_understeer_entry": "コーナー進入でアンダーステアが出る",
        "phrase_oversteer_exit": "コーナー脱出でオーバーステアが出る",
        "phrase_slides_mid": "コーナー中盤で滑りすぎる",
        "phrase_unstable_high": "高速で不安定",
        "phrase_front_overheat": "フロントタイヤがすぐオーバーヒートする",
        "phrase_rear_cold": "リアタイヤが温まらない",
        "phrase_tire_wear": "タイヤ摩耗が激しい",
        "phrase_wheel_lock": "ブレーキングでホイールがロックする",
        "phrase_brakes_weak": "ブレーキが効かない",
        "phrase_brake_pull": "ブレーキング時に片側に引っ張られる",
        "phrase_spin_slow": "低速コーナー脱出でスピンする",
        "phrase_traction_high": "高速コーナーでトラクションを失う",
        "phrase_rain_setup": "雨用セットアップが必要",
        "phrase_drying_track": "路面が乾いてきた、調整したい",
        "phrase_more_speed": "ストレートスピードを上げたい",
        "phrase_kerb_harsh": "縁石で硬すぎる",
        "phrase_stable_setup": "より安定した予測可能なセットアップが欲しい",
        "phrase_fuel_high": "燃費が悪い",
        "phrase_bottoming": "ボトミングが発生している",
        "phrase_wear_fast": "タイヤ摩耗が速すぎる",
        
        # Base Setup
        "setup_base": "ベースセットアップ",
        "no_setup_loaded": "セットアップ未読込",
        "load_svm": ".svmを読込",
        "view_details": "詳細表示",
        
        # Quick actions
        "quick_actions": "クイックアクション",
        "create_setup": "セットアップ作成",
        "edit_setup": "セットアップ編集",
        "ask_ia": "AI提案を求める",
        "use_heuristics": "ヒューリスティクス使用",
        
        # Adjustment suggestions
        "adjustment_suggestions": "調整提案",
        "aero": "エアロダイナミクス",
        "rear_wing": "リアウィング (RW)",
        "springs": "スプリング",
        "front_spring": "フロントスプリング",
        "rear_spring": "リアスプリング",
        "camber": "キャンバー",
        "front_camber": "フロントキャンバー",
        "rear_camber": "リアキャンバー",
        "tire_pressure": "タイヤ空気圧",
        "front_pressure": "フロント圧",
        "rear_pressure": "リア圧",
        "apply_adjustments": "調整を適用",
        
        # Telemetry
        "live_telemetry": "ライブテレメトリ",
        "speed": "速度",
        "rpm": "回転数",
        "gear": "ギア",
        "throttle": "スロットル",
        "brake": "ブレーキ",
        "steering": "ステアリング",
        "lap_time": "ラップタイム",
        "best_lap": "ベストラップ",
        "current_lap": "現在のラップ",
        "lap": "ラップ",
        "sector": "セクター",
        "delta": "デルタ",
        "fuel": "燃料",
        "fuel_per_lap": "燃料/ラップ",
        "laps_remaining": "残りラップ",
        
        # Tires
        "tires": "タイヤ",
        "tire_temp": "タイヤ温度",
        "tire_wear": "タイヤ摩耗",
        "tire_pressure_live": "タイヤ空気圧",
        "front_left": "左前",
        "front_right": "右前",
        "rear_left": "左後",
        "rear_right": "右後",
        "inner": "内",
        "middle": "中",
        "outer": "外",
        
        # Feedback
        "car_balance": "車のバランス",
        "balance_desc": "コーナーでの車の挙動は？",
        "general_balance": "全体バランス",
        "understeer": "アンダー",
        "oversteer": "オーバー",
        "slow_corners": "低速コーナー",
        "fast_corners": "高速コーナー",
        "sub": "アンダー",
        "over": "オーバー",
        "problem_zone": "コーナーの問題ゾーン",
        "where_problem": "問題が発生する場所は？",
        "entry": "進入",
        "braking": "ブレーキング",
        "mid": "中盤",
        "apex": "エイペックス",
        "exit": "脱出",
        "acceleration": "加速",
        "car_feeling": "車の感触",
        "how_car_feels": "車の感触は？",
        "grip": "グリップ",
        "low_grip": "低い",
        "high_grip": "高い",
        "predictability": "予測性",
        "unpredictable": "不安定",
        "predictable": "安定",
        "confidence": "信頼感",
        "not_confident": "信頼できない",
        "confident": "信頼できる",
        "send_feedback": "フィードバック送信",
        
        # Data
        "database": "データベース",
        "sessions": "セッション",
        "statistics": "統計",
        "export": "エクスポート",
        "import": "インポート",
        "clear_data": "データクリア",
        "total_laps": "総ラップ数",
        "total_sessions": "総セッション数",
        "cars_driven": "走行車両",
        "tracks_driven": "サーキット",
        "models_trained": "訓練済みモデル",
        
        # Settings
        "settings": "設定",
        "language": "言語",
        "theme": "テーマ",
        "dark_mode": "ダークモード",
        "light_mode": "ライトモード",
        "lmu_path": "LMUパス",
        "detect_auto": "自動検出",
        "driver_name": "ドライバー名",
        "ia_settings": "AI設定",
        "learning_laps": "学習ラップ数",
        "training_interval": "訓練間隔",
        "auto_backup": "自動バックアップ",
        
        # Messages
        "msg_setup_loaded": "セットアップを読み込みました！",
        "msg_setup_created": "新しいセットアップを作成しました！",
        "msg_setup_saved": "セットアップを保存しました！",
        "msg_no_data": "提案に十分なデータがありません。",
        "msg_need_laps": "提案を改善するためにもっとラップを走行してください。",
        "msg_ia_thinking": "AIが分析中...",
        "msg_ia_ready": "提案準備完了！",
        "msg_feedback_sent": "フィードバックを記録しました！",
        "msg_language_changed": "言語を変更しました！適用するにはプログラムを再起動してください。",
        "msg_restart_required": "変更を適用するには再起動が必要です。",
    },
    
    # ═══════════════════════════════════════════════════════
    # 中文 (CHINESE)
    # ═══════════════════════════════════════════════════════
    "zh": {
        # General
        "app_title": "Sector Flow Setups",
        "version": "版本",
        "loading": "加载中...",
        "save": "保存",
        "cancel": "取消",
        "close": "关闭",
        "apply": "应用",
        "reset": "重置",
        "ok": "确定",
        "yes": "是",
        "no": "否",
        "error": "错误",
        "warning": "警告",
        "success": "成功",
        "info": "信息",
        
        # Main tabs
        "tab_setup": "设定",
        "tab_telemetry": "遥测",
        "tab_feedback": "反馈",
        "tab_data": "数据",
        
        # Header
        "weather_dry": "干燥",
        "weather_wet": "湿滑",
        "weather_mixed": "混合",
        "track_temp": "赛道温度",
        "air_temp": "气温",
        "lmu_status": "LMU",
        "ia_status": "AI",
        "waiting_connection": "等待连接LMU...",
        "connected": "已连接",
        "disconnected": "未连接",
        
        # Setup Tab - Chat
        "virtual_engineer": "虚拟工程师",
        "ia_confidence": "AI置信度",
        "learning": "学习中...",
        "samples": "样本",
        "welcome_message": "你好！我是你的虚拟工程师。🏎",
        "welcome_description": "告诉我你在车上的感觉，我会建议设定调整。你可以：",
        "welcome_step1": "• 描述问题（例如：'车子转向不足'）",
        "welcome_step2": "• 点击下方的建议短语",
        "welcome_step3": "• 使用侧边的操作按钮",
        "welcome_start": "首先在右侧面板加载一个基础.svm文件！",
        "quick_suggestions": "快速建议：",
        "input_placeholder": "描述车辆问题或输入命令...",
        
        # Suggested phrases
        "phrase_understeer_entry": "入弯时转向不足",
        "phrase_oversteer_exit": "出弯时转向过度",
        "phrase_slides_mid": "弯中滑动太多",
        "phrase_unstable_high": "高速时不稳定",
        "phrase_front_overheat": "前轮过热太快",
        "phrase_rear_cold": "后轮无法达到温度",
        "phrase_tire_wear": "轮胎磨损太高",
        "phrase_wheel_lock": "刹车时车轮锁死",
        "phrase_brakes_weak": "刹车制动力不足",
        "phrase_brake_pull": "刹车时车辆偏向一侧",
        "phrase_spin_slow": "慢弯出口打滑",
        "phrase_traction_high": "高速弯失去抓地力",
        "phrase_rain_setup": "需要雨天设定",
        "phrase_drying_track": "赛道正在变干，想要调整",
        "phrase_more_speed": "想要更高的直道速度",
        "phrase_kerb_harsh": "过路肩时太硬",
        "phrase_stable_setup": "想要更稳定可预测的设定",
        "phrase_fuel_high": "油耗太高",
        "phrase_bottoming": "车辆触底（底盘触地）",
        "phrase_wear_fast": "轮胎磨损太快",
        
        # Base Setup
        "setup_base": "基础设定",
        "no_setup_loaded": "未加载设定",
        "load_svm": "加载.svm",
        "view_details": "查看详情",
        
        # Quick actions
        "quick_actions": "快速操作",
        "create_setup": "创建设定",
        "edit_setup": "编辑设定",
        "ask_ia": "请求AI建议",
        "use_heuristics": "使用启发式",
        
        # Adjustment suggestions
        "adjustment_suggestions": "调整建议",
        "aero": "空气动力学",
        "rear_wing": "后翼 (RW)",
        "springs": "弹簧",
        "front_spring": "前弹簧",
        "rear_spring": "后弹簧",
        "camber": "外倾角",
        "front_camber": "前外倾角",
        "rear_camber": "后外倾角",
        "tire_pressure": "轮胎气压",
        "front_pressure": "前轮气压",
        "rear_pressure": "后轮气压",
        "apply_adjustments": "应用调整",
        
        # Telemetry
        "live_telemetry": "实时遥测",
        "speed": "速度",
        "rpm": "转速",
        "gear": "档位",
        "throttle": "油门",
        "brake": "刹车",
        "steering": "转向",
        "lap_time": "圈速",
        "best_lap": "最佳圈速",
        "current_lap": "当前圈",
        "lap": "圈",
        "sector": "扇区",
        "delta": "差距",
        "fuel": "燃油",
        "fuel_per_lap": "燃油/圈",
        "laps_remaining": "剩余圈数",
        
        # Tires
        "tires": "轮胎",
        "tire_temp": "轮胎温度",
        "tire_wear": "轮胎磨损",
        "tire_pressure_live": "轮胎气压",
        "front_left": "左前",
        "front_right": "右前",
        "rear_left": "左后",
        "rear_right": "右后",
        "inner": "内",
        "middle": "中",
        "outer": "外",
        
        # Feedback
        "car_balance": "车辆平衡",
        "balance_desc": "车辆在弯道中的表现如何？",
        "general_balance": "整体平衡",
        "understeer": "转向不足",
        "oversteer": "转向过度",
        "slow_corners": "慢弯",
        "fast_corners": "快弯",
        "sub": "不足",
        "over": "过度",
        "problem_zone": "弯道问题区域",
        "where_problem": "问题发生在哪里？",
        "entry": "入弯",
        "braking": "制动",
        "mid": "弯中",
        "apex": "弯心",
        "exit": "出弯",
        "acceleration": "加速",
        "car_feeling": "车辆感觉",
        "how_car_feels": "车辆感觉如何？",
        "grip": "抓地力",
        "low_grip": "低",
        "high_grip": "高",
        "predictability": "可预测性",
        "unpredictable": "不可预测",
        "predictable": "可预测",
        "confidence": "信心",
        "not_confident": "没信心",
        "confident": "有信心",
        "send_feedback": "发送反馈",
        
        # Data
        "database": "数据库",
        "sessions": "会话",
        "statistics": "统计",
        "export": "导出",
        "import": "导入",
        "clear_data": "清除数据",
        "total_laps": "总圈数",
        "total_sessions": "总会话数",
        "cars_driven": "驾驶车辆",
        "tracks_driven": "赛道",
        "models_trained": "已训练模型",
        
        # Settings
        "settings": "设置",
        "language": "语言",
        "theme": "主题",
        "dark_mode": "深色模式",
        "light_mode": "浅色模式",
        "lmu_path": "LMU路径",
        "detect_auto": "自动检测",
        "driver_name": "车手姓名",
        "ia_settings": "AI设置",
        "learning_laps": "学习圈数",
        "training_interval": "训练间隔",
        "auto_backup": "自动备份",
        
        # Messages
        "msg_setup_loaded": "设定加载成功！",
        "msg_setup_created": "新设定已创建！",
        "msg_setup_saved": "设定已保存！",
        "msg_no_data": "数据不足，无法建议。",
        "msg_need_laps": "完成更多圈数以改善建议。",
        "msg_ia_thinking": "AI正在分析...",
        "msg_ia_ready": "建议已准备好！",
        "msg_feedback_sent": "反馈已记录！",
        "msg_language_changed": "语言已更改！重启程序以应用。",
        "msg_restart_required": "需要重启以应用更改。",
    },
}


class I18n:
    """Gerenciador de internacionalização."""
    
    _instance: Optional["I18n"] = None
    _current_lang: str = "pt-br"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass
    
    @classmethod
    def set_language(cls, lang: str) -> bool:
        """Define o idioma atual."""
        if lang in TRANSLATIONS:
            cls._current_lang = lang
            logger.info("Idioma definido para: %s", lang)
            return True
        logger.warning("Idioma não suportado: %s", lang)
        return False
    
    @classmethod
    def get_language(cls) -> str:
        """Retorna o idioma atual."""
        return cls._current_lang
    
    @classmethod
    def t(cls, key: str, **kwargs) -> str:
        """
        Traduz uma chave para o idioma atual.
        
        Args:
            key: Chave de tradução
            **kwargs: Variáveis para interpolação
            
        Returns:
            Texto traduzido ou a chave se não encontrado
        """
        lang = cls._current_lang
        
        # Tenta no idioma atual
        if lang in TRANSLATIONS and key in TRANSLATIONS[lang]:
            text = TRANSLATIONS[lang][key]
        # Fallback para português
        elif key in TRANSLATIONS["pt-br"]:
            text = TRANSLATIONS["pt-br"][key]
        else:
            logger.debug("Chave de tradução não encontrada: %s", key)
            return key
        
        # Interpolação de variáveis
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    @classmethod
    def get_available_languages(cls) -> Dict[str, str]:
        """Retorna dicionário de idiomas disponíveis."""
        return AVAILABLE_LANGUAGES.copy()


# Atalho para tradução
def _(key: str, **kwargs) -> str:
    """Atalho para I18n.t()"""
    return I18n.t(key, **kwargs)


# Função para inicializar com config
def init_i18n(language: str = "pt-br"):
    """Inicializa o sistema de i18n com o idioma especificado."""
    I18n.set_language(language)
