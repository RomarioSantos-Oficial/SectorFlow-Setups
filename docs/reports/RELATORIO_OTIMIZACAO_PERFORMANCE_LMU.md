# Relatório Técnico: Otimização de Performance e Responsividade do SectorFlow Setups para Le Mans Ultimate

Este relatório aborda os problemas de lentidão e travamento na interface do **SectorFlow Setups**, propondo soluções para otimizar o carregamento do sistema, o processamento de dados e a responsividade da GUI, com foco nas especificidades do **Le Mans Ultimate (LMU)**.

---

## 1. Diagnóstico de Gargalos de Performance

### 1.1. Interface Gráfica (GUI)
O principal problema de travamento da interface (`gui/app.py`, `gui/tab_telemetry.py`, `gui/tab_database.py`) parece estar relacionado à natureza síncrona das atualizações de widgets e ao volume de dados processados. A aba de telemetria (`tab_telemetry.py`) atualiza muitos elementos visuais em alta frequência, e a aba de banco de dados (`tab_database.py`) realiza consultas SQL diretas e carrega todo o conteúdo em `CTkTextbox` sem paginação, o que pode ser lento para grandes volumes de dados.

### 1.2. Coleta e Amostragem de Telemetria (`data/telemetry_reader.py`)
A coleta contínua de telemetria a 10Hz (`SAMPLE_INTERVAL_SEC = 0.1`) gera um grande volume de dados por volta (`MAX_SAMPLES_PER_LAP = 2000`). Embora a acumulação use `deque` com `maxlen`, o processamento e a geração de `LapSummary` ao final de cada volta podem ser custosos, especialmente se a thread principal for bloqueada.

### 1.3. Operações de Banco de Dados (`data/database.py`)
A inicialização do `DatabaseManager` é síncrona e envolve a leitura de um esquema SQL considerável. Operações de `INSERT` e `UPDATE` frequentes, com `commit` imediato, podem introduzir latência. Embora o `sqlite3` seja rápido, a falta de paralelismo ou batching pode impactar a responsividade em cenários de alta carga.

### 1.4. Carregamento de Modelos de IA (`core/brain.py`)
O `ModelManager` utiliza `torch.load(map_location='cpu', weights_only=True)` para carregar modelos. Esta operação é síncrona e pode ser demorada para modelos maiores, bloqueando a GUI durante a inicialização ou ao alternar entre carros/pistas que exigem o carregamento de um novo modelo.

### 1.5. Destilação de Conhecimento (`core/knowledge_distiller.py`)
Embora a destilação ocorra em uma thread separada, a geração de cenários sintéticos (`generate_scenarios`) é atualmente muito genérica. A criação de cenários aleatórios para `CAR_CLASSES` e `SESSION_TYPES` sem considerar as especificidades do LMU (compostos de pneu por classe, regras de chuva/seco, etc.) pode levar a um treinamento ineficiente e a um modelo que demora mais para convergir para um estado autônomo útil.

---

## 2. Soluções Propostas para Otimização

### 2.1. Otimização da Interface Gráfica (UI)

| Problema | Solução Proposta | Impacto Esperado |
| :--- | :--- | :--- |
| **Travamentos da GUI** | Implementar um sistema de **atualização assíncrona** para a GUI, utilizando `threading` ou `asyncio` para descarregar tarefas pesadas da thread principal. Widgets críticos (pneus, velocidade) podem ter uma taxa de atualização maior, enquanto outros (clima, estatísticas) podem ser atualizados em intervalos maiores (ex: 1Hz). | **Alta:** Eliminação de travamentos, interface fluida. |
| **Carga de Dados no DB** | Implementar **paginação** e **carregamento sob demanda** (`lazy loading`) na `DatabaseTab`. Exibir apenas um subconjunto de dados (ex: 10-20 registros) e carregar mais apenas quando o usuário rolar ou solicitar. | **Média:** Redução do uso de memória e CPU ao exibir dados históricos. |
| **Feedback Visual** | Adicionar um **overlay de carregamento** ou indicadores de progresso (ex: `ctk.CTkProgressBar`) para operações demoradas (carregamento de modelo, destilação, exportação de dados). | **Média:** Melhoria da percepção do usuário sobre a responsividade do sistema. |

### 2.2. Amostragem Inteligente de Dados

Para reduzir o volume de dados e focar na relevância, propomos uma **Amostragem por Eventos Críticos** em `data/telemetry_reader.py`.

| Evento Crítico | Dados a Coletar (Snapshot) | Justificativa |
| :--- | :--- | :--- |
| **Frenagem** | Pressão/Temperatura de Freio, Carga Vertical, Desaceleração Longitudinal | Diagnóstico de bloqueio de rodas, balanceamento de freio, estabilidade em frenagem. |
| **Apex da Curva** | Roll, Pitch, Heave, Ride Height, Carga Lateral, Velocidade Mínima | Equilíbrio aerodinâmico, rigidez da suspensão, comportamento em apoio. |
| **Saída de Curva** | Slip Angle, Aceleração Longitudinal, Ativação do TC, Desgaste de Pneu | Tração, sobre-esterço de potência, otimização do diferencial. |
| **Reta Principal** | Velocidade Máxima, Downforce (F/R), Drag | Eficiência aerodinâmica, configuração de asa. |

Esta abordagem reduzirá o `MAX_SAMPLES_PER_LAP` e o volume de dados armazenados, focando em informações acionáveis para o setup.

### 2.3. Otimização de Operações de Banco de Dados

| Problema | Solução Proposta | Impacto Esperado |
| :--- | :--- | :--- |
| **Inicialização Síncrona** | Carregar o esquema do banco de dados e realizar migrações em uma **thread de inicialização separada**. A GUI pode exibir uma tela de *splash* ou um indicador de carregamento durante este processo. | **Alta:** Redução do tempo de inicialização percebido pelo usuário. |
| **Commits Frequentes** | Implementar **batching de commits** para operações de gravação de telemetria e dados de treinamento. Agrupar várias operações de `INSERT` ou `UPDATE` em uma única transação antes de chamar `commit()`. | **Média:** Melhoria da performance de gravação e redução de I/O de disco. |

### 2.4. Carregamento Assíncrono de Modelos de IA

| Problema | Solução Proposta | Impacto Esperado |
| :--- | :--- | :--- |
| **Carregamento Bloqueante** | Carregar modelos de IA (`torch.load`) em uma **thread de background**. A GUI pode exibir um indicador de carregamento na aba de setup enquanto o modelo é carregado. | **Alta:** Eliminação de travamentos ao carregar ou trocar modelos de IA. |

### 2.5. Melhorias na Destilação de Conhecimento (Knowledge Distillation)

Para tornar a destilação mais eficiente e relevante para o LMU:

| Problema | Solução Proposta | Impacto Esperado |
| :--- | :--- | :--- |
| **Cenários Genéricos** | Refatorar `generate_scenarios` em `core/knowledge_distiller.py` para gerar cenários **específicos por classe, composto de pneu e condição climática** (seco/chuva). Utilizar os dados do `adapter/rf2_data.py` para mapear os compostos de pneu disponíveis por classe no LMU. | **Alta:** Treinamento mais rápido e preciso da IA, resultando em sugestões mais relevantes. |
| **Falta de Especificidade** | Incluir **marca do carro** e **tipo de pista** (alta velocidade, técnica) como parâmetros na geração de cenários, permitindo que a IA aprenda as nuances de setup por fabricante e layout de pista. | **Alta:** Sugestões de setup mais refinadas e adaptadas às características de cada carro e pista. |

---

## 3. Regras Específicas de Setup (Aprofundamento)

Com base na pesquisa, as regras de setup devem ser mais granulares:

### 3.1. Pneus e Condições
- **Compostos:** A IA deve diferenciar entre os 2 compostos da GT3 (Goodyear) e os 3-4 da Hypercar/GTE (Michelin), aplicando janelas de pressão e temperatura ideais específicas para cada um. O `adapter/rf2_data.py` fornece os nomes dos compostos (`front_tire_compound_name`, `rear_tire_compound_name`).
- **Seco vs. Chuva:**
    - **Chuva:** Aumentar asa traseira (+1 a +3 cliques), amolecer suspensão (molas, ARBs), aumentar dutos de freio para evitar superaquecimento e melhorar a modulação. A IA deve sugerir a troca para pneus de chuva quando a umidade da pista (`wetness` em `adapter/rf2_data.py`) atingir **15%**.
    - **Seco:** Otimizar para downforce ou velocidade final dependendo da pista.
- **Qualificação vs. Corrida:**
    - **Qualificação:** Pressões de pneu ligeiramente mais altas para *peak grip* imediato. Dutos de radiador mais fechados para otimizar temperatura do motor (se o tempo de sessão permitir). Ajustes de freio para máxima mordida.
    - **Corrida:** Pressões de pneu para consistência. Dutos de radiador mais abertos para resfriamento. Ajustes de freio para durabilidade.

### 3.2. Diferenciação por Carro/Marca
- **GT3/GTE:**
    - **Motor Dianteiro (BMW M4, Aston Martin Vantage):** A IA deve priorizar o equilíbrio do eixo dianteiro com camber mais agressivo e traseira mais rígida para combater o subesterço natural.
    - **Motor Central/Traseiro (Ferrari 296, Porsche 911, McLaren 720S):** Focar na estabilidade de frenagem e tração. Evitar molas traseiras excessivamente rígidas que podem causar sobre-esterço súbito em curvas de alta.

### 3.3. Coleta de Dados para Regras Específicas
- **Desgaste de Pneus:** Monitorar `tyre.wear()` do `adapter/rf2_data.py` para alertar sobre degradação e sugerir ajustes de pressão ou troca.
- **Temperaturas:** Usar `tyre.surface_temperature_ico()` e `tyre.core_temperature()` para monitorar o aquecimento e o *spread* de temperatura, sugerindo ajustes de camber, toe e pressão.
- **Freios:** Monitorar `brake.temperature()` para evitar superaquecimento ou subaquecimento, sugerindo ajustes nos dutos de freio.

---

## 4. Sistema de Salvamento e Tratamento de Dados (Robustez)

| Problema | Solução Proposta | Impacto Esperado |
| :--- | :--- | :--- |
| **Corrupção de Dados** | Implementar **checksums** (ex: SHA256) para arquivos `.svm` e dados de treinamento. Verificar o checksum antes de carregar e após salvar para garantir a integridade. | **Alta:** Prevenção de perda de dados e setups corrompidos. |
| **Normalização Inadequada** | Reforçar a **normalização por pista e por carro** no `core/normalizer.py`. Cada combinação carro-pista deve ter seu próprio conjunto de estatísticas de normalização para evitar que dados de uma pista distorçam a análise de outra. | **Alta:** Melhoria da precisão da IA, pois os dados são comparados em um contexto relevante. |
| **Gerenciamento de Memória** | Implementar um **sistema de cache inteligente** para modelos de IA e normalizadores. Carregar apenas os modelos e normalizadores da combinação carro-pista ativa, e descarregar os não utilizados após um período de inatividade. | **Média:** Redução do consumo de RAM, especialmente para usuários com muitos carros/pistas. |

---

## 5. Próximos Passos Recomendados (Implementação)

1.  **Fase 1: Refatoração da GUI e Assincronismo:** Implementar `threading` ou `asyncio` para o loop de atualização da GUI e para o carregamento de modelos/DB. Adicionar *loading overlays*.
2.  **Fase 2: Amostragem Inteligente:** Modificar `data/telemetry_reader.py` para coletar dados por eventos críticos, reduzindo o volume e aumentando a relevância.
3.  **Fase 3: Matriz de Regras de Setup:** Atualizar `core/heuristics.py` e `core/knowledge_distiller.py` com as regras específicas por classe, composto de pneu, condição climática e marca de carro.
4.  **Fase 4: Robustez do Sistema:** Implementar checksums e aprimorar o cache de normalizadores e modelos.

---
**Relatório gerado por:** Manus AI
**Data:** 14 de Abril de 2026
**Foco:** Otimização de Performance e Engenharia de Setup para Le Mans Ultimate
