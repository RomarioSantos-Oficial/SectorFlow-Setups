# RELATÓRIO: Melhorias de Aprendizagem Autônoma da IA v2

**Data:** 02/04/2026  
**Projeto:** LMU Virtual Engineer  
**Objetivo:** Tornar a IA capaz de aprender sozinha, manipular seu banco de dados, buscar conhecimento e evoluir de forma autônoma usando LLM local (LM Studio)

---

## SITUAÇÃO ATUAL

### O que já existe (4 camadas)
| Camada | Função | Status |
|--------|--------|--------|
| Heurísticas | 65+ regras baseadas em física | ✅ Funcional |
| Rede Neural (MLP) | 49 inputs → 8-45 outputs | ✅ Funcional |
| LLM Multi-provedor | Chat + análise de telemetria | ✅ Funcional (7 provedores) |
| Knowledge Distillation | LLM ensina rede neural | ✅ Funcional |

### Banco de dados atual (20+ tabelas)
- `laps` — dados de telemetria por volta
- `training_data` — vetores de treino (input/output/reward)
- `learning_rules` — regras causa→efeito com efetividade
- `ai_knowledge_base` — conceitos aprendidos (topic/answer)
- `car_track_memory` — memória persistente por carro×pista
- `setup_library` — setups escaneados para padrões
- `setup_comparison_log` — comparações A/B

### Limitações identificadas
1. **A IA NÃO busca conhecimento proativamente** — só aprende quando recebe dados de telemetria
2. **Destilação é batch-only** — precisa ser acionada manualmente pelo usuário
3. **Sem ciclo de auto-reflexão** — a IA não revisa o que aprendeu para corrigir erros
4. **ai_knowledge_base** quase vazia — não é populada automaticamente
5. **Sem curriculum learning contínuo** — após destilação inicial, para de aprender do LLM
6. **learning_rules** não influenciam diretamente a rede neural — apenas boosteiam heurísticas

---

## PROPOSTAS DE MELHORIA

### 1. AUTO-APRENDIZAGEM CONTÍNUA (Motor de Curiosidade)
**O que é:** Um loop que roda em background quando o LM Studio está ativo, fazendo a IA buscar conhecimento e treinar sozinha.

**Como funciona:**
```
Loop contínuo (a cada 5-10 minutos quando idle):
  1. Identificar LACUNAS de conhecimento
     → "Nunca treinei cenário: chuva + pneus gastos + hypercar"
     → "Não tenho regras efetivas para oversteer em Spa"
  2. Gerar cenário sintético para a lacuna
  3. Consultar LLM local (LM Studio) — custo ZERO
  4. Salvar resposta como training_data
  5. Treinar rede neural com novos dados
  6. Medir se a autonomia melhorou
  7. Registrar em ai_knowledge_base
```

**Impacto:** A IA evolui 24/7 mesmo quando o jogo não está rodando.

**Tabela nova no schema:**
```sql
CREATE TABLE IF NOT EXISTS auto_learning_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type    TEXT NOT NULL,    -- 'curiosity', 'review', 'research'
    scenario_desc   TEXT,
    llm_query       TEXT,
    llm_response    TEXT,
    knowledge_gained TEXT,            -- JSON resumo do que aprendeu
    autonomy_before REAL,
    autonomy_after  REAL,
    was_useful      INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Arquivo novo: `core/auto_learner.py`**

**Aprovar?** ⬜ SIM / ⬜ NÃO

---

### 2. MANIPULAÇÃO AUTÔNOMA DO BANCO DE DADOS
**O que é:** Dar à IA permissão para ler, escrever e atualizar tabelas específicas do banco de forma autônoma.

**Tabelas que a IA PODE modificar (seguras):**
| Tabela | Operação | Motivo |
|--------|----------|--------|
| `ai_knowledge_base` | INSERT, UPDATE | Armazenar conceitos aprendidos |
| `learning_rules` | INSERT, UPDATE | Registrar novas regras |
| `car_track_memory` | UPDATE | Atualizar memória por combo |
| `auto_learning_log` | INSERT | Registrar atividade de aprendizagem |
| `training_data` | INSERT | Adicionar dados de treino |

**Tabelas que a IA NÃO pode modificar (proteção):**
| Tabela | Motivo |
|--------|--------|
| `laps` | Dados reais — nunca alterar |
| `sessions` | Dados reais — nunca alterar |
| `cars`, `tracks` | Catálogo — só human edit |
| `driver_profiles` | Dados pessoais |
| `setup_snapshots` | Histórico imutável |

**Classe `AutoLearner` terá métodos encapsulados com validação para cada operação permitida.**

**Aprovar?** ⬜ SIM / ⬜ NÃO

---

### 3. REESCRITA INTELIGENTE DA KNOWLEDGE BASE
**O que é:** A IA pode reescrever e atualizar suas próprias entradas na `ai_knowledge_base`, melhorando respostas conforme aprende mais.

**Fluxo:**
```
1. IA responde pergunta sobre "understeer na chuva"
2. Puxa da knowledge_base: encontra resposta antiga com confidence 0.5
3. Consulta LLM local com contexto completo (regras efetivas + dados reais)
4. Compara resposta nova vs antiga
5. Se nova é melhor (mais específica, cita dados reais):
   → UPDATE ai_knowledge_base SET answer = novo, confidence = novo
   → Registra no auto_learning_log
6. Se antiga é melhor: mantém, incrementa times_accessed
```

**Proteções:**
- Nunca deleta entradas — apenas atualiza
- Mantém histórico de versões (campo `previous_answer`)
- Confidence só sobe se dados reais confirmam
- Máximo 50 updates por sessão de auto-aprendizagem (rate limit)

**Alteração no schema:**
```sql
ALTER TABLE ai_knowledge_base ADD COLUMN previous_answer TEXT;
ALTER TABLE ai_knowledge_base ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE ai_knowledge_base ADD COLUMN auto_updated INTEGER DEFAULT 0;
```

**Aprovar?** ⬜ SIM / ⬜ NÃO

---

### 4. PESQUISA DE CONHECIMENTO (Research Mode)
**O que é:** A IA conversa com o LLM local para "pesquisar" tópicos que não domina, como se estivesse lendo um livro.

**Tópicos de pesquisa automática (exemplos):**
```python
RESEARCH_TOPICS = [
    # Técnicos
    "Como ajustar ride height para efeito solo máximo em LMH",
    "Relação entre rake angle e equilíbrio aerodinâmico",
    "Impacto do peso de combustível na mola ideal",
    "Degradação de pneus: curva de temperatura vs grip",
    "Estratégia de energia para Le Mans 24h em Hypercar",
    
    # Pistas específicas
    "Características da pista de Monza para GT3",
    "Setup ideal para Spa-Francorchamps em chuva",
    "Setores de Bahrain que mais desgastam pneus",
    
    # Classe-específico
    "Diferenças de setup entre Porsche 963 e Ferrari 499P",
    "Como ajustar engine braking em LMP2 sem TC",
    "Gestão de regen em curvas de baixa velocidade",
]
```

**Fluxo:**
```
1. Escolher tópico (priorizar lacunas do knowledge_base)
2. Montar prompt para o LLM: 
   "Você é engenheiro de corrida. Explique em detalhes técnicos: [tópico]"
3. Receber resposta detalhada
4. Extrair pontos-chave → salvar em ai_knowledge_base
5. Se resposta menciona parâmetros (asa, mola, camber):
   → Gerar regras novas em learning_rules
6. Registrar no auto_learning_log
```

**Proteção:** Conhecimento de pesquisa começa com `confidence = 0.4` e só sobe quando dados reais confirmam.

**Aprovar?** ⬜ SIM / ⬜ NÃO

---

### 5. CICLO DE AUTO-REFLEXÃO (Self-Review)
**O que é:** Periodicamente, a IA revisa suas regras e conhecimentos, descartando o que não funciona e reforçando o que funciona.

**Fluxo:**
```
A cada 24h (ou quando idle por >30min):
  1. Puxar learning_rules com effectiveness_rate < 0.3 e times_applied > 5
     → "Regras que FALHARAM repetidamente"
  2. Puxar learning_rules com effectiveness_rate > 0.8
     → "Regras que FUNCIONAM bem"
  3. Montar prompt para LLM:
     "Estas regras falharam: [lista]. Estas funcionaram: [lista]. 
      Por que as ruins falharam? Sugira regras melhores."
  4. LLM analisa e sugere correções
  5. Atualizar/criar regras corrigidas
  6. Marcar regras ruins como "revisadas"
  7. Registrar insight no auto_learning_log
```

**Tabela nova:**
```sql
CREATE TABLE IF NOT EXISTS learning_reviews (
    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    car_class       TEXT,
    rules_reviewed  INTEGER,     -- quantas regras analisou
    rules_updated   INTEGER,     -- quantas corrigiu
    rules_deprecated INTEGER,    -- quantas invalidou
    insights        TEXT,        -- JSON com insights da revisão
    llm_analysis    TEXT,        -- análise completa do LLM
    reviewed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Aprovar?** ⬜ SIM / ⬜ NÃO

---

### 6. DASHBOARD DE EVOLUÇÃO DA IA
**O que é:** Um painel na GUI que mostra em tempo real como a IA está evoluindo.

**Métricas exibidas:**
- Autonomy Score (%) — gráfico de evolução temporal
- Total de regras efetivas vs falhas
- Knowledge base por categoria (quantos temas domina)
- Sessões de auto-aprendizagem (últimas 24h)
- Top 5 lacunas de conhecimento (o que ainda não sabe)
- Comparação: IA de ontem vs IA de hoje

**Onde:** Nova seção na aba "Dados" ou card extra na aba "Setup"

**Aprovar?** ⬜ SIM / ⬜ NÃO

---

## MUDANÇAS PONTUAIS EM ARQUIVOS EXISTENTES

### 7. Melhorias menores em módulos existentes

| Arquivo | Mudança | Motivo |
|---------|---------|--------|
| `core/knowledge_distiller.py` | Adicionar modo `continuous` além do `batch` | Destilação contínua em background |
| `core/heuristics.py` | Consultar `learning_rules` efetivas antes de aplicar regras fixas | Regras aprendidas têm prioridade sobre as seed |
| `core/llm_advisor.py` | Novo método `research(topic)` — prompt simplificado para pesquisa | Pesquisa de conhecimento dirigida |
| `data/database.py` | Novos métodos: `get_knowledge_gaps()`, `update_knowledge()`, `get_rules_for_review()` | Suporte à auto-aprendizagem |
| `data/schema.sql` | 2 tabelas novas + 3 colunas novas no ai_knowledge_base | Suporte a logs e versionamento |
| `gui/tab_setup.py` | Checkbox "🧠 Auto-Aprendizagem Contínua" no card de LLM | Ligar/desligar o motor de curiosidade |
| `config.py` | Novas configs: `auto_learning_enabled`, `auto_learning_interval_min`, `max_auto_learns_per_day` | Controle do auto-learner |

**Aprovar?** ⬜ SIM / ⬜ NÃO

---

## ARQUITETURA PROPOSTA

```
                    ┌─────────────────────────┐
                    │     LM Studio (Local)    │
                    │    (LLM grátis, 24/7)    │
                    └──────────┬──────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼──────┐ ┌───────▼───────┐
    │  Auto-Learner  │ │  Researcher │ │  Self-Review  │
    │  (Curiosidade) │ │  (Pesquisa) │ │  (Reflexão)   │
    │                │ │             │ │               │
    │ Gera cenários  │ │ Pergunta ao │ │ Revisa regras │
    │ sintéticos e   │ │ LLM sobre   │ │ que falharam  │
    │ treina a rede  │ │ tópicos que │ │ e corrige     │
    │ neural         │ │ não domina  │ │               │
    └───────┬────────┘ └──────┬──────┘ └───────┬───────┘
            │                 │                 │
            ▼                 ▼                 ▼
    ┌───────────────────────────────────────────────────┐
    │              BANCO DE DADOS SQLite                │
    │                                                   │
    │  training_data ← novos exemplos de treino         │
    │  ai_knowledge_base ← conceitos pesquisados        │
    │  learning_rules ← regras corrigidas/novas         │
    │  auto_learning_log ← log de tudo que aprendeu     │
    │  learning_reviews ← histórico de revisões         │
    │  car_track_memory ← memória atualizada            │
    └───────────────────────────────────────────────────┘
            │
            ▼
    ┌───────────────────┐
    │   Rede Neural     │
    │  (mais inteligente│
    │   a cada ciclo)   │
    └───────────────────┘
```

---

## ESTIMATIVA DE IMPACTO

| Métrica | Antes | Depois (estimado) |
|---------|-------|--------------------|
| Autonomy Score após 1 dia | ~30% (manual) | ~70% (auto) |
| Autonomy Score após 1 semana | ~50% (manual) | ~90%+ (auto) |
| Knowledge base entries | ~0 (vazia) | ~200+ (auto-populada) |
| Learning rules efetivas | ~65 (seed only) | ~300+ (aprendidas) |
| Necessidade de API paga | Sempre | Só no início, depois 100% local |

---

## RISCOS E MITIGAÇÕES

| Risco | Mitigação |
|-------|-----------|
| LLM local dá resposta errada | Confidence começa em 0.4; só sobe com dados reais |
| Loop infinito de treinamento | Rate limit: máx 50 operações/dia, intervalo mínimo 5min |
| Banco cresce demais | VACUUM INCREMENTAL + limpeza de dados antigos com reward ~0 |
| IA "desaprende" algo bom | Regras com effectiveness > 0.8 são protegidas de update |
| Overhead de CPU/RAM | Thread de baixa prioridade, pausa quando jogo está rodando |

---

## PRIORIDADE DE IMPLEMENTAÇÃO

| Ordem | Proposta | Complexidade | Valor |
|-------|----------|-------------|-------|
| 1 | Auto-Learner (Motor de Curiosidade) | Média | ⭐⭐⭐⭐⭐ |
| 2 | Manipulação autônoma do DB | Baixa | ⭐⭐⭐⭐⭐ |
| 3 | Reescrita da Knowledge Base | Média | ⭐⭐⭐⭐ |
| 4 | Research Mode | Baixa | ⭐⭐⭐⭐ |
| 5 | Self-Review | Média | ⭐⭐⭐ |
| 6 | Dashboard de Evolução | Baixa | ⭐⭐⭐ |
| 7 | Mudanças pontuais | Baixa | ⭐⭐⭐⭐ |

---

## DECISÃO

**Marque quais propostas quer que eu implemente:**

- [ ] **Proposta 1:** Auto-Aprendizagem Contínua (Motor de Curiosidade)
- [ ] **Proposta 2:** Manipulação Autônoma do Banco de Dados
- [ ] **Proposta 3:** Reescrita Inteligente da Knowledge Base
- [ ] **Proposta 4:** Pesquisa de Conhecimento Externo
- [ ] **Proposta 5:** Ciclo de Auto-Reflexão
- [ ] **Proposta 6:** Dashboard de Evolução
- [ ] **Proposta 7:** Mudanças Pontuais em Arquivos Existentes
- [ ] **TODAS** — Implementar tudo na ordem de prioridade
