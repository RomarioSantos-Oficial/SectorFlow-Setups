# Descobertas de Pesquisa - Le Mans Ultimate (LMU)

## Pneus e Pressões (Michelin/Goodyear)
- **Target Geral:** ~1.8 a 1.9 bar (180-190 kPa) hot.
- **Temperatura de Operação (Core/Rubber):** ~80-90°C é o ideal para grip.
- **Diferença de Classes:**
  - **Hypercar (Michelin):** Usa sliders que muitas vezes não chegam aos 1.8 bar reais recomendados pela FIA, mas o "meta" no jogo tende a pressões mínimas e camber baixo para evitar superaquecimento da carcaça.
  - **LMP2 (Goodyear):** Diferente da Michelin, possui janelas próprias. Recomendação FIA (Spa): 1.95 bar hot.
  - **GT3:** Novo modelo de pneus Michelin (2024/2025). Janela de temperatura ideal citada como 80-90°C.
- **Condições de Chuva:**
  - Pressões precisam ser ajustadas para evitar aquaplanagem e manter temperatura (geralmente mais altas que seco para "abrir" os sulcos).
  - Linhas de direção mudam (evitar puddles).

## Comportamento do Simulador (rFactor 2 Engine)
- **Carcass vs Surface vs Rubber Temp:** A temperatura do "Rubber" (logo abaixo da superfície) é a mais estável e importante para o grip.
- **Meta Atual:** Alguns usuários relatam que pressões mínimas e camber baixo são mais eficientes devido à forma como a carcaça é simulada, embora isso possa mudar com atualizações.

## Regras de Setup por Sessão
- **Qualificação:** Foco em temperatura rápida (fechar dutos de freio/radiador para aquecer pneus mais rápido em 1-2 voltas).
- **Corrida:** Foco em estabilidade térmica e desgaste (dutos mais abertos).

## Estratégia de Amostragem (Melhoria)
- Em vez de coletar dados de cada frame, focar em:
  - **Pico de frenagem:** Temp de freio e pressão de pneu sob carga.
  - **Apex:** Grip lateral e inclinação (roll).
  - **Saída de curva:** Tração e temperatura de superfície.

## Compostos de Pneus por Categoria (2025/2026 Meta)
### LMGT3 (Goodyear)
- **Compostos:** Geralmente **2 compostos** (Soft/Medium ou Medium/Hard) dependendo da pista. Recentemente introduzido o "Red-labeled Hard" em pistas de alta abrasão (ex: São Paulo).
- **Características:** Mais sensíveis ao BoP. Pneus Goodyear no LMU têm janelas de pressão ligeiramente diferentes dos Michelin (focar em 1.95 bar hot como base).

### Hypercar & GTE (Michelin)
- **Compostos:** Até **3 ou 4 compostos** disponíveis (Soft Cold, Soft Hot, Medium, Hard).
- **Alocação:** A Michelin define 2 dos 3 compostos para corridas comuns; Le Mans geralmente tem os 3 disponíveis.
- **Estratégia:** Soft Cold para Qualy ou noites frias; Hard para stints duplos em pistas abrasivas (Bahrain, Sebring).

### Pneus de Chuva (Wet/Monsoon)
- **Crossover:** ~15% de umidade na pista é o ponto de troca entre slick e wet.
- **Pressão:** Deve ser aumentada significativamente para evitar aquaplanagem e manter a carcaça "aberta" para drenagem.

## Diferenças por Marca e Arquitetura (GT3/GTE)
### Motor Dianteiro (BMW M4, Aston Martin Vantage)
- **Tendência:** Subesterço na entrada; melhor estabilidade em frenagem.
- **Setup:** Requer traseira mais solta (ARB traseira rígida) e camber dianteiro agressivo para compensar o peso do motor.

### Motor Central/Traseiro (Ferrari 296, Porsche 911, McLaren 720S)
- **Tendência:** Sobre-esterço na saída; excelente tração.
- **Setup:** Requer cuidado com a traseira em frenagens em apoio; molas traseiras mais rígidas podem causar instabilidade.

## Otimização de Amostragem (Engenharia)
- **Eventos Críticos:** 
  1. **Início da Frenagem:** Medir temperatura de disco e pressão de pneu (carga longitudinal).
  2. **Apex (Vmin):** Medir Roll e Pitch (equilíbrio aerodinâmico).
  3. **Início da Aceleração:** Medir Slip Angle e tração (eficiência do TC).
- **Redução de Dados:** Descartar dados de retas (exceto Top Speed e Drag) para reduzir o peso do processamento em 70%.
