Relatório: Investigação — Memória da IA e aplicação de histórico

Resumo executivo
- Problema: A IA está, por vezes, usando dados antigos de memória ou não aplicando a memória ao sugerir deltas mesmo quando o jogo/telemetria está conectado.
- Conclusão rápida: comportamento observado é consequência de três pontos principais no código:
  1) A memória persistente `car×track` só é carregada no evento de "volta completada" (_on_lap_completed_), portanto antes da primeira volta não há memória disponível para uso.
  2) A aplicação da memória às sugestões está condicionada a um limiar de confiança (`memory_confidence >= 0.1`) e a presença de `learning_samples`. Memórias com confiança baixa são ignoradas por `main._apply_memory_to_deltas`.
  3) Não há verificação de "freshness" (timestamp) nem logs fortes que indiquem quando a memória foi aplicada ou ignorada em runtime.

Evidências (trechos relevantes)
- Carregamento de memória chamado apenas ao completar uma volta:
  - `main.py` — `_on_lap_completed` chama `_load_session_memory` quando detecta novo combo carro×pista: [main.py](main.py#L1625)
- Função que aplica memória às deltas utiliza `memory_confidence` e pode retornar sem aplicar quando < 0.1:
  - `main.py` — `_apply_memory_to_deltas`: a verificação `if memory_conf < 0.1: return deltas` impede aplicação de memórias de baixa confiança: [main.py](main.py#L2419)
- Leitura/escrita da memória persistente no DB:
  - `data/database.py` — `load_car_track_memory` carrega JSONs e retorna dicionário com `memory_confidence`: [data/database.py](data/database.py#L978)
  - `data/database.py` — `update_session_learning_data` incrementa `memory_confidence` em +0.01 por atualização de aprendizagem (por volta válida): [data/database.py](data/database.py#L1216)

Causa-raiz detalhada
1) Carregamento tardio da memória
   - A memória é carregada somente quando uma volta é completada; se o usuário conectar o jogo e esperar que a IA já use histórico antes de completar uma volta, o código atual não carrega a memória.
   - Trecho-chave: chamada em `_on_lap_completed` → `_load_session_memory` ([main.py](main.py#L1625)).
2) Limiar de confiança e mecanismo de aprendizagem lento
   - `memory_confidence` aumenta levemente (0.01) apenas quando a função `update_session_learning_data` é chamada, ou seja, após acumular amostras válidas — por isso memórias antigas podem iniciar com confiança baixa e serem ignoradas pelo algoritmo de blending.
   - Trecho de incremento: `memory["memory_confidence"] = min(1.0, confidence + 0.01)` ([data/database.py](data/database.py#L1216)).
   - `_apply_memory_to_deltas` bloqueia memórias com `memory_conf < 0.1` — isto é intencional para evitar uso prematuro de memória fraca, porém pode contrariar expectativas do usuário (usar histórico existente imediatamente).
3) Falta de instrumentation (logs) que mostrem decisão
   - Embora existam logs de carregamento (`"Memória carregada..."`), não há log granular no momento em que `_apply_memory_to_deltas` decide "usar" vs "ignorar" a memória para cada parâmetro.

Reprodução proposta (passo a passo)
1) Iniciar a aplicação (`python main.py`) com o jogo fechado — observar que há leitura da base de setups e que a shared memory fecha (simulador OFF).
2) Abrir o jogo e conectar à mesma pista/car. Antes de completar qualquer volta, observar que a GUI não recebe mensagem de "memória carregada" e que `self._active_memory` permanece `None`.
3) Completar a primeira volta — verificar no log que o `_load_session_memory` foi executado e que `memory_confidence` é lido do DB.
4) Repetir e inspecionar se `_apply_memory_to_deltas` aplica memória (ver mensagens de log após patch proposto).

Recomendações e correções (prioridade)
1) Carregar memória ao detectar combo carro×pista (conexão ao jogo), não somente na 1ª volta
   - Onde: chamar `_load_session_memory(car_id, track_id)` assim que o jogo/reporta `car_name` e `track_name` (por exemplo, no handler de conexão ou logo após `get_car_info()`), e ajustar `_memory_loaded_for` para `combo`.
   - Benefício: memória histórica estará imediatamente disponível para o motor de sugestões.
2) Ajustar política de aplicação de memória / confiança
   - Opções:
     a) Aplicar memória em modo "fallback" mesmo com `memory_confidence < 0.1`, mas com peso mínimo e log claro.
     b) Tornar `memory_confidence` configurável via `config.py` (por ex., `memory.apply_threshold`) e permitir que o usuário reduza o limiar.
   - Recomendo aplicar (1) + (2a): permitir aplicação inicial com peso muito pequeno (ex: memory_weight mínimo 0.05) para que histórico influencie desde o início.
3) Instrumentar logs para decisões de memória
   - Adicionar `logger.debug`/`info` em `_apply_memory_to_deltas` detalhando: `memory_confidence`, `ai_confidence`, `memory_weight` e quais parâmetros foram preenchidos/mesclados.
   - Exemplo de mensagem: `logger.info("Memória aplicada: %d parâmetros, peso=%.2f (mem_conf=%.2f ai_conf=%.2f)", len(applied), memory_weight, memory_conf, ai_conf)`
4) Adicionar campo de timestamp e verificação de frescor (opcional)
   - Incluir em `car_track_memory` um `last_learned_at` e rejeitar memória muito antiga (ex: > 1 ano) ou sinalizar o usuário.

Exemplo de patch sugerido (pseudo)
- No local onde `car_name`/`track_name` são detectados (após `get_car_info()` / auto-connection):
```
# após detectar car_id / track_id
if self._memory_loaded_for != (car_id, track_id):
    self._load_session_memory(car_id, track_id)
    self._memory_loaded_for = (car_id, track_id)
```
- Em `_apply_memory_to_deltas`, adicionar logs e ajuste do limiar:
```
memory_conf = self._active_memory.get('memory_confidence', 0)
if memory_conf < self.config.get('memory.apply_threshold', 0.05):
    logger.debug('Memória disponível mas abaixo do limiar (%.2f) — aplicando com peso reduzido', memory_conf)
# calcular memory_weight com floor mínimo
memory_weight = max(0.05, 0.5 * (1.0 - ai_conf) * memory_conf)
# ... aplicar e logar parâmetros alterados
```

Checklist de verificação (para aceitar correção)
- [ ] Chamadas a `_load_session_memory` ocorrem assim que o combo carro×pista é detectado (antes da 1ª volta).
- [ ] Logs mostram quando a memória foi aplicada ou ignorada e o motivo.
- [ ] A IA passa a misturar histórico mesmo nas primeiras voltas com peso conservador.
- [ ] `memory_confidence` exposto na GUI (opcional) para diagnóstico.

Próximos passos que eu posso executar agora
- Aplicar o patch para carregar memória imediatamente ao detectar `car/track` e adicionar logs de decisão em `_apply_memory_to_deltas` (posso editar e executar rapidamente na sua cópia).
- Ajustar o limiar configurável e documentar em `config.py`.
- Executar a aplicação e gerar logs demonstrando o comportamento antes/depois.

Arquivo criado
- `docs/reports/RELATORIO_INVESTIGACAO_MEMORIA_IA_Detalhado.md` (este relatório).

Quer que eu aplique automaticamente os patches (carregar memória ao detectar combo e adicionar logs) e execute a aplicação para coletar logs de verificação? Se sim, confirmo antes de alterar o código.