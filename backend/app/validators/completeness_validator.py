from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from backend.app.validators.base import BaseValidator


class CompletenessValidator(BaseValidator):
    ANALYSIS_CATEGORIES = {
        "imagery",
        "cep",
        "dependent",
        "attribute",
        "attributes",
        "equity",
        "strategic",
    }

    MISSING_TOKENS = {
        "",
        "na",
        "n/a",
        "nan",
        "null",
        "none",
        "system missing",
        "sysmiss",
        ".",
    }

    def __init__(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
        profile_config: Dict[str, Any],
        respondent_id_col: Optional[str] = None,
        brand_col: Optional[str] = None,
        country_col: Optional[str] = None,
    ) -> None:
        super().__init__(df, metadata, profile_config)
        self.respondent_id_col = respondent_id_col
        self.brand_col = brand_col
        self.country_col = country_col

    @staticmethod
    def _is_missing(value: Any) -> bool:
        if pd.isna(value):
            return True
        if isinstance(value, str):
            return value.strip().lower() in CompletenessValidator.MISSING_TOKENS
        return False

    @staticmethod
    def _detect_country_col(df: pd.DataFrame) -> Optional[str]:
        candidates = ["country", "country_code", "market", "cntry", "nation"]
        for col in df.columns:
            lower_col = col.lower()
            if any(token in lower_col for token in candidates):
                return col
        return None

    def _get_analysis_variables(self) -> List[str]:
        variables = self.config.get("variables", []) if self.config else []
        analysis_vars: List[str] = []

        for var in variables:
            var_name = var.get("name")
            if not var_name or var_name not in self.df.columns:
                continue

            explicit_analysis = bool(var.get("is_analysis_variable", False))
            category = str(var.get("category", "")).strip().lower()
            inferred_analysis = category in self.ANALYSIS_CATEGORIES

            if explicit_analysis or inferred_analysis:
                analysis_vars.append(var_name)

        return sorted(set(analysis_vars))

    @staticmethod
    def _band_label(completed_pct: float) -> str:
        if completed_pct >= 100.0:
            return "100% Completed"
        if completed_pct >= 75.0:
            return "75% - 99% Completed"
        if completed_pct >= 50.0:
            return "50% - 74% Completed"
        if completed_pct >= 25.0:
            return "25% - 49% Completed"
        return "0% - 24% Completed"

    @staticmethod
    def _severity_from_pct(fully_missing_pct: float) -> str:
        if fully_missing_pct < 1.0:
            return "INFO"
        if fully_missing_pct <= 3.0:
            return "WARNING"
        return "FAIL"

    @staticmethod
    def _quality_penalty(fully_missing_pct: float) -> int:
        if fully_missing_pct > 5.0:
            return 5
        if fully_missing_pct > 3.0:
            return 3
        if fully_missing_pct >= 1.0:
            return 1
        return 0

    def validate(self) -> Dict[str, Any]:
        analysis_variables = self._get_analysis_variables()
        total_respondents = len(self.df)
        total_analysis_variables = len(analysis_variables)

        resolved_country_col = self.country_col if self.country_col in self.df.columns else self._detect_country_col(self.df)
        resolved_brand_col = self.brand_col if self.brand_col in self.df.columns else None
        resolved_id_col = self.respondent_id_col if self.respondent_id_col in self.df.columns else None

        if total_respondents == 0 or total_analysis_variables == 0:
            return {
                "status": "INFO",
                "total_respondents": total_respondents,
                "total_analysis_variables": total_analysis_variables,
                "fully_missing_respondents_count": 0,
                "fully_missing_respondents_pct": 0.0,
                "respondent_id_col": resolved_id_col,
                "country_col": resolved_country_col,
                "brand_col": resolved_brand_col,
                "analysis_variables": analysis_variables,
                "coverage_distribution": [
                    {"band": "100% Completed", "respondents": 0},
                    {"band": "75% - 99% Completed", "respondents": 0},
                    {"band": "50% - 74% Completed", "respondents": 0},
                    {"band": "25% - 49% Completed", "respondents": 0},
                    {"band": "0% - 24% Completed", "respondents": 0},
                ],
                "fully_missing_respondents": [],
                "quality_score_penalty": 0,
                "quality_score_note": "No analysis variables available for completeness validation.",
            }

        analysis_df = self.df[analysis_variables]
        missing_mask = analysis_df.map(self._is_missing)
        missing_counts = missing_mask.sum(axis=1)
        fully_missing_mask = missing_counts == total_analysis_variables
        fully_missing_count = int(fully_missing_mask.sum())
        fully_missing_pct = round((fully_missing_count / total_respondents) * 100, 2)

        completed_pct = ((total_analysis_variables - missing_counts) / total_analysis_variables) * 100
        band_order = [
            "100% Completed",
            "75% - 99% Completed",
            "50% - 74% Completed",
            "25% - 49% Completed",
            "0% - 24% Completed",
        ]
        band_counts = {band: 0 for band in band_order}
        for value in completed_pct:
            band_counts[self._band_label(float(value))] += 1

        fully_missing_details: List[Dict[str, Any]] = []
        for idx in self.df[fully_missing_mask].index:
            respondent_id = self.df.at[idx, resolved_id_col] if resolved_id_col else int(idx) + 1
            country_value = self.df.at[idx, resolved_country_col] if resolved_country_col else None
            brand_value = self.df.at[idx, resolved_brand_col] if resolved_brand_col else None

            fully_missing_details.append(
                {
                    "respondent_id": respondent_id,
                    "country": None if pd.isna(country_value) else str(country_value),
                    "brand": None if pd.isna(brand_value) else str(brand_value),
                    "missing_analysis_variables": int(missing_counts.loc[idx]),
                    "missing_pct": 100.0,
                }
            )

        severity = self._severity_from_pct(fully_missing_pct)
        quality_penalty = self._quality_penalty(fully_missing_pct)

        return {
            "status": severity,
            "total_respondents": total_respondents,
            "total_analysis_variables": total_analysis_variables,
            "fully_missing_respondents_count": fully_missing_count,
            "fully_missing_respondents_pct": fully_missing_pct,
            "respondent_id_col": resolved_id_col,
            "country_col": resolved_country_col,
            "brand_col": resolved_brand_col,
            "analysis_variables": analysis_variables,
            "coverage_distribution": [{"band": band, "respondents": int(band_counts[band])} for band in band_order],
            "fully_missing_respondents": fully_missing_details,
            "quality_score_penalty": quality_penalty,
            "quality_score_note": f"{fully_missing_pct}% respondents are fully missing across analysis variables.",
        }
