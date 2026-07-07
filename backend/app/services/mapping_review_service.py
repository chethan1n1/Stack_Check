from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional


class MappingReviewService:
    @staticmethod
    def _normalize_name(value: str) -> str:
        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "", value)
        return value

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        tokens = re.findall(r"[A-Za-z0-9]+", str(value or "").lower())
        return {t for t in tokens if t}

    @staticmethod
    def _confidence_label(score: float) -> str:
        if score >= 0.95:
            return "HIGH"
        if score >= 0.78:
            return "MEDIUM"
        if score >= 0.62:
            return "LOW"
        return "NONE"

    @staticmethod
    def _score(dp_name: str, dataset_col: str) -> Dict[str, Any]:
        dp_norm = MappingReviewService._normalize_name(dp_name)
        col_norm = MappingReviewService._normalize_name(dataset_col)
        if not dp_norm or not col_norm:
            return {"score": 0.0, "reason": "no_match"}

        if dp_name == dataset_col:
            return {"score": 1.0, "reason": "exact_name"}

        if str(dp_name).lower().strip() == str(dataset_col).lower().strip():
            return {"score": 0.985, "reason": "case_insensitive_exact"}

        if dp_norm == col_norm:
            return {"score": 0.955, "reason": "normalized_exact"}

        ratio = SequenceMatcher(None, dp_norm, col_norm).ratio()
        dp_tokens = MappingReviewService._tokenize(dp_name)
        col_tokens = MappingReviewService._tokenize(dataset_col)
        overlap = 0.0
        if dp_tokens and col_tokens:
            overlap = len(dp_tokens & col_tokens) / len(dp_tokens | col_tokens)

        blended = round(max(ratio * 0.7 + overlap * 0.3, overlap), 4)
        if overlap >= 0.7:
            reason = "token_match"
        elif ratio >= 0.74:
            reason = "fuzzy_char_match"
        else:
            reason = "weak_match"
        return {"score": blended, "reason": reason}

    @staticmethod
    def _to_col_name(col: Any) -> str:
        if isinstance(col, dict):
            return str(col.get("name", "")).strip()
        return str(col or "").strip()

    @staticmethod
    def _to_col_type(col: Any) -> str:
        if isinstance(col, dict):
            return str(col.get("type_hint", "Unknown") or "Unknown")
        return "Unknown"

    @staticmethod
    def _status_from_selection(selected_col: Optional[str], waived: bool) -> str:
        if selected_col:
            return "MATCHED"
        if waived:
            return "WAIVED"
        return "UNMATCHED"

    @staticmethod
    def build_mapping_preview(profile_config: Dict[str, Any], dataset_columns: List[Any]) -> Dict[str, Any]:
        variables = profile_config.get("variables", []) if profile_config else []
        dataset_columns = dataset_columns or []
        dataset_names = [MappingReviewService._to_col_name(c) for c in dataset_columns if MappingReviewService._to_col_name(c)]
        dataset_type_map = {MappingReviewService._to_col_name(c): MappingReviewService._to_col_type(c) for c in dataset_columns}
        dataset_set = set(dataset_names)
        items: List[Dict[str, Any]] = []
        used_columns: set[str] = set()

        for var in variables:
            dp_var = var.get("name", "")
            if not dp_var:
                continue

            normalized_label = var.get("normalized_label") or MappingReviewService._normalize_name(dp_var)

            best_col: Optional[str] = None
            best_score = 0.0
            best_reason = "no_match"
            ranked_candidates: List[Dict[str, Any]] = []
            for col in dataset_names:
                candidate = MappingReviewService._score(dp_var, col)
                s = candidate["score"]
                if s > best_score:
                    best_col = col
                    best_score = s
                    best_reason = candidate["reason"]
                ranked_candidates.append(
                    {
                        "column": col,
                        "score": s,
                        "reason": candidate["reason"],
                        "type_hint": dataset_type_map.get(col, "Unknown"),
                    }
                )

            # Keep exact name matches even with low heuristic score.
            if dp_var in dataset_set:
                best_col = dp_var
                best_score = 1.0
                best_reason = "exact_name"

            confidence = MappingReviewService._confidence_label(best_score)
            if best_col and confidence != "NONE":
                used_columns.add(best_col)

            ranked_candidates.sort(key=lambda x: x["score"], reverse=True)
            top_candidates = [c for c in ranked_candidates[:5] if c["score"] >= 0.5]

            items.append(
                {
                    "dp_variable": dp_var,
                    "normalized_label": normalized_label,
                    "required": bool(var.get("required", True)),
                    "category": var.get("category", "Core"),
                    "suggested_column": best_col if confidence != "NONE" else None,
                    "auto_match": best_col if confidence != "NONE" else None,
                    "auto_reason": best_reason if confidence != "NONE" else "no_match",
                    "dataset_type_hint": dataset_type_map.get(best_col or "", "Unknown"),
                    "confidence_score": best_score,
                    "confidence": confidence,
                    "confidence_band": confidence,
                    "status": "MATCHED" if confidence != "NONE" else "UNMATCHED",
                    "waived": False,
                    "waive_reason": None,
                    "candidates": top_candidates,
                }
            )

        unmatched_required = [i for i in items if i["required"] and i["status"] == "UNMATCHED"]
        unmatched_optional = [i for i in items if (not i["required"]) and i["status"] == "UNMATCHED"]
        unused_columns = [col for col in dataset_names if col not in used_columns]
        unused_dataset_candidates = [
            {"name": col, "type_hint": dataset_type_map.get(col, "Unknown")}
            for col in unused_columns
        ]

        return {
            "items": items,
            "summary": {
                "dp_variables": len(items),
                "dataset_columns": len(dataset_names),
                "matched": len([i for i in items if i["status"] == "MATCHED"]),
                "unmatched_required": len(unmatched_required),
                "unmatched_optional": len(unmatched_optional),
                "unused_dataset_columns": len(unused_columns),
            },
            "unmatched_required": unmatched_required,
            "unmatched_optional": unmatched_optional,
            "unused_dataset_columns": unused_columns,
            "unused_dataset_candidates": unused_dataset_candidates,
        }

    @staticmethod
    def apply_confirmed_mapping(
        profile_config: Dict[str, Any],
        confirmed_mapping: Dict[str, Optional[str]],
        waivers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not profile_config:
            return {"variables": []}

        waivers = waivers or {}
        variables = profile_config.get("variables", [])
        mapped_variables = []
        unresolved_required: List[str] = []
        unresolved_optional: List[str] = []
        for var in variables:
            var_name = var.get("name")
            mapped_name = confirmed_mapping.get(var_name)
            if mapped_name:
                new_var = dict(var)
                new_var["source_dp_name"] = var_name
                new_var["name"] = mapped_name
                mapped_variables.append(new_var)
            elif waivers.get(var_name):
                new_var = dict(var)
                new_var["source_dp_name"] = var_name
                new_var["waived"] = True
                new_var["waive_reason"] = waivers.get(var_name)
                mapped_variables.append(new_var)
            else:
                if bool(var.get("required", True)):
                    unresolved_required.append(var_name)
                else:
                    unresolved_optional.append(var_name)
                mapped_variables.append(dict(var))

        output = dict(profile_config)
        output["variables"] = mapped_variables
        output["confirmed_mapping"] = confirmed_mapping
        output["mapping_waivers"] = waivers
        output["mapping_diagnostics"] = {
            "unresolved_required": unresolved_required,
            "unresolved_optional": unresolved_optional,
            "total_unresolved": len(unresolved_required) + len(unresolved_optional),
        }
        return output

    @staticmethod
    def build_decision_rows(
        preview: Dict[str, Any],
        overrides: Dict[str, Optional[str]],
        waivers: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        waivers = waivers or {}
        items = preview.get("items", []) if preview else []
        rows: List[Dict[str, Any]] = []
        for item in items:
            dp_var = item.get("dp_variable")
            auto_match = item.get("suggested_column")
            selected = overrides.get(dp_var)
            if selected is None:
                selected = auto_match
            waive_reason = waivers.get(dp_var)
            waived = bool(waive_reason)
            status = MappingReviewService._status_from_selection(selected, waived)
            rows.append(
                {
                    "dp_variable": dp_var,
                    "required": bool(item.get("required", True)),
                    "auto_suggestion": auto_match,
                    "selected_column": selected,
                    "confidence_band": item.get("confidence_band") or item.get("confidence") or "NONE",
                    "confidence_score": float(item.get("confidence_score", 0.0) or 0.0),
                    "match_reason": item.get("auto_reason") or "no_match",
                    "user_override": bool(selected and selected != auto_match),
                    "waived": waived,
                    "waive_reason": waive_reason,
                    "status": status,
                }
            )
        return rows

    @staticmethod
    def build_summary(decision_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(decision_rows)
        auto = len([r for r in decision_rows if r.get("selected_column") and not r.get("user_override")])
        manual = len([r for r in decision_rows if r.get("selected_column") and r.get("user_override")])
        waived = len([r for r in decision_rows if r.get("waived")])
        unresolved = len([r for r in decision_rows if not r.get("selected_column") and not r.get("waived")])
        unresolved_required = len(
            [r for r in decision_rows if r.get("required") and not r.get("selected_column") and not r.get("waived")]
        )
        return {
            "total_dp_variables": total,
            "auto_matched": auto,
            "manually_mapped": manual,
            "waived": waived,
            "unresolved": unresolved,
            "unresolved_required": unresolved_required,
        }
