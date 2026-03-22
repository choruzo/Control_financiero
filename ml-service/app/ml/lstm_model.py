"""
Arquitectura LSTM bidireccional para predicción de flujo de caja.

El modelo recibe una secuencia de N meses (income, expenses normalizados) y predice
el mes siguiente. Para predicciones multi-paso se usa rolling prediction.

MC Dropout se activa durante la inferencia para generar intervalos de confianza
(P10/P50/P90) mediante múltiples muestras estocásticas.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class CashflowLSTM(nn.Module):
    """LSTM bidireccional para predicción de ingresos y gastos mensuales."""

    def __init__(
        self,
        input_size: int = 2,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout_rate = dropout

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        # bidireccional → hidden_size * 2 → 2 salidas (income, expenses)
        self.fc = nn.Linear(hidden_size * 2, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Tensor de shape [batch_size, seq_len, 2] (income, expenses normalizados)

        Returns:
            Tensor de shape [batch_size, 2] (predicción del mes siguiente)
        """
        lstm_out, _ = self.lstm(x)
        last_out = lstm_out[:, -1, :]  # último timestep
        out = self.dropout(last_out)
        return self.fc(out)
