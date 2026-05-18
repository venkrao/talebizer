"""Serialize pandas frames for JSON responses."""
from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd


def dataframe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))
