# Relatório de problemas e melhorias — persistência, IA e cálculo de combustível

## Resumo executivo

O sistema apresenta três problemas principais que explicam o comportamento observado:

1. A persistência de sessão e memória está inconsistente, o que faz o app salvar ou restaurar estado de forma parcial ou desatualizada.
2. A IA está reutilizando dados de histórico antigo demais, sem uma limpeza ou validação forte de contexto entre sessões.
3. O cálculo de combustível está baseado em uma lógica frágil, com dados incompletos e sem validação de eventos como pit stop, reabastecimento e voltas inválidas.

---

## 1) Problemas encontrados

### 1.1 Persistência incompleta ou instável

**Onde aparece**
- [main.py](main.py)
- [data/database.py](data/database.py)

**Causa provável**
- O estado da sessão é salvo apenas em certos gatilhos, como aplicar sugestão, carregar setup ou a cada 5 voltas. Isso não garante que todos os dados relevantes sejam persistidos sempre.
- O sistema salva estado em diferentes estruturas: sessão, memória de carro × pista e snapshots de setup. Isso mistura responsabilidades e facilita inconsistências.
- A restauração depende de informações como nome do carro e pista. Se esses campos não estiverem corretamente preenchidos, o restore pode não acontecer ou restaurar dados errados.

**Sintoma observado**
- Arquivo/estado não guarda corretamente as informações esperadas, especialmente quando o contexto muda ou a sessão é reiniciada.

**Impacto**
- A IA e a GUI podem trabalhar com estado antigo, incompleto ou mal restaurado.

### 1.2 Uso excessivo de memória antiga da IA

**Onde aparece**
- [main.py](main.py)
- [data/database.py](data/database.py)

**Causa provável**
- A memória persistente de carro × pista é carregada e usada como base para sugestões sem uma validação forte de frescor dos dados.
- O código carrega essa memória uma vez por combo carro × pista e a reutiliza durante a sessão sem um reset claro entre sessões diferentes.
- Não há um mecanismo forte para desconsiderar histórico antigo quando as condições mudaram muito (mudança de clima, setup, pista, pit stop, reabastecimento, etc.).

**Sintoma observado**
- A IA “pega” informação antiga ou não compatível com a situação atual.
- Sugestões podem parecer baseadas em dados de uma sessão anterior, não na sessão atual.

**Impacto**
- A IA passa a sugerir com base em contexto desatualizado, gerando decisões ruins.

### 1.3 Cálculo de combustível frágil e provavelmente incorreto

**Onde aparece**
- [main.py](main.py)
- [data/telemetry_reader.py](data/telemetry_reader.py)
- [data/svm_parser.py](data/svm_parser.py)

**Causa provável**
- O cálculo usa diferença entre combustível restante de voltas consecutivas, mas não valida eventos como pit stop, reabastecimento, volta de saída do box, volta inválida ou mudança de sessão.
- O código usa dados parciais de telemetria e não faz uma correção robusta do consumo por volta.
- O algoritmo de estratégia arredonda de forma agressiva e pode exagerar ou subestimar o combustível necessário.
- O cálculo depende de valores de combustível que podem estar ausentes ou inconsistente na estrutura de histórico.

**Sintoma observado**
- O valor de combustível mostrado na interface não bate com o real, e a estratégia recomendada é inconsistente.

**Impacto**
- Estratégia de stint, consumo por volta e recomendações de reabastecimento ficam inexatos.

---

## 2) Causas técnicas concretas

### 2.1 Falta de um único fluxo de persistência confiável

Hoje o app persiste dados em vários lugares diferentes:
- estado de sessão
- memória carro × pista
- snapshots de setup
- histórico de voltas
- banco SQLite

Isso é bom para flexibilidade, mas ruim para consistência. O ideal é ter um fluxo único e bem definido:
- salvar sempre no mesmo formato
- validar antes de persistir
- restaurar com um único caminho

### 2.2 Memória da IA sem “freshness” nem invalidação contextual

A memória carregada em [main.py](main.py) é usada para influenciar o comportamento da IA, mas falta:
- limiar de confiança
- invalidação após mudanças de contexto forte
- reset automático ao mudar de sessão ou de condições meteorológicas
- comparação entre histórico recente e histórico antigo

### 2.3 Cálculo de combustível sem robustez operacional

No fluxo atual, há risco de:
- contar consumo de volta errado durante pit stop
- somar combustível com base em lap history incompleta
- usar valores inválidos de combustível como se fossem válidos
- não descontar reabastecimento e consumo em volta de saída de pits

---

## 3) Melhorias recomendadas (prioridade alta)

### P1 — Padronizar a persistência

1. Criar um único objeto de estado de sessão e salvar sempre por uma função central.
2. Adicionar validação antes de gravar: verificar se há carro, pista, lap history e dados de telemetria válidos.
3. Salvar também metadados de contexto: clima, sessão, combustível inicial/final, pit status e timestamp.
4. Adicionar versão do schema de persistência para evitar mix de formatos antigos e novos.

### P2 — Separar memória “curta” e “longa” para a IA

1. Usar memória curta para a sessão atual e memória longa para histórico.
2. Dar mais peso aos dados recentes e menos peso aos dados antigos.
3. Resetar a memória curta ao detectar:
   - mudança de carro
   - mudança de pista
   - pit stop
   - reabastecimento
   - mudança forte de clima

### P3 — Reescrever o cálculo de combustível

1. Calcular consumo com base em diferença entre combustível inicial e final da volta, mas somente quando a volta for válida.
2. Ignorar explicitamente voltas com:
   - pit stop
   - reabastecimento
   - volta de saída do box
   - bandeira ou penalidade relevante
3. Usar uma média móvel recente, não um valor global antigo.
4. Separar “combustível restante” de “consumo por volta” em dois conceitos distintos.
5. Mostrar ao usuário tanto o combustível atual quanto o consumo estimado por volta com um intervalo de confiança.

### P4 — Adicionar logs e diagnósticos

1. Registrar em log cada cálculo de consumo com entrada e saída.
2. Exibir no painel o motivo de uma estimativa ter sido usada: live, histórico, memória, fallback.
3. Marcar quando o sistema está usando dados antigos ou com baixa confiança.

---

## 4) Melhorias de UX e confiabilidade

- Mostrar uma mensagem clara quando a IA está usando dados de histórico antigo.
- Mostrar o estado de confiança do cálculo de combustível.
- Adicionar opção para “recalcular a estratégia” após um pit stop ou reabastecimento.
- Exibir se a estimativa de combustível foi calculada com base em sessão atual, histórico recente ou memória antiga.

---

## 5) Prioridade sugerida

1. Corrigir persistência e restaurar corretamente o estado da sessão.
2. Reduzir o uso de memória antiga na IA.
3. Reescrever o cálculo de combustível com validação de contexto.
4. Melhorar logs e visibilidade para o usuário.

---

## 6) Conclusão

Os problemas não parecem ser de um único ponto isolado. Eles vêm de um conjunto de decisões de arquitetura: persistência espalhada, memória da IA sem controle de frescor e cálculo de combustível sem robustez para cenários reais de corrida. A correção mais importante é reorganizar esse fluxo para que o app use dados recentes, válidos e bem contextualizados antes de tomar decisões.
