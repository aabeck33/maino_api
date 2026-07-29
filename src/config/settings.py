"""Centralized project settings and file paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataFiles:
    """Logical mapping for all data files consumed by the application."""

    sales_orders: str = "pedidos_confirmados.xlsx"
    products: str = "produtos.xlsx"
    history: str = "vendas - All Drive - Histórico Gerensys.xlsx"
    customers: str = "clientes.xlsx"
    profitability_output: str = "indicadores_financeiros.xlsx"
    profitability_summary_output: str = "indicadores_financeiros_resumo.xlsx"


@dataclass(frozen=True)
class AppPaths:
    """Canonical project folders used by all modules."""

    project_root: Path
    src_dir: Path
    work_dir: Path
    data_dir: Path


class _Settings:
    """Singleton-like access to filesystem settings."""

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.paths = AppPaths(
            project_root=project_root,
            src_dir=project_root / "src",
            work_dir=project_root / "work",
            data_dir=project_root / "work",
        )
        self.data_files = DataFiles()

    def data_file_path(self, filename: str) -> Path:
        """Builds an absolute path for a file under the configured data directory."""
        return self.paths.data_dir / filename


SETTINGS = _Settings()
