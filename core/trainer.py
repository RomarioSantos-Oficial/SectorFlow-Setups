"""
trainer.py — Loop de treinamento da rede neural.

Responsável por:
- Treinar o modelo com dados do banco (online e offline)
- Aplicar loss ponderada por reward
- Gerenciar checkpoints e logging

O treinamento online acontece a cada N voltas (~50ms no CPU).
O treinamento offline pode ser disparado pelo usuário.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from .brain import SetupNeuralNet, TORCH_AVAILABLE

if TORCH_AVAILABLE:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
else:
    # Dummy classes/objects if torch is not available
    class SetupNeuralNet:
        def __init__(self, *args, **kwargs):
            pass
        def train(self):
            pass
        def eval(self):
            pass
        def parameters(self):
            return []

    class DummyOptimizer:
        def __init__(self, *args, **kwargs):
            pass
        def zero_grad(self):
            pass
        def step(self):
            pass

    class DummyScheduler:
        def __init__(self, *args, **kwargs):
            pass
        def step(self, loss):
            pass

    class DummyMSELoss:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, predictions, targets):
            return torch.zeros_like(predictions) # Return zeros to avoid errors

    torch = None # Ensure torch is None if not available
    nn = None
    optim = None
    DataLoader = None
    TensorDataset = None

logger = logging.getLogger("LMU_VE.trainer")


@dataclass
class TrainingResult:
    """Resultado de uma sessão de treinamento."""
    epochs_completed: int
    final_loss: float
    avg_reward: float
    total_samples: int


if TORCH_AVAILABLE:
    class Trainer:
        pass
else:
    class Trainer:
        def __init__(self, model: SetupNeuralNet | None = None,
                     learning_rate: float = 1e-3):
            logger.warning("Trainer inicializado em modo heurístico (PyTorch não disponível).")
            self.model = None
            self.optimizer = None
            self.scheduler = None
            self.criterion = None
            self._learning_rate = learning_rate
            self._total_epochs = 0

        def set_model(self, model: SetupNeuralNet):
            logger.warning("set_model() chamado, mas PyTorch não está disponível. Ignorando.")

        def _init_optimizer(self):
            pass

        def train_online(self, training_data: list[dict],
                         epochs: int = 3, batch_size: int = 16) -> TrainingResult:
            logger.warning("Treinamento online chamado, mas PyTorch não está disponível. Retornando resultado dummy.")
            return TrainingResult(0, 0.0, 0.0, 0)

        def train_offline(self, training_data: list[dict],
                          epochs: int = 50, batch_size: int = 32) -> TrainingResult:
            logger.warning("Treinamento offline chamado, mas PyTorch não está disponível. Retornando resultado dummy.")
            return TrainingResult(0, 0.0, 0.0, 0)

        def _train(self, training_data: list[dict],
                   epochs: int, batch_size: int,
                   shuffle: bool = True) -> TrainingResult:
            logger.warning("_train() chamado, mas PyTorch não está disponível. Retornando resultado dummy.")
            return TrainingResult(0, 0.0, 0.0, 0)

        def _prioritize_experience(self, data: list[dict]) -> list[dict]:
            return data

        def _augment_data(self, data: list[dict]) -> list[dict]:
            return data

        @property
        def total_epochs(self) -> int:
            return 0

        @property
        def current_lr(self) -> float:
            return 0.0

        def _compute_epochs(self, num_samples: int) -> int:
            return 0
    """
    Treinador da rede neural com loss ponderada por reward.

    A loss é ponderada pelo reward de cada exemplo:
    - Reward positivo → reforça os pesos (aprenda a repetir)
    - Reward negativo → penaliza (aprenda a fazer o oposto)
    - Reward ~0 → peso baixo (pouco informativo)

    Inclui:
    - Experience Replay Priorizado (dados importantes treinam mais)
    - LR Scheduling (learning rate reduz automaticamente em platôs)
    - Data Augmentation (gera dados sintéticos para treinar mais rápido)
    """

    def __init__(self, model: SetupNeuralNet | None = None,
                 learning_rate: float = 1e-3):
        self.model = model
        self.optimizer = None
        self.scheduler = None
        self.criterion = nn.MSELoss(reduction="none")
        self._learning_rate = learning_rate
        self._total_epochs = 0
        if model is not None:
            self._init_optimizer()

    def set_model(self, model: SetupNeuralNet):
        """Define ou troca o modelo a ser treinado."""
        self.model = model
        self._init_optimizer()

    def _init_optimizer(self):
        """Inicializa o otimizador Adam com LR scheduling."""
        self.optimizer = optim.Adam(self.model.parameters(), lr=self._learning_rate)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=10,
            min_lr=1e-5, verbose=False
        )

    def train_online(self, training_data: list[dict],
                     epochs: int = 3, batch_size: int = 16) -> TrainingResult:
        """
        Treinamento online (durante o jogo).
        Rápido (~50ms no CPU) — roda a cada N voltas completadas.
        Preserva ordem temporal dos dados (shuffle=False).

        Args:
            training_data: Lista de dicts com 'input', 'output', 'reward', 'weight'
            epochs: Número de épocas (3 padrão para online)
            batch_size: Tamanho do mini-batch

        Returns:
            TrainingResult com métricas do treino
        """
        return self._train(training_data, epochs, batch_size, shuffle=False)

    def train_offline(self, training_data: list[dict],
                      epochs: int = 50, batch_size: int = 32) -> TrainingResult:
        """
        Treinamento offline (pós-sessão, manual).
        Usa TODOS os dados do banco por N épocas.
        Dados embaralhados para generalização (shuffle=True).

        Args:
            training_data: Lista completa de dados de treinamento
            epochs: Número de épocas (50 padrão para offline)
            batch_size: Tamanho do batch
        """
        epochs = self._compute_epochs(len(training_data))
        return self._train(training_data, epochs, batch_size, shuffle=True)

    def _train(self, training_data: list[dict],
               epochs: int, batch_size: int,
               shuffle: bool = True) -> TrainingResult:
        """
        Loop de treinamento com loss ponderada por reward.

        Loss para cada exemplo = MSE(predição, target) × weight
        Onde weight é derivado do reward:
        - Reward > 0: weight = reward (reforça)
        - Reward < 0: target é invertido (aprende o oposto)
        - Reward ≈ 0: weight = 0.1 (quase ignora)

        Inclui Experience Replay Priorizado:
        - Dados com reward extremo (|reward| > 0.5) → peso 3×
        - Dados recentes (últimas 5 sessões) → peso 2×
        - Dados antigos + reward ~0 → peso 0.5×
        """
        if not training_data:
            return TrainingResult(0, 0.0, 0.0, 0)

        if self.model is None or self.optimizer is None:
            logger.warning("Trainer: modelo não configurado. Use set_model() primeiro.")
            return TrainingResult(0, 0.0, 0.0, 0)

        # Experience Replay Priorizado: ajustar pesos por importância
        training_data = self._prioritize_experience(training_data)

        # Data Augmentation: gerar exemplos sintéticos
        training_data = self._augment_data(training_data)

        # Montar tensores
        inputs = torch.tensor(
            np.array([d["input"] for d in training_data]),
            dtype=torch.float32
        )
        targets = []
        weights = []
        for d in training_data:
            reward = d["reward"]
            output = d["output"].copy()

            if reward < 0:
                # Reward negativo: inverte o target
                # Ensina a IA a fazer o OPOSTO do que foi feito
                output = -output

            targets.append(output)
            weights.append(d["weight"])

        targets_tensor = torch.tensor(np.array(targets), dtype=torch.float32)
        weights_tensor = torch.tensor(weights, dtype=torch.float32)

        dataset = TensorDataset(inputs, targets_tensor, weights_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)

        self.model.train()
        total_loss = 0.0
        num_batches = 0

        for epoch in range(epochs):
            epoch_loss = 0.0
            for batch_inputs, batch_targets, batch_weights in dataloader:
                self.optimizer.zero_grad()

                # Forward pass
                predictions = self.model(batch_inputs)

                # Loss por exemplo (sem redução)
                loss_per_sample = self.criterion(predictions, batch_targets)

                # Média por outputs, depois ponderar por weight
                loss_per_sample = loss_per_sample.mean(dim=1)
                weighted_loss = (loss_per_sample * batch_weights).mean()

                # Backpropagation
                weighted_loss.backward()
                # Gradient clipping para estabilidade
                nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()

                epoch_loss += weighted_loss.item()
                num_batches += 1

            total_loss = epoch_loss

        self._total_epochs += epochs
        final_loss = total_loss / max(num_batches, 1)
        avg_reward = float(np.mean([d["reward"] for d in training_data]))

        # LR Scheduling: reduz learning rate se loss estagnou
        if self.scheduler is not None:
            self.scheduler.step(final_loss)

        current_lr = self.optimizer.param_groups[0]['lr']
        logger.info(
            "Treinamento: %d épocas, %d amostras, loss=%.4f, reward_médio=%.3f, lr=%.1e",
            epochs, len(training_data), final_loss, avg_reward, current_lr
        )

        return TrainingResult(
            epochs_completed=epochs,
            final_loss=final_loss,
            avg_reward=avg_reward,
            total_samples=len(training_data),
        )

    def _prioritize_experience(self, data: list[dict]) -> list[dict]:
        """
        Experience Replay Priorizado.
        Ajusta os pesos dos exemplos por importância:
        - Reward extremo (|r| > 0.5) → peso ×3 (sinal forte)
        - Dados recentes por timestamp real:
            ≤ 7 dias → ×2.0  (sessão recente)
            8-30 dias → ×1.5 (mês corrente)
            31-90 dias → ×1.0 (referência neutra)
            > 90 dias → ×0.7 (dados antigos — LMU pode ter sofrido update)
        - Reward ~0 → peso ×0.5 (pouco informativo)
        """
        now = datetime.now(tz=timezone.utc)

        for d in data:
            priority_multiplier = 1.0
            original_reward = d.get("reward", 0)
            reward = abs(original_reward)

            # Prioridade por reward
            if original_reward < -0.3: # Dado claramente prejudicial — ignorar no treinamento
                priority_multiplier = 0.0
            elif original_reward < 0: # Leve negativo — penalizar com peso pequeno
                priority_multiplier *= abs(original_reward) * 0.2
            elif original_reward > 0.5:
                priority_multiplier *= 3.0
            elif original_reward < 0.1:
                priority_multiplier *= 0.5
            else:
                priority_multiplier *= max(original_reward, 0.05)

            # Prioridade por recência (timestamp real)
            created_at = d.get("created_at")
            if created_at:
                try:
                    # SQLite retorna ISO string sem timezone
                    ts = datetime.fromisoformat(str(created_at))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    days_old = max(0, (now - ts).total_seconds() / 86400)
                    if days_old <= 7:
                        priority_multiplier *= 2.0
                    elif days_old <= 30:
                        priority_multiplier *= 1.5
                    elif days_old > 90:
                        priority_multiplier *= 0.7
                    # 31-90 dias → ×1.0 (neutro)
                except (ValueError, TypeError):
                    # Sem timestamp válido → usar posição como fallback
                    pass

            d["weight"] = d.get("weight", 1.0) * priority_multiplier

        return data

    def _augment_data(self, data: list[dict]) -> list[dict]:
        """
        Data Augmentation: gera exemplos sintéticos para treinar mais rápido.

        Para cada exemplo com reward forte (|r| > 0.3):
        1. Inversão: inverte deltas + inverte reward (ex: +2 → -2 seria ruim)
        2. Ruído: adiciona ±5% de ruído gaussiano nos inputs
        """
        augmented = list(data)  # cópia

        for d in data:
            reward = d.get("reward", 0)
            if abs(reward) < 0.3:
                continue  # Só augmenta dados informativos

            inp = np.array(d["input"])
            out = np.array(d["output"])

            # 1. Inversão: se +2 camber foi bom, -2 seria ruim
            augmented.append({
                "input": inp.copy(),
                "output": (-out).tolist(),
                "reward": -reward,
                "weight": d.get("weight", 1.0) * 0.7,  # Peso menor que real
            })

            # 2. Ruído: pequena variação nos inputs
            noise = np.random.normal(0, 0.05, size=inp.shape)
            noisy_input = inp + noise * np.abs(inp + 1e-8)
            # Aplicar clipping para garantir que os outputs sintéticos fiquem no range [-1, 1]
            clipped_output = np.clip(out + np.random.normal(0, 0.05, size=out.shape), -1.0, 1.0)
            augmented.append({
                "input": noisy_input.tolist(),
                "output": clipped_output.tolist(),
                "reward": reward,
                "weight": d.get("weight", 1.0) * 0.5, # Peso menor que real
            })

        logger.debug("Data augmentation: %d → %d exemplos", len(data), len(augmented))
        return augmented

    @property
    def total_epochs(self) -> int:
        """Total de épocas acumuladas."""
        return self._total_epochs

    @property
    def current_lr(self) -> float:
        """Learning rate atual."""
        if self.optimizer is None:
            return self._learning_rate
        return self.optimizer.param_groups[0]['lr']

    def _compute_epochs(self, num_samples: int) -> int:
        """Épocas inversamente proporcionais ao volume de dados."""
        if num_samples < 50:
            return 200   # Poucos dados: mais épocas para aprender
        if num_samples < 200:
            return 100
        if num_samples < 1000:
            return 50    # Padrão atual
        return 30        # Muitos dados: menos épocas, evitar overfitting
