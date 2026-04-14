# Relatório Técnico: Otimização Estrutural e Engenharia de Setup para Le Mans Ultimate

Este relatório detalha as melhorias propostas para o **SectorFlow Setups**, focando em performance do sistema, precisão na amostragem de dados e regras de engenharia específicas para as classes e condições do **Le Mans Ultimate (LMU)**.

---

## 1. Otimização de Performance e Layout (UI)
Muitos dos travamentos relatados ocorrem devido ao processamento síncrono de grandes volumes de telemetria e atualizações de interface.

| Problema | Solução Proposta | Impacto |
| :--- | :--- | :--- |
| **Interface Travando** | Implementar `asyncio` ou `threading` para o loop de atualização da GUI, separando a lógica de renderização da lógica de cálculo. | Alta Fluidez |
| **Carga de Dados no DB** | Implementar **Paginação** na aba de Banco de Dados e carregar apenas os últimos 20 registros por padrão. | Menor uso de RAM |
| **Atualização Excessiva** | Reduzir a frequência de atualização de widgets não críticos (ex: clima) para 1Hz, mantendo apenas pneus/velocidade em alta frequência. | Menor CPU |

---

## 2. Amostragem Inteligente de Dados (Event-Based)
Atualmente, o sistema coleta dados a 10Hz de forma contínua. Propomos uma transição para **Amostragem por Eventos Críticos** para reduzir o ruído e focar no que realmente importa para o setup.

### Pontos de Coleta (Snapshots):
1.  **Zona de Frenagem (Threshold):** Capturar pressão de pneus e temperatura de discos no pico de desaceleração.
2.  **Apex (Vmin):** Capturar *Roll*, *Pitch* e *Ride Height* no ponto de menor velocidade da curva (máxima carga lateral).
3.  **Saída de Curva (Traction):** Capturar *Slip Angle* e ativação de TC no início da aceleração total.
4.  **Reta Principal (Top Speed):** Capturar velocidade máxima e arrasto (*Drag*) para validar a asa traseira.

---

## 3. Matriz de Regras de Setup (LMU Específico)
O simulador LMU exige abordagens diferentes dependendo da classe, marca e condição climática.

### A. Diferenciação por Classe e Pneus
- **LMGT3 (Goodyear):** Focar em 2 compostos (Soft/Medium ou Medium/Hard). Alvo de pressão: **1.95 bar hot**.
- **Hypercar/GTE (Michelin):** Gerenciar até 4 compostos. Alvo de pressão: **1.85 bar hot**.
- **Regra de Crossover:** A IA deve sugerir troca para pneus *Wet* quando a umidade da pista atingir **15%**.

### B. Condições de Sessão e Clima
- **Qualificação:** 
  - Fechar dutos de freio/radiador em 1-2 cliques para aquecimento rápido.
  - Pressões de pneus ligeiramente mais altas para pico de performance imediato.
- **Chuva (Wet):**
  - **Asa:** Aumento de 1-3 níveis na asa traseira.
  - **Suspensão:** Amaciamento global de molas e barras anti-rolagem (ARB) para maximizar o contato.
  - **Freios:** Aumentar dutos de freio para evitar travamentos por superaquecimento local em poças.

### C. Especificidades por Marca (GT3/GTE)
- **Motor Dianteiro (ex: BMW, Aston Martin):** A IA deve priorizar o equilíbrio do eixo dianteiro com camber mais agressivo e traseira mais rígida.
- **Motor Central/Traseiro (ex: Ferrari, Porsche):** Priorizar estabilidade de frenagem e tração, evitando molas traseiras excessivamente rígidas que causem sobre-esterço súbito.

---

## 4. Sistema de Salvamento e Aprendizagem
Para evitar corrupção e melhorar a "inteligência" da rede neural:
- **Checksum de Dados:** Validar a integridade do arquivo `.svm` antes e depois de cada gravação.
- **Normalização por Pista:** Os dados de telemetria serão comparados apenas com a média daquela pista específica, evitando que o "vácuo" de Monza polua os dados de "downforce" de Spa.
- **Knowledge Distillation 2.0:** Incluir o tipo de composto de pneu e a marca do carro como inputs diretos na rede neural, permitindo que a IA aprenda as nuances de cada fabricante.

---

## 5. Próximos Passos Recomendados
1.  **Refatoração do `telemetry_reader.py`** para incluir os gatilhos de eventos.
2.  **Atualização do `heuristics.py`** com a nova matriz de regras por marca/classe.
3.  **Implementação de um `Loading Overlay`** na GUI para processos pesados, evitando a percepção de travamento.

---
**Relatório gerado por:** Manus AI
**Data:** 14 de Abril de 2026
**Foco:** Le Mans Ultimate Simulator Performance & Engineering
