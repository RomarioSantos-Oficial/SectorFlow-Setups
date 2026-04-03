"""
normalizer.py — Normalização de features para a rede neural.

Sem normalização, a rede daria peso desproporcional a features
com valores maiores (ex: Kelvin ~350 vs feedback -1/+1).

Implementa StandardScaler (média=0, desvio=1) que é atualizado
incrementalmente conforme novos dados chegam.
Os parâmetros de normalização são salvos junto com o modelo .pth.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger("LMU_VE.normalizer")


class FeatureNormalizer:
    """
    Normalização incremental das features de telemetria.

    Usa StandardScaler (z-score): x_norm = (x - média) / desvio_padrão

    O scaler é atualizado a cada nova volta, acumulando estatísticas
    sem precisar manter todos os dados em memória.
    """

    def __init__(self, num_features: int = 49):
        self.num_features = num_features
        # Estatísticas acumuladas (Welford's algorithm incremental)
        self._count = 0
        self._mean = np.zeros(num_features, dtype=np.float64)
        self._m2 = np.zeros(num_features, dtype=np.float64)
        # Cache calculado
        self._std = np.ones(num_features, dtype=np.float64)
        self.last_normalized = None  # Último vetor normalizado (para chat LLM)

    def update(self, x: np.ndarray):
        """
        Atualiza as estatísticas com um novo vetor de features.
        Usa o algoritmo de Welford para cálculo incremental de
        média e variância (estável numericamente).

        Args:
            x: Vetor de features (num_features,)
        """
        self._count += 1
        delta = x - self._mean
        self._mean += delta / self._count
        delta2 = x - self._mean
        self._m2 += delta * delta2
        # Atualizar desvio padrão cache
        if self._count > 1:
            variance = self._m2 / (self._count - 1)
            self._std = np.sqrt(np.maximum(variance, 1e-8))

    def normalize(self, x: np.ndarray) -> np.ndarray:
        """
        Normaliza um vetor de features usando as estatísticas acumuladas.

        Args:
            x: Vetor de features (num_features,)

        Returns:
            Vetor normalizado (média ~0, desvio ~1)
        """
        if self._count < 2:
            result = x.astype(np.float32)
        else:
            result = ((x - self._mean) / self._std).astype(np.float32)
        self.last_normalized = result
        return result

    def denormalize(self, x_norm: np.ndarray) -> np.ndarray:
        """Reverte a normalização."""
        return (x_norm * self._std + self._mean).astype(np.float32)

    @property
    def is_fitted(self) -> bool:
        """Retorna True se o scaler tem dados suficientes."""
        return self._count >= 5

    def save(self, path):
        """Salva os parâmetros de normalização."""
        path = Path(path)
        np.savez(path,
                 count=self._count,
                 mean=self._mean,
                 m2=self._m2,
                 std=self._std)

    def load(self, path):
        """Carrega parâmetros de normalização salvos."""
        path = Path(path)
        if not path.exists():
            return
        data = np.load(path)
        self._count = int(data["count"])
        self._mean = data["mean"]
        self._m2 = data["m2"]
        self._std = data["std"]
        logger.info("Normalizer carregado (%d amostras)", self._count)

    def should_reset(self, max_count: int = 100_000) -> bool:
        """Retorna True se o normalizer acumulou amostras demais."""
        return self._count > max_count

    def soft_reset(self, keep_ratio: float = 0.2):
        """
        Reset parcial: mantém as estatísticas mas reduz o peso
        das amostras antigas, como se apenas keep_ratio dos dados
        existissem. Preserva média e desvio, mas permite que
        novos dados influenciem mais rapidamente.
        """
        if self._count < 10:
            return
        new_count = max(int(self._count * keep_ratio), 5)
        # m2 escala linearmente com count
        self._m2 *= (new_count / self._count)
        self._count = new_count
        logger.info("Normalizer soft-reset: count reduzido para %d", new_count)
