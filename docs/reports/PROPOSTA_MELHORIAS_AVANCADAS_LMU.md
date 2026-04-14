# 🏎️ Proposta de Melhorias Avançadas — SectorFlow Setups (Le Mans Ultimate)

Este documento detalha as melhorias estratégicas para o **SectorFlow Setups**, focando exclusivamente nas mecânicas internas, regras e classes de veículos do jogo **Le Mans Ultimate (LMU)**.

---

## 1. Módulo de Gestão de Energia Virtual (NRG)
O sistema de Virtual Energy no LMU é uma das mecânicas mais críticas para corridas de endurance. A IA deve ser capaz de otimizar o setup para este sistema.

| Funcionalidade | Descrição Técnica no LMU | Melhoria Proposta |
| :--- | :--- | :--- |
| **Otimização de Stint** | O NRG limita o consumo total (combustível + bateria) por stint. | Calcular o `Virtual Energy Consumption per Lap` e sugerir mapas de motor (Engine Map) e níveis de Regen para atingir a meta de voltas por stint. |
| **Mapa de Motor Elétrico** | Controla a entrega de potência híbrida (Hypercars). | Sugerir ajustes no mapa elétrico baseados na telemetria de tração (ex: reduzir entrega em saídas de curva se houver muito wheelspin). |
| **Regen Level** | Recuperação de energia sob frenagem. | Monitorar a temperatura dos freios e o estado da bateria; sugerir redução de Regen se a bateria estiver 100% (evitando superaquecimento dos freios mecânicos). |

---

## 2. Especialização por Classe de Veículo
O LMU possui comportamentos físicos distintos para cada classe. O assistente deve adaptar suas heurísticas.

### 🔵 Hypercar (LMH & LMDh)
*   **Complexidade Eletrônica:** Focar em diferenciais (Diff Preload) e mapas de motor.
*   **Aero Rake:** Sensibilidade extrema à altura de rodagem (Ride Height). A IA deve sugerir ajustes milimétricos para manter o `Aero Balance` estável em altas velocidades (ex: Le Mans).
*   **Michelin Cold Tyres:** Implementar um "Modo de Aquecimento" que sugere pressões mais altas para facilitar o ganho de temperatura na saída dos boxes.

### 🔴 LMP2 & LMP3
*   **Simplicidade Pura:** Focar em equilíbrio mecânico (molas e barras estabilizadoras).
*   **Downforce:** Otimizar a relação entre `Rear Wing` e `Ride Height` para maximizar a velocidade de reta sem perder estabilidade em curvas rápidas.
*   **Traction Control:** Ajustar o TC baseado no desgaste dos pneus traseiros ao longo do stint.

### 🟢 LMGT3 & GTE
*   **ABS & TC:** Essencial para GT3. A IA deve analisar a frequência de intervenção do ABS e sugerir ajustes no `Brake Bias` ou `Brake Pressure`.
*   **Mechanical Grip:** Focar em `Camber` e `Toe` para lidar com o peso maior dos GTs em comparação aos protótipos.
*   **Diferenças de Marca:**
    *   *Ferrari/Porsche (Mid-Engine):* Focar em estabilidade de traseira na entrada de curva.
    *   *BMW/Aston Martin (Front-Engine):* Focar em reduzir o understeer na entrada e proteger os pneus dianteiros.

---

## 3. Calibração de Pneus Michelin (Lógica do Jogo)
No LMU, os pneus Michelin têm janelas de operação muito específicas.

*   **Pressão Alvo (Hot Pressure):** O "sweet spot" no jogo é geralmente entre **26.0 e 27.0 PSI** (aprox. 180-186 kPa).
*   **Temperatura Alvo:** 
    *   *Slick Soft:* 70°C - 90°C.
    *   *Slick Medium/Hard:* 80°C - 105°C.
*   **Melhoria IA:** O assistente deve ler a pressão/temperatura média da volta anterior e calcular o ajuste exato de cliques no setup para atingir o alvo na volta seguinte.

---

## 4. Adaptação por Pista e Modelo
As sugestões devem ser contextualizadas pelo banco de dados de pistas do LMU.

*   **Pistas de Alta Velocidade (Le Mans, Spa, Monza):** Priorizar `Low Drag` e estabilidade de `Rake`.
*   **Pistas Técnicas (Bahrain, Portimão, Fuji):** Priorizar `Mechanical Grip` e resposta de direção.
*   **Análise de Zebras (Kerbs):** Se a telemetria detectar altos picos de aceleração vertical (suspensão batendo no fundo), sugerir aumento da `Slow Bump` ou `Ride Height` especificamente para aquela pista.

---

## 5. Interface de "Engenheiro de Pista"
Adicionar um modo de diálogo focado no jogo:
*   "Como está o balanço na Tertre Rouge?"
*   "O carro está instável na frenagem para a Mulsanne?"
*   A IA deve correlacionar esses nomes de curvas com os micro-setores da telemetria gravada.

---
**Próximos Passos:** Integrar essas regras ao arquivo `core/heuristics.py` e criar perfis de classes no banco de dados.
