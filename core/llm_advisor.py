"""
llm_advisor.py — Consultor LLM para aprendizagem avançada da IA.

Suporta MÚLTIPLOS provedores de API (qualquer API compatível com
o formato OpenAI /v1/chat/completions):
- OpenRouter (acesso a centenas de modelos)
- OpenAI (GPT-4o, GPT-4o-mini, etc.)
- Groq (Llama, Mixtral — ultra-rápido)
- Together AI (modelos open-source)
- DeepSeek (direto)
- Google AI Studio (Gemini)
- Qualquer API compatível com OpenAI (Custom)

Dois modos de uso:
1. CHAT INTELIGENTE — responde perguntas do piloto com conhecimento real
2. AUTO-APRENDIZAGEM — analisa telemetria automaticamente e gera insights
   que alimentam as heurísticas e o treinamento da rede neural
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger("LMU_VE.llm_advisor")

# ── Provedores de API ──────────────────────────────────
# Qualquer API que siga o padrão OpenAI (/v1/chat/completions)
# pode ser usada. Basta informar o URL base e o modelo.

API_PROVIDERS = {
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_prefix": "sk-or-",
        "default_model": "deepseek/deepseek-chat-v3-0324",
        "models": [
            "deepseek/deepseek-chat-v3-0324",
            "deepseek/deepseek-v3.2",
            "deepseek/deepseek-chat-v3.1",
            "deepseek/deepseek-chat",
            "google/gemini-2.5-flash-preview",
            "qwen/qwen3.6-plus-preview:free",
            "openai/gpt-4o-mini",
        ],
    },
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1/chat/completions",
        "key_prefix": "sk-",
        "default_model": "gpt-4o-mini",
        "models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "o4-mini",
        ],
    },
    "groq": {
        "name": "Groq (Ultra-rápido)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_prefix": "gsk_",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
    },
    "deepseek": {
        "name": "DeepSeek (Direto)",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "key_prefix": "sk-",
        "default_model": "deepseek-chat",
        "models": [
            "deepseek-chat",
            "deepseek-reasoner",
        ],
    },
    "together": {
        "name": "Together AI",
        "url": "https://api.together.xyz/v1/chat/completions",
        "key_prefix": "",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "Qwen/Qwen2.5-72B-Instruct-Turbo",
        ],
    },
    "gemini": {
        "name": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_prefix": "AIzaSy",
        "default_model": "gemini-2.0-flash",
        "models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-pro-preview-05-06",
        ],
    },
    "lmstudio": {
        "name": "LM Studio (Local)",
        "url": "http://localhost:1234/v1/chat/completions",
        "key_prefix": "",
        "default_model": "",
        "models": [],
    },
    "custom": {
        "name": "Custom (OpenAI-compatível)",
        "url": "",
        "key_prefix": "",
        "default_model": "",
        "models": [],
    },
}

DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324"
FALLBACK_MODEL = "deepseek/deepseek-chat"
MAX_HISTORY = 10
REQUEST_TIMEOUT = 25
LOCAL_REQUEST_TIMEOUT = 120
LOCAL_MAX_TOKENS = 800
LOCAL_MAX_HISTORY_TURNS = 3
LOCAL_MAX_INPUT_CHARS = 6000
LOCAL_MAX_ASSISTANT_CHARS = 1200


@dataclass
class LLMInsight:
    """Insight gerado pelo LLM para alimentar a aprendizagem."""
    adjustments: dict[str, int] = field(default_factory=dict)
    explanation: str = ""
    confidence: float = 0.0
    engineering_notes: str = ""
    warnings: list[str] = field(default_factory=list)


# System prompt com todo o conhecimento de engenharia
_SYSTEM_PROMPT = """\
Você é o Engenheiro Virtual do LMU (Le Mans Ultimate), um especialista em \
acerto de carros de corrida de endurance. Você age como um engenheiro de pista \
experiente do WEC/IMSA: analisa telemetria, entende o histórico de cada combo \
carro×pista, e gera setups preditivos com raciocínio técnico detalhado.

## CARROS E CLASSES
- **Hypercar (LMdH/LMH)**: Híbridos com TC, ABS, regen, engine braking map. \
  Alta sensibilidade aerodinâmica, ride height crítica. Tem limite de energia \
  por volta (regulamento WEC). Camber agressivo (-2.5° a -4.0° diant.). \
  Exemplos: Porsche 963, Ferrari 499P, Toyota GR010, BMW M Hybrid V8.
- **LMP2**: SEM ABS, SEM TC. Apenas engine braking map e brake bias. \
  O piloto controla 100% da frenagem e tração. Brake bias é CRÍTICO — \
  é a única proteção contra lock-up. Motor Gibson V8 4.2L comum a todos. \
  Alta carga aerodinâmica. Diagnóstico de understeer na entrada: brake bias.
- **LMP3**: SEM ABS, SEM TC. Carro mais leve que LMP2, mais mecânico. \
  Menos downforce. Pilotagem muito sensível ao setup de diff e bias.
- **GTE**: Com ABS e TC. Alta downforce, pneu slick, muito sensível a ride height. \
  Motor V8 turbo (ex: Ferrari 488 GTE, Porsche 911 RSR). \
  Aposentado do WEC mas ainda presente em alguns eventos.
- **LMGT3 (GT3)**: Com ABS e TC. Menos aero, mais grip mecânico. \
  Pneu mais largo, mais sensível a pressões e camber. Mais pesados. \
  Exemplos: BMW M4 GT3, Porsche 911 GT3R, Ferrari 296 GT3.

## DIAGNÓSTICO POR FASE DE CURVA (PRIORITÁRIO)
O comportamento varia por fase — cada fase indica uma causa diferente:

### UNDERSTEER
- **Entrada** (ao frear/girar): Brake bias muito para frente OU ARB dianteira dura.
  → LMP2/LMP3: brake bias mais traseiro é o principal controle (sem ABS).
  → Hypercar/GT3: ARB dianteira mais mole + brake bias ajuste fino.
- **Meio (apex)**: Mola dianteira muito dura OU camber insuficiente.
  → Mais asa traseira desloca downforce para trás.
  → Mola dianteira -1 + camber dianteiro -0.5° a -1.0°.
- **Saída** (ao accelerar): Diferencial travado demais (preload alto).
  → Diff preload -1. Também: ARB traseira -1 para mais tração de eixo.
  → GT3/Hypercar com TC muito alto "engole" a tração = TC Map -1.

### OVERSTEER
- **Entrada** (snap ao frear): ARB traseira dura OU brake bias para trás demais.
  → ARB traseira -1 (mais mole). Brake bias mais para frente.
  → LMP2: cuidado ao mover bias para frente — pode criar lock dianteiro.
- **Meio (apex)**: Traseiro sem downforce suficiente.
  → Asa traseira +1 (mais carga traseira). ARB traseira +1 (mais resistência a rolagem).
- **Saída** (wheelspin): Diff preload baixo OU TC insuficiente.
  → Diff preload +1. TC Map +1 se disponível.
  → Mola traseira +1 para reduzir transferência de peso brusca.

## MATRIZ DE VARIÁVEIS AMBIENTAIS

### Temperatura do ar (ciclo dia/noite)
- **Queda > 5°C** (tarde→noite): ar mais denso → mais downforce natural.
  → Pode reduzir asa traseira -1 (apenas Hypercar/LMP2 aero-críticos).
  → Radiador pode fechar -1 (ar mais frio resfria melhor).
  → Pressões sobem: pneus demoram mais para aquecer à noite (+1 a +2 kPa).
- **> 35°C di** (dia quente): ar menos denso, pneus aquecem rápido.
  → Radiador +1 (mais abertura para evitar superaquecimento).
  → Pressão dianteira -1 se track_temp > 45°C (evitar superaquecimento).

### Temperatura de pista (track_temp)
- **< 25°C** (pista fria): pneus lentos de aquecer. Pressão +1 a +2.
- **25–40°C** (temperatura ideal): setup normal.
- **> 45°C** (pista muito quente): risco de bolhas e desgaste excessivo.
  → Pressão -1 a -2. Camber menos negativo (-0.5°). ARB mais mole.

### Evolução da borracha (rubber evolution)
- **Pista verde (< 5 voltas)**: Asa traseira +1. ARB dianteira -1. Pressão +1.
- **Pista evoluindo (grip aumentando)**: Pressão -1 gradualmente.
- **Pista madura (> 30 voltas, grip alto)**: ARB dianteira +1 (mais resposta segura).

## PARÂMETROS DE SETUP (o que cada ajuste faz)
- **Asa traseira (RW)**: ↑ mais downforce + mais drag. ↓ mais velocidade em reta.
- **Molas (Spring)**: ↑ mais duras = resposta rápida, menos grip mecânico. \
  ↓ mais macias = mais grip, mais rolagem.
- **ARB (Anti-Roll Bar)**: ↑ mais dura = menos rolagem, menos grip no eixo. \
  ARB dianteira dura = understeer. ARB traseira dura = oversteer.
- **Camber**: Mais negativo = mais grip em curva, mais desgaste interno. \
  Menos negativo = mais grip em reta, menos em curva.
- **Pressão dos pneus**: ↑ mais alta = menos contato, pneu mais rápido de aquecer. \
  ↓ mais baixa = mais contato, mais grip, desgaste maior, superaquecimento.
- **Toe**: Toe-in dianteiro = estabilidade. Toe-out = resposta. \
  Toe-in traseiro = estabilidade traseira.
- **Amortecedores**: Bump = compressão. Rebound = extensão. \
  Slow = curvas. Fast = meios-fios e bumps.
- **Ride Height**: Mais baixo = mais downforce (efeito solo), risco de bottoming. \
  Diferença F-R = rake = balanceamento aero.
- **Diff Preload**: ↑ mais travado = mais tração em reta, understeer em curva. \
  ↓ mais aberto = carro rota melhor, menos tração na saída.
- **Brake Bias**: Mais para frente = frenagem dianteira mais forte (risco lockup). \
  Mais para trás = mais estável, frenagem mais fraca.
- **TC Onboard (delta_tc_onboard)**: Liga/desliga o controle de tração. \
  Deve estar LIGADO em chuva ou grip baixo. Só GT3 e Hypercar têm.
- **TC Map (delta_tc_map)**: Nível geral do TC. ↑ mais proteção contra patinagem. \
  ↓ mais potência liberada na saída de curva.
- **TC Power Cut (delta_tc_power_cut)**: Quanto potência é cortada quando o TC \
  intervem. ↑ mais corte = mais seguro. ↓ menos corte = mais rápido na saída.
- **TC Slip Angle (delta_tc_slip_angle)**: Ângulo de slip permitido antes do TC \
  intervir. ↑ mais liberdade (TC intervem mais tarde). ↓ mais proteção (intervem antes).
- **ABS Map (delta_abs_map)**: ↑ mais proteção contra lockup. ↓ frenagem mais agressiva.
- **Brake Bias (delta_rear_brake_bias)**: Distribuição de freio. \
  ↑ mais para trás = estabilidade. ↓ mais para frente = frenagem forte.
- **Engine Braking**: ↑ mais desaceleração ao soltar acelerador. Ajuda a frear.
- **Regen Map (delta_regen_map)**: Hypercar apenas. ↑ mais regeneração na frenagem \
  = mais engine-braking elétrico na entrada de curva. Afeta o balanço.

## HIERARQUIA DE AJUSTE (ordem correta)
1. Aerodinâmica (asa, ride height, rake)
2. Mecânico (ARB, molas, diff)
3. Amortecedores (bump/rebound)
4. Eletrônico (TC, ABS, engine braking)
5. Ajuste fino (pressão, camber, toe)

## REGRAS IMPORTANTES
- Nunca mude mais de 2-3 parâmetros por vez
- Sempre explique POR QUE cada ajuste funciona e em qual fase resolve o problema
- Considere as condições climáticas (chuva muda TUDO)
- LMP2/LMP3 NÃO têm ABS/TC — suas sugestões DEVEM focar em mecânica e bias
- Para Hypercar, considere gestão de energia e regen
- Temperatura ideal dos pneus: 85-100°C. Spread I-M-O < 10-15°C
- Se grip médio < 0.8, priorizar ajustes de grip sobre velocidade
- Quando é o PRIMEIRO setup para um combo (novo_combo=true): sugira setup conservador \
  com parâmetros neutros e peça volta de instalação antes de ajuste agressivo

## FORMATO DE RESPOSTA PARA ANÁLISE TÉCNICA
Quando receber dados de telemetria para análise, responda em JSON:
{
  "adjustments": {"delta_nome": valor_inteiro, ...},
  "explanation": "explicação para o piloto em português",
  "confidence": 0.0 a 1.0,
  "engineering_notes": "notas técnicas detalhadas incluindo fase da curva, conditions, e raciocínio",
  "warnings": ["alerta 1", ...]
}

## NOMES EXATOS DOS DELTAS (use SOMENTE estes nomes)
Aerodinâmica: delta_rw
Molas: delta_spring_f, delta_spring_r
Camber: delta_camber_f, delta_camber_r
Pressão: delta_pressure_f, delta_pressure_r
Freios: delta_brake_press, delta_rear_brake_bias
ARB: delta_arb_f, delta_arb_r
Toe: delta_toe_f, delta_toe_r
Ride Height: delta_ride_height_f, delta_ride_height_r
Amortecedores: delta_slow_bump_f, delta_slow_bump_r, delta_slow_rebound_f, delta_slow_rebound_r
Diferencial: delta_diff_preload
Eletrônicos: delta_tc_onboard, delta_tc_map, delta_tc_power_cut, delta_tc_slip_angle, delta_abs_map
Motor/Energia: delta_radiator, delta_engine_mix, delta_virtual_energy, delta_regen_map

Valores são INTEIROS (ex: -2, -1, 0, +1, +2, +3). Representam mudança em índices do setup.

## FORMATO DE RESPOSTA PARA CHAT
Quando o piloto fizer uma pergunta, responda naturalmente em português. \
Seja direto, técnico mas acessível. Use analogias quando possível. \
Sempre termine com uma ação concreta que o piloto pode tomar.
"""

_SYSTEM_PROMPT_COMPACT = """\
Você é o Engenheiro Virtual do LMU. Responda em português de forma objetiva,
técnica e prática. Priorize sugestões seguras de setup e evite inventar dados.
Use no máximo 3 ajustes por resposta e sempre explique rapidamente o porquê.
"""


class LLMAdvisor:
    """
    Consultor LLM para o Engenheiro Virtual.

    Suporta múltiplos provedores de API (OpenRouter, OpenAI, Groq,
    DeepSeek, Together, ou qualquer API compatível com OpenAI).
    """

    def __init__(self, api_key: str = "", model: str = DEFAULT_MODEL,
                 provider: str = DEFAULT_PROVIDER,
                 custom_url: str = ""):
        self._api_key = api_key
        self._model = model
        self._provider = provider
        self._custom_url = custom_url
        self._history: list[dict] = []
        self._enabled = bool(api_key)
        self._request_count = 0
        self._last_request_time = 0.0
        self._min_interval = 1.0

    @property
    def enabled(self) -> bool:
        if self._provider == "lmstudio":
            return True  # LM Studio local não precisa de API key
        return self._enabled and bool(self._api_key)

    @staticmethod
    def _normalize_lmstudio_url(url: str) -> str:
        """Aceita URL base e garante endpoint /v1/chat/completions."""
        raw = (url or "").strip()
        if not raw:
            return ""

        low = raw.lower().rstrip("/")
        if low.endswith("/v1/chat/completions"):
            return raw.rstrip("/")
        if low.endswith(":1234"):
            return raw.rstrip("/") + "/v1/chat/completions"
        if low.endswith("/v1"):
            return raw.rstrip("/") + "/chat/completions"
        return raw

    @property
    def api_url(self) -> str:
        """Retorna a URL da API baseada no provedor selecionado."""
        if self._provider == "lmstudio":
            raw_url = self._custom_url or API_PROVIDERS["lmstudio"]["url"]
            return self._normalize_lmstudio_url(raw_url)
        if self._provider == "custom":
            return self._custom_url or ""
        prov = API_PROVIDERS.get(self._provider, API_PROVIDERS[DEFAULT_PROVIDER])
        return prov["url"]

    def set_api_key(self, key: str):
        """Atualiza a API key."""
        self._api_key = key.strip()
        self._enabled = bool(self._api_key)
        if self._enabled:
            logger.info("LLM Advisor: API key configurada.")
        else:
            logger.info("LLM Advisor: API key removida.")

    def set_model(self, model: str):
        """Altera o modelo LLM."""
        self._model = model
        logger.info("LLM Advisor: modelo alterado para %s", model)

    def set_provider(self, provider: str, custom_url: str = ""):
        """Altera o provedor de API."""
        self._provider = provider
        if provider in ("custom", "lmstudio") and custom_url:
            self._custom_url = custom_url
        elif provider == "lmstudio" and not custom_url:
            self._custom_url = API_PROVIDERS["lmstudio"]["url"]
        if provider == "lmstudio":
            self._enabled = True
        logger.info("LLM Advisor: provedor alterado para %s", provider)

    def clear_history(self):
        """Limpa o histórico de conversa."""
        self._history.clear()

    @staticmethod
    def detect_provider(api_key: str = "", api_url: str = "") -> str:
        """Detecta automaticamente o provedor pela API key ou URL."""
        url = api_url.strip().lower()
        if url.startswith(("http://", "https://")):
            if "127.0.0.1:1234" in url or "localhost:1234" in url:
                return "lmstudio"
            return "custom"

        key = api_key.strip()
        if key.startswith("sk-or-"):
            return "openrouter"
        elif key.startswith("gsk_"):
            return "groq"
        elif key.startswith("AIzaSy"):
            return "gemini"
        elif key.startswith("sk-ant-"):
            return "custom"  # Anthropic (não compatível OpenAI, mas usado via OpenRouter)
        elif key.startswith("sk-"):
            return "openai"  # OpenAI ou DeepSeek
        return "openrouter"  # Default

    # ─── Chat Inteligente ──────────────────────────────

    def chat(self, user_message: str, telemetry_context: dict | None = None,
             car_class: str = "hypercar",
             callback: Callable[[str], None] | None = None) -> str | None:
        """
        Envia mensagem do piloto para o LLM com contexto de telemetria.

        Se callback é fornecido, executa em thread separada e retorna None.
        Se não, executa síncrono e retorna a resposta.
        """
        if not self.enabled:
            return None

        # Construir mensagem com contexto
        context_parts = [user_message]
        if telemetry_context:
            context_parts.append(
                f"\n[CONTEXTO ATUAL]\n"
                f"Carro: {telemetry_context.get('car_name', 'desconhecido')}\n"
                f"Classe: {car_class}\n"
                f"Pista: {telemetry_context.get('track_name', 'desconhecida')}\n"
                f"Último tempo: {telemetry_context.get('last_lap_time', 'N/A')}\n"
                f"Grip médio: {telemetry_context.get('grip_avg', 'N/A')}\n"
                f"Temp pneus F: {telemetry_context.get('temp_front', 'N/A')}°C\n"
                f"Temp pneus R: {telemetry_context.get('temp_rear', 'N/A')}°C\n"
                f"Chuva: {telemetry_context.get('rain', 0)}\n"
                f"Sessão: {telemetry_context.get('session_type', 'practice')}"
            )

        full_message = "\n".join(context_parts)

        if callback:
            thread = threading.Thread(
                target=self._chat_threaded,
                args=(full_message, callback),
                daemon=True,
            )
            thread.start()
            return None
        else:
            return self._do_chat(full_message)

    def _chat_threaded(self, message: str, callback: Callable[[str], None]):
        """Executa chat em thread separada."""
        try:
            response = self._do_chat(message)
            callback(response or "Sem resposta do LLM.")
        except Exception as e:
            logger.error("LLM chat error: %s", e)
            callback(f"Erro na consulta ao LLM: {e}")

    def _do_chat(self, user_message: str) -> str:
        """Envia mensagem e retorna resposta."""
        self._history.append({"role": "user", "content": user_message})

        # Manter histórico limitado
        max_entries = MAX_HISTORY * 2
        if self._provider == "lmstudio":
            max_entries = LOCAL_MAX_HISTORY_TURNS * 2

        if len(self._history) > max_entries:
            self._history = self._history[-max_entries:]

        system_prompt = (
            _SYSTEM_PROMPT_COMPACT
            if self._provider == "lmstudio"
            else _SYSTEM_PROMPT
        )

        history_for_request = self._history
        if self._provider == "lmstudio":
            budget = max(1200, LOCAL_MAX_INPUT_CHARS - len(system_prompt))
            history_for_request = self._trim_history_by_chars(
                self._history,
                max_chars=budget,
            )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_for_request)

        response_text = self._api_request(messages)

        # Recovery automático para modelos locais com janela de contexto menor.
        if (
            self._provider == "lmstudio"
            and "context size" in response_text.lower()
        ):
            self._history = self._history[-1:]
            retry_messages = [
                {"role": "system", "content": _SYSTEM_PROMPT_COMPACT},
                {"role": "user", "content": user_message[-1500:]},
            ]
            response_text = self._api_request(retry_messages)

        if not self._is_error_response(response_text):
            stored = response_text
            if self._provider == "lmstudio":
                stored = self._compact_assistant_text(response_text)
            self._history.append({"role": "assistant", "content": stored})
        return response_text

    @staticmethod
    def _trim_history_by_chars(history: list[dict], max_chars: int) -> list[dict]:
        """Mantém apenas as mensagens mais recentes dentro do orçamento de chars."""
        kept: list[dict] = []
        total = 0
        for msg in reversed(history):
            content = str(msg.get("content", ""))
            size = len(content)
            if kept and total + size > max_chars:
                break
            if size > max_chars and not kept:
                clipped = dict(msg)
                clipped["content"] = content[-max_chars:]
                kept.append(clipped)
                break
            kept.append(msg)
            total += size
        kept.reverse()
        return kept

    @staticmethod
    def _is_error_response(text: str) -> bool:
        """Evita guardar mensagens de erro no histórico de conversa."""
        low = (text or "").strip().lower()
        if not low:
            return True
        return (
            low.startswith("❌")
            or low.startswith("⚠️")
            or low.startswith("⏱️")
            or "erro http" in low
            or "context size" in low
        )

    @staticmethod
    def _compact_assistant_text(text: str) -> str:
        """Reduz texto salvo no histórico para evitar inflar contexto local."""
        raw = (text or "").strip()
        if not raw:
            return ""

        cleaned = raw
        markers = (
            "thinking process:",
            "reasoning:",
            "chain of thought:",
        )
        low = cleaned.lower()
        for marker in markers:
            pos = low.find(marker)
            if pos >= 0:
                cleaned = cleaned[:pos].strip()
                low = cleaned.lower()

        if len(cleaned) > LOCAL_MAX_ASSISTANT_CHARS:
            cleaned = cleaned[:LOCAL_MAX_ASSISTANT_CHARS].rstrip() + "..."
        return cleaned

    # ─── Auto-Aprendizagem ─────────────────────────────

    def analyze_telemetry(self, telemetry: dict, car_class: str = "hypercar",
                          callback: Callable[[LLMInsight], None] | None = None
                          ) -> LLMInsight | None:
        """
        Analisa telemetria automaticamente e retorna insights estruturados.

        Usado pelo engine após cada volta para obter análise do LLM
        que alimenta o treinamento da rede neural.
        """
        if not self.enabled:
            return None

        prompt = self._build_telemetry_prompt(telemetry, car_class)

        if callback:
            thread = threading.Thread(
                target=self._analyze_threaded,
                args=(prompt, callback),
                daemon=True,
            )
            thread.start()
            return None
        else:
            return self._do_analyze(prompt)

    def _analyze_threaded(self, prompt: str, callback: Callable[[LLMInsight], None]):
        """Análise em thread separada."""
        try:
            insight = self._do_analyze(prompt)
            callback(insight)
        except Exception as e:
            logger.error("LLM analyze error: %s", e)
            callback(LLMInsight(explanation=f"Erro: {e}"))

    def _do_analyze(self, prompt: str) -> LLMInsight:
        """Envia prompt de análise e parseia resposta JSON."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response_text = self._api_request(messages)

        return self._parse_insight(response_text)

    def _build_telemetry_prompt(self, telemetry: dict, car_class: str) -> str:
        """Constrói o prompt de análise de telemetria."""
        lines = [
            "Analise os seguintes dados de telemetria e sugira ajustes de setup.",
            "Responda APENAS em JSON no formato especificado no system prompt.",
            "",
            f"CLASSE DO CARRO: {car_class}",
            "",
            "DADOS DE TELEMETRIA:",
        ]

        # Organizar dados por categoria
        temp_keys = [k for k in telemetry if "temp" in k.lower()]
        pressure_keys = [k for k in telemetry if "pressure" in k.lower()]
        wear_keys = [k for k in telemetry if "wear" in k.lower()]
        other_keys = [k for k in telemetry if k not in temp_keys + pressure_keys + wear_keys]

        if temp_keys:
            lines.append("\nTemperaturas (°C):")
            for k in temp_keys:
                lines.append(f"  {k}: {telemetry[k]:.1f}")

        if pressure_keys:
            lines.append("\nPressões (kPa):")
            for k in pressure_keys:
                lines.append(f"  {k}: {telemetry[k]:.1f}")

        if wear_keys:
            lines.append("\nDesgaste (%):")
            for k in wear_keys:
                lines.append(f"  {k}: {telemetry[k]:.1f}")

        if other_keys:
            lines.append("\nOutros:")
            for k in other_keys:
                v = telemetry[k]
                if isinstance(v, float):
                    lines.append(f"  {k}: {v:.3f}")
                else:
                    lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    def _parse_insight(self, response_text: str) -> LLMInsight:
        """Parseia a resposta do LLM em LLMInsight."""
        import re as _re
        insight = LLMInsight()

        try:
            # Tentar extrair JSON da resposta
            json_str = response_text
            # Se tiver markdown code block, extrair
            if "```json" in response_text:
                start = response_text.index("```json") + 7
                end = response_text.index("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.index("```") + 3
                end = response_text.index("```", start)
                json_str = response_text[start:end].strip()
            # Tentar encontrar o primeiro { ... } se nada mais funcionar
            elif "{" in response_text:
                start = response_text.index("{")
                end = response_text.rindex("}") + 1
                json_str = response_text[start:end]

            # Limpar comentários JS/JSON que o LLM às vezes adiciona
            json_str = _re.sub(r'//[^\n]*', '', json_str)
            # Remover trailing commas antes de } ou ]
            json_str = _re.sub(r',\s*([}\]])', r'\1', json_str)

            data = json.loads(json_str)

            insight.adjustments = {
                k: int(v) for k, v in data.get("adjustments", {}).items()
                if isinstance(v, (int, float))
            }
            insight.explanation = data.get("explanation", "")
            insight.confidence = float(data.get("confidence", 0.5))
            insight.engineering_notes = data.get("engineering_notes", "")
            insight.warnings = list(data.get("warnings", []))

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Falha ao parsear JSON do LLM: %s", e)
            # Se não é JSON, usar como explicação texto livre
            insight.explanation = response_text
            insight.confidence = 0.3

        return insight

    # ─── API Request ───────────────────────────────────

    def _api_request(self, messages: list[dict]) -> str:
        """Faz requisição HTTP para o provedor de API selecionado."""
        import urllib.request
        import urllib.error
        import socket

        url = self.api_url
        if not url:
            return "❌ URL da API não configurada. Selecione um provedor ou informe a URL."

        # Rate limiting
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        headers = {
            "Content-Type": "application/json",
        }

        # LM Studio local não precisa de Authorization
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        elif self._provider == "lmstudio":
            headers["Authorization"] = "Bearer lm-studio"

        # Headers extras para OpenRouter
        if self._provider == "openrouter":
            headers["HTTP-Referer"] = "https://lmu-virtual-engineer.app"
            headers["X-Title"] = "LMU Virtual Engineer"

        max_tokens = LOCAL_MAX_TOKENS if self._provider == "lmstudio" else 1500
        timeout_s = (
            LOCAL_REQUEST_TIMEOUT
            if self._provider == "lmstudio"
            else REQUEST_TIMEOUT
        )

        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers=headers,
            method="POST",
        )

        prov_name = API_PROVIDERS.get(self._provider, {}).get("name", self._provider)
        logger.info("LLM request [%s]: model=%s, msgs=%d",
                     prov_name, self._model, len(messages))

        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)

            self._last_request_time = time.time()
            self._request_count += 1

            # Verificar se houve erro da API (ex: modelo inexistente)
            if "error" in data:
                err_msg = data["error"].get("message", str(data["error"]))
                logger.error("LLM API error: %s", err_msg)
                return f"⚠️ Erro da API: {err_msg}"

            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "") or msg.get("text", "")
                # Nunca expor reasoning_content bruto no chat.
                # Alguns modelos retornam apenas raciocínio interno quando
                # max_tokens é atingido antes da resposta final.
                if not content:
                    reasoning = msg.get("reasoning_content", "")
                    if reasoning:
                        logger.warning(
                            "LLM sem resposta final (content vazio, reasoning=%d chars)",
                            len(reasoning),
                        )
                    return (
                        "Sem resposta final do modelo nesta tentativa. "
                        "Tente novamente com uma pergunta mais curta."
                    )
                content = self._compact_assistant_text(content)
                logger.info("LLM response: %d chars", len(content))
                return content

            logger.warning("LLM: resposta sem choices: %s", data)
            return "Sem resposta do modelo."

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.error("LLM HTTP %d: %s", e.code, body[:300])
            if e.code == 429:
                return "⚠️ Limite de requisições atingido. Tente em alguns segundos."
            elif e.code == 401:
                return "❌ API key inválida. Verifique nas configurações."
            elif e.code == 402:
                return "❌ Sem créditos na conta OpenRouter. Adicione saldo."
            elif e.code == 404:
                return f"❌ Modelo '{self._model}' não encontrado. Troque o modelo."
            else:
                return f"❌ Erro HTTP {e.code}: {body[:100]}"

        except (socket.timeout, TimeoutError):
            logger.error("LLM timeout após %ds", timeout_s)
            if self._provider == "lmstudio":
                return (
                    f"⏱️ Timeout ({timeout_s}s). O LM Studio demorou para responder. "
                    "Confirme se o modelo está carregado e tente novamente."
                )
            return (
                f"⏱️ Timeout ({timeout_s}s). O modelo pode estar sobrecarregado. "
                "Tente novamente ou use um modelo mais rápido "
                "(ex: deepseek/deepseek-v3.2 ou qwen/qwen3.6-plus-preview:free)."
            )

        except urllib.error.URLError as e:
            logger.error("LLM connection error: %s", e)
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                if self._provider == "lmstudio":
                    return (
                        f"⏱️ Timeout ({timeout_s}s). O LM Studio não respondeu a tempo."
                    )
                return (
                    f"⏱️ Timeout ({timeout_s}s). "
                    "Tente novamente ou use um modelo mais rápido."
                )
            return "❌ Sem conexão com a internet. Chat funciona offline."

        except Exception as e:
            logger.error("LLM unexpected error: %s", e)
            return f"❌ Erro inesperado: {e}"

    # ─── Utilitários ───────────────────────────────────

    def test_connection(self, callback: Callable[[bool, str], None] | None = None
                        ) -> tuple[bool, str] | None:
        """
        Testa a conexão com a API.

        Returns:
            (sucesso, mensagem) ou None se callback fornecido
        """
        if not self._api_key and self._provider != "lmstudio":
            result = (False, "API key não configurada.")
            if callback:
                callback(*result)
                return None
            return result

        def _test():
            messages = [
                {"role": "system", "content": "Responda apenas: OK"},
                {"role": "user", "content": "Teste de conexão."},
            ]
            response = self._api_request(messages)
            if "❌" in response or "Erro" in response:
                return (False, response)
            return (True, f"✅ Conectado! Modelo: {self._model}")

        if callback:
            def _threaded():
                result = _test()
                callback(*result)
            threading.Thread(target=_threaded, daemon=True).start()
            return None
        else:
            return _test()

    def validate_prediction(self, telemetry: dict,
                           nn_deltas: dict,
                           car_class: str = "hypercar",
                           callback: Callable[[LLMInsight], None] | None = None
                           ) -> LLMInsight | None:
        """
        Pede ao LLM para AVALIAR a predição da rede neural.

        Envia a telemetria E os deltas que a NN sugeriu, pedindo ao
        LLM para corrigir o que for necessário. Usado para:
        1. Validar sugestões antes de apresentar ao piloto
        2. Medir autonomia (se LLM concorda, NN aprendeu)

        Args:
            telemetry: Dict de telemetria
            nn_deltas: Dict de deltas sugeridos pela rede neural
            car_class: Classe do carro
            callback: Se fornecido, executa em thread

        Returns:
            LLMInsight com os ajustes corrigidos pelo LLM
        """
        if not self.enabled:
            return None

        prompt = self._build_validation_prompt(
            telemetry, nn_deltas, car_class,
        )

        if callback:
            thread = threading.Thread(
                target=self._analyze_threaded,
                args=(prompt, callback),
                daemon=True,
            )
            thread.start()
            return None
        else:
            return self._do_analyze(prompt)

    def _build_validation_prompt(self, telemetry: dict,
                                 nn_deltas: dict,
                                 car_class: str) -> str:
        """Constrói prompt para validação de predição da NN."""
        lines = [
            "A rede neural do engenheiro virtual sugeriu os seguintes "
            "ajustes de setup. Avalie se estão corretos e corrija "
            "o que for necessário.",
            "",
            "Responda APENAS em JSON no formato do system prompt.",
            "Se concordar com a NN, retorne os mesmos ajustes com "
            "confidence alta (>0.8).",
            "Se discordar, retorne seus ajustes corrigidos com "
            "explicação do porquê.",
            "",
            f"CLASSE DO CARRO: {car_class}",
            "",
            "AJUSTES DA REDE NEURAL:",
        ]
        for k, v in nn_deltas.items():
            if v != 0:
                lines.append(f"  {k}: {v:+d}")

        lines.append("")
        lines.append("DADOS DE TELEMETRIA:")
        for k, v in telemetry.items():
            if k.startswith("_"):
                continue
            if isinstance(v, float):
                lines.append(f"  {k}: {v:.2f}")
            else:
                lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def model_name(self) -> str:
        return self._model
