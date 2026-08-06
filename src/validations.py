"""Validaciones estructurales, numéricas y cruzadas de los datos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from src.data_loader import DataBundle

Severity = Literal["ERROR", "ADVERTENCIA"]

REQUIRED_COLUMNS = {
    "ingredientes": (
        "ingrediente_id",
        "nombre",
        "proveedor",
        "unidad_base",
        "formato_compra",
        "unidad_base_por_formato",
        "es_perecedero",
    ),
    "consumo_historico": (
        "sucursal",
        "ingrediente_id",
        "semana",
        "consumo_unidad_base",
    ),
    "inventario_actual": (
        "sucursal",
        "ingrediente_id",
        "stock_actual_unidad_base",
    ),
    "orden_compra": (
        "sucursal",
        "ingrediente_id",
        "cantidad_formatos",
    ),
}

NUMERIC_COLUMNS = {
    "ingredientes": ("unidad_base_por_formato",),
    "consumo_historico": ("consumo_unidad_base",),
    "inventario_actual": ("stock_actual_unidad_base",),
    "orden_compra": ("cantidad_formatos",),
}

UNIQUE_KEYS = {
    "ingredientes": ("ingrediente_id",),
    "consumo_historico": ("sucursal", "ingrediente_id", "semana"),
    "inventario_actual": ("sucursal", "ingrediente_id"),
    "orden_compra": ("sucursal", "ingrediente_id"),
}

EXPECTED_WEEKS = {f"S{week}" for week in range(1, 7)}


@dataclass(frozen=True)
class ValidationIssue:
    """Problema encontrado durante la revisión de los datos."""

    severity: Severity
    code: str
    dataset: str
    message: str
    row_count: int = 0
    examples: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Representación tabular amigable para Streamlit y pruebas."""
        return {
            "Nivel": self.severity,
            "Código": self.code,
            "Archivo": self.dataset,
            "Filas": self.row_count,
            "Mensaje": self.message,
            "Ejemplos": " | ".join(self.examples),
        }


@dataclass(frozen=True)
class ValidationReport:
    """Resultado de la validación y versión numérica limpia de los datos."""

    cleaned_data: DataBundle
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "ERROR")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "ADVERTENCIA")

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte los hallazgos en una tabla ordenada por gravedad."""
        columns = ("Nivel", "Código", "Archivo", "Filas", "Mensaje", "Ejemplos")
        if not self.issues:
            return pd.DataFrame(columns=columns)

        result = pd.DataFrame(issue.as_dict() for issue in self.issues)
        severity_order = pd.CategoricalDtype(["ERROR", "ADVERTENCIA"], ordered=True)
        result["Nivel"] = result["Nivel"].astype(severity_order)
        return result.sort_values(["Nivel", "Archivo", "Código"]).reset_index(drop=True)


def _examples(frame: pd.DataFrame, columns: tuple[str, ...], mask: pd.Series) -> tuple[str, ...]:
    """Genera ejemplos compactos de registros problemáticos."""
    available = [column for column in columns if column in frame.columns]
    if not available:
        return ()

    rows = frame.loc[mask, available].head(5).fillna("<vacío>")
    return tuple(
        ", ".join(f"{column}={row[column]}" for column in available)
        for _, row in rows.iterrows()
    )


def _missing_columns(dataset: str, frame: pd.DataFrame) -> list[ValidationIssue]:
    missing = [column for column in REQUIRED_COLUMNS[dataset] if column not in frame.columns]
    if not missing:
        return []

    return [
        ValidationIssue(
            severity="ERROR",
            code="COLUMNAS_FALTANTES",
            dataset=dataset,
            message=f"Faltan columnas obligatorias: {', '.join(missing)}.",
            row_count=len(missing),
            examples=tuple(missing),
        )
    ]


def _validate_required_values(dataset: str, frame: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for column in REQUIRED_COLUMNS[dataset]:
        if column not in frame.columns:
            continue
        missing_mask = frame[column].isna()
        if missing_mask.any():
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="VALORES_VACIOS",
                    dataset=dataset,
                    message=f"La columna '{column}' contiene valores vacíos.",
                    row_count=int(missing_mask.sum()),
                    examples=_examples(frame, UNIQUE_KEYS[dataset], missing_mask),
                )
            )
    return issues


def _coerce_and_validate_numeric(
    dataset: str, frame: pd.DataFrame
) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    cleaned = frame.copy()
    issues: list[ValidationIssue] = []

    for column in NUMERIC_COLUMNS[dataset]:
        if column not in cleaned.columns:
            continue

        raw = cleaned[column]
        converted = pd.to_numeric(raw, errors="coerce")
        invalid_mask = raw.notna() & converted.isna()
        if invalid_mask.any():
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="NUMERO_INVALIDO",
                    dataset=dataset,
                    message=f"La columna '{column}' contiene valores que no son numéricos.",
                    row_count=int(invalid_mask.sum()),
                    examples=_examples(frame, (*UNIQUE_KEYS[dataset], column), invalid_mask),
                )
            )

        negative_mask = converted < 0
        if negative_mask.any():
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="VALOR_NEGATIVO",
                    dataset=dataset,
                    message=f"La columna '{column}' contiene cantidades negativas.",
                    row_count=int(negative_mask.sum()),
                    examples=_examples(frame, (*UNIQUE_KEYS[dataset], column), negative_mask),
                )
            )

        cleaned[column] = converted.astype("Float64")

    return cleaned, issues


def _validate_duplicates(dataset: str, frame: pd.DataFrame) -> list[ValidationIssue]:
    keys = UNIQUE_KEYS[dataset]
    if any(column not in frame.columns for column in keys):
        return []

    duplicate_mask = frame.duplicated(list(keys), keep=False)
    if not duplicate_mask.any():
        return []

    return [
        ValidationIssue(
            severity="ERROR",
            code="REGISTROS_DUPLICADOS",
            dataset=dataset,
            message=f"Hay registros repetidos para la llave: {', '.join(keys)}.",
            row_count=int(duplicate_mask.sum()),
            examples=_examples(frame, keys, duplicate_mask),
        )
    ]


def _validate_catalog(cleaned: DataBundle) -> list[ValidationIssue]:
    frame = cleaned.ingredientes
    issues: list[ValidationIssue] = []

    required = {"es_perecedero", "unidad_base_por_formato", "ingrediente_id"}
    if not required.issubset(frame.columns):
        return issues

    invalid_flag = ~frame["es_perecedero"].str.casefold().isin({"si", "sí", "no"})
    invalid_flag &= frame["es_perecedero"].notna()
    if invalid_flag.any():
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="PERECEDERO_INVALIDO",
                dataset="ingredientes",
                message="'es_perecedero' solo puede contener Sí o No.",
                row_count=int(invalid_flag.sum()),
                examples=_examples(frame, ("ingrediente_id", "es_perecedero"), invalid_flag),
            )
        )

    invalid_format = frame["unidad_base_por_formato"] <= 0
    if invalid_format.any():
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="FORMATO_NO_POSITIVO",
                dataset="ingredientes",
                message="La cantidad base por formato debe ser mayor que cero.",
                row_count=int(invalid_format.sum()),
                examples=_examples(
                    frame,
                    ("ingrediente_id", "unidad_base_por_formato"),
                    invalid_format,
                ),
            )
        )

    return issues


def _validate_unknown_ingredients(cleaned: DataBundle) -> list[ValidationIssue]:
    if "ingrediente_id" not in cleaned.ingredientes.columns:
        return []

    catalog_ids = set(cleaned.ingredientes["ingrediente_id"].dropna())
    issues: list[ValidationIssue] = []

    for dataset, frame in cleaned.as_dict().items():
        if dataset == "ingredientes" or "ingrediente_id" not in frame.columns:
            continue

        unknown_mask = frame["ingrediente_id"].notna() & ~frame["ingrediente_id"].isin(catalog_ids)
        if not unknown_mask.any():
            continue

        severity: Severity = "ADVERTENCIA" if dataset == "orden_compra" else "ERROR"
        issues.append(
            ValidationIssue(
                severity=severity,
                code="INGREDIENTE_DESCONOCIDO",
                dataset=dataset,
                message="Hay ingredientes que no existen en el catálogo maestro.",
                row_count=int(unknown_mask.sum()),
                examples=_examples(
                    frame,
                    ("sucursal", "ingrediente_id"),
                    unknown_mask,
                ),
            )
        )

    return issues


def _validate_history(cleaned: DataBundle) -> list[ValidationIssue]:
    frame = cleaned.consumo_historico
    required = {"sucursal", "ingrediente_id", "semana"}
    if not required.issubset(frame.columns):
        return []

    issues: list[ValidationIssue] = []
    unexpected_mask = frame["semana"].notna() & ~frame["semana"].isin(EXPECTED_WEEKS)
    if unexpected_mask.any():
        issues.append(
            ValidationIssue(
                severity="ADVERTENCIA",
                code="SEMANA_DESCONOCIDA",
                dataset="consumo_historico",
                message="Se encontraron etiquetas de semana distintas de S1 a S6.",
                row_count=int(unexpected_mask.sum()),
                examples=_examples(
                    frame,
                    ("sucursal", "ingrediente_id", "semana"),
                    unexpected_mask,
                ),
            )
        )

    counts = (
        frame.dropna(subset=["sucursal", "ingrediente_id", "semana"])
        .groupby(["sucursal", "ingrediente_id"], dropna=False)["semana"]
        .nunique()
    )
    incomplete = counts[counts != 6]
    if not incomplete.empty:
        examples = tuple(
            f"sucursal={branch}, ingrediente_id={ingredient}, semanas={count}"
            for (branch, ingredient), count in incomplete.head(5).items()
        )
        issues.append(
            ValidationIssue(
                severity="ADVERTENCIA",
                code="HISTORICO_INCOMPLETO",
                dataset="consumo_historico",
                message="Algunas combinaciones no tienen exactamente seis semanas de histórico.",
                row_count=len(incomplete),
                examples=examples,
            )
        )

    return issues


def _validate_missing_inventory(cleaned: DataBundle) -> list[ValidationIssue]:
    history = cleaned.consumo_historico
    inventory = cleaned.inventario_actual
    keys = ["sucursal", "ingrediente_id"]
    if not set(keys).issubset(history.columns) or not set(keys).issubset(inventory.columns):
        return []

    expected = history[keys].dropna().drop_duplicates()
    available = inventory[keys].dropna().drop_duplicates().assign(_inventory_present=True)
    merged = expected.merge(available, on=keys, how="left")
    missing_mask = merged["_inventory_present"].isna()
    if not missing_mask.any():
        return []

    return [
        ValidationIssue(
            severity="ERROR",
            code="INVENTARIO_FALTANTE",
            dataset="inventario_actual",
            message="Falta inventario para combinaciones que sí tienen consumo histórico.",
            row_count=int(missing_mask.sum()),
            examples=_examples(merged, tuple(keys), missing_mask),
        )
    ]


def _validate_omitted_order_lines(cleaned: DataBundle) -> list[ValidationIssue]:
    history = cleaned.consumo_historico
    orders = cleaned.orden_compra
    catalog = cleaned.ingredientes
    keys = ["sucursal", "ingrediente_id"]

    if (
        not set(keys).issubset(history.columns)
        or not set(keys).issubset(orders.columns)
        or "ingrediente_id" not in catalog.columns
    ):
        return []

    catalog_ids = set(catalog["ingrediente_id"].dropna())
    expected = history.loc[history["ingrediente_id"].isin(catalog_ids), keys].drop_duplicates()
    available = (
        orders.loc[orders["ingrediente_id"].isin(catalog_ids), keys]
        .drop_duplicates()
        .assign(_order_present=True)
    )
    merged = expected.merge(available, on=keys, how="left")
    missing_mask = merged["_order_present"].isna()
    if not missing_mask.any():
        return []

    return [
        ValidationIssue(
            severity="ADVERTENCIA",
            code="LINEA_ORDEN_OMITIDA",
            dataset="orden_compra",
            message=(
                "Hay combinaciones con histórico que no aparecen en la orden. "
                "La Fase 3 determinará si realmente requieren compra."
            ),
            row_count=int(missing_mask.sum()),
            examples=_examples(merged, tuple(keys), missing_mask),
        )
    ]


def validate_data(data: DataBundle) -> ValidationReport:
    """Valida los cuatro datasets y devuelve copias con números convertidos."""
    issues: list[ValidationIssue] = []
    cleaned_frames: dict[str, pd.DataFrame] = {}

    for dataset, frame in data.as_dict().items():
        issues.extend(_missing_columns(dataset, frame))
        issues.extend(_validate_required_values(dataset, frame))
        issues.extend(_validate_duplicates(dataset, frame))
        cleaned_frame, numeric_issues = _coerce_and_validate_numeric(dataset, frame)
        cleaned_frames[dataset] = cleaned_frame
        issues.extend(numeric_issues)

    cleaned = DataBundle(**cleaned_frames)
    issues.extend(_validate_catalog(cleaned))
    issues.extend(_validate_unknown_ingredients(cleaned))
    issues.extend(_validate_history(cleaned))
    issues.extend(_validate_missing_inventory(cleaned))
    issues.extend(_validate_omitted_order_lines(cleaned))

    return ValidationReport(cleaned_data=cleaned, issues=tuple(issues))
