"""
endpoints_downloader.py - Robust orchestrator for downloading, parsing,
and storing data from all 138 nba_api endpoints into SQLite and JSON archive.
"""

import os
import json
import time
import logging
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from .client import configure_nba_api_client, call_with_retry
from .database import NBADatabase
from .endpoints_catalog import get_all_endpoints_catalog, CANONICAL_DEFAULTS

logger = logging.getLogger(__name__)

DATA_ARCHIVE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "endpoints"))


class NBAEndpointDownloader:
    """Orchestrates downloading and storing all endpoints listed in nba_api."""

    def __init__(
        self,
        db: Optional[NBADatabase] = None,
        impersonate: str = "chrome120",
        archive_dir: Optional[str] = None,
    ):
        self.db = db or NBADatabase()
        self.db.init_database()
        configure_nba_api_client(impersonate=impersonate)
        self.catalog = get_all_endpoints_catalog()
        self.db.register_endpoints_catalog(self.catalog)
        self.archive_dir = archive_dir or DATA_ARCHIVE_DIR
        os.makedirs(self.archive_dir, exist_ok=True)

    def _prepare_kwargs(self, meta: Dict[str, Any], custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepares valid kwargs for the endpoint's constructor."""
        kwargs = dict(meta.get("default_test_params", {}))
        if custom_params:
            kwargs.update(custom_params)

        all_params = meta.get("all_params", {})
        # Filter to only params accepted by the class
        valid_kwargs = {}
        for k, v in kwargs.items():
            if k in all_params:
                valid_kwargs[k] = v

        # Add timeout if accepted
        valid_kwargs["timeout"] = 35
        return valid_kwargs

    def download_endpoint(
        self,
        endpoint_name: str,
        custom_params: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Downloads a single endpoint by name, stores result sets into SQLite tables,
        archives raw JSON, and updates catalog record.
        """
        if endpoint_name not in self.catalog:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")

        meta = self.catalog[endpoint_name]
        cls = meta["class_ref"]
        is_live = meta.get("is_live", False)

        # Check existing status if not forcing
        if not force:
            existing = self.db.get_endpoint_detail(endpoint_name)
            if existing and existing.get("status") in ("SUCCESS", "EMPTY"):
                logger.info("Endpoint %s already downloaded (%s). Skipping.", endpoint_name, existing["status"])
                return {
                    "endpoint_name": endpoint_name,
                    "status": "SKIPPED",
                    "total_rows": existing.get("total_rows", 0),
                    "result_sets_count": existing.get("result_sets_count", 0),
                    "table_names": existing.get("table_names", []),
                }

        kwargs = self._prepare_kwargs(meta, custom_params)
        logger.info("Downloading %s with params: %s", endpoint_name, kwargs)

        table_names: List[str] = []
        total_rows = 0
        status = "PENDING"
        error_msg = None
        dfs_to_save: List[tuple] = []  # (dataset_name, df)

        try:
            if is_live:
                # Live endpoints handling
                inst = call_with_retry(lambda: cls(**kwargs))
                raw_dict = inst.get_dict()
                raw_json = inst.get_json() if hasattr(inst, "get_json") else json.dumps(raw_dict)

                # Convert live dict into tabular DataFrames
                if endpoint_name == "LiveScoreBoard":
                    games = raw_dict.get("scoreboard", {}).get("games", [])
                    if games:
                        df_games = pd.json_normalize(games)
                        dfs_to_save.append(("ScoreboardGames", df_games))
                elif endpoint_name == "LiveBoxScore":
                    game_info = raw_dict.get("game", {})
                    if game_info:
                        home_players = game_info.get("homeTeam", {}).get("players", [])
                        away_players = game_info.get("awayTeam", {}).get("players", [])
                        all_players = home_players + away_players
                        if all_players:
                            dfs_to_save.append(("BoxScorePlayers", pd.json_normalize(all_players)))
                elif endpoint_name == "LivePlayByPlay":
                    actions = raw_dict.get("game", {}).get("actions", [])
                    if actions:
                        dfs_to_save.append(("PlayByPlayActions", pd.json_normalize(actions)))

            else:
                # Stats endpoints handling
                inst = call_with_retry(lambda: cls(**kwargs))
                dfs = inst.get_data_frames()
                raw_dict = inst.get_dict()
                raw_json = inst.get_json()

                # Extract dataset names
                ds_names = []
                if "resultSets" in raw_dict:
                    rs_obj = raw_dict["resultSets"]
                    if isinstance(rs_obj, list):
                        ds_names = [rs.get("name", f"Dataset{i}") if isinstance(rs, dict) else f"Dataset{i}" for i, rs in enumerate(rs_obj)]
                    elif isinstance(rs_obj, dict):
                        ds_names = [rs_obj.get("name", "Default")]
                elif "resultSet" in raw_dict:
                    rs_obj = raw_dict["resultSet"]
                    if isinstance(rs_obj, dict):
                        ds_names = [rs_obj.get("name", "Default")]
                    elif isinstance(rs_obj, list):
                        ds_names = [rs.get("name", f"Dataset{i}") if isinstance(rs, dict) else f"Dataset{i}" for i, rs in enumerate(rs_obj)]

                # Match names to dataframes
                for i, df in enumerate(dfs):
                    name = ds_names[i] if i < len(ds_names) else f"ResultSet_{i}"
                    dfs_to_save.append((name, df))

            # Save raw JSON archive
            json_file = os.path.join(self.archive_dir, f"{endpoint_name}.json")
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(raw_json)

            # Persist DataFrames into SQLite tables
            for ds_name, df in dfs_to_save:
                if df is not None and not df.empty:
                    tbl = self.db.save_endpoint_dataset(endpoint_name, ds_name, df)
                    table_names.append(tbl)
                    total_rows += len(df)
                else:
                    # Still register empty table schema if columns exist
                    if df is not None and len(df.columns) > 0:
                        tbl = self.db.save_endpoint_dataset(endpoint_name, ds_name, df)
                        table_names.append(tbl)

            if total_rows > 0:
                status = "SUCCESS"
            else:
                status = "EMPTY"

        except Exception as exc:
            err_str = str(exc)
            logger.warning("Failed to download endpoint %s: %s", endpoint_name, err_str)
            if isinstance(exc, KeyError) or any(term in err_str.lower() for term in ["deprecated", "not found", "404", "invalid", "unauthorized", "expecting value", "jsondecodeerror"]):
                status = "DEPRECATED"
            else:
                status = "ERROR"
            error_msg = err_str

        # Update catalog record
        self.db.update_endpoint_status(
            endpoint_name=endpoint_name,
            status=status,
            result_sets_count=len(table_names),
            total_rows=total_rows,
            table_names=table_names,
            error_message=error_msg,
        )

        return {
            "endpoint_name": endpoint_name,
            "status": status,
            "total_rows": total_rows,
            "result_sets_count": len(table_names),
            "table_names": table_names,
            "error_message": error_msg,
        }

    def download_all_endpoints(
        self,
        categories: Optional[List[str]] = None,
        force: bool = False,
        delay: float = 0.8,
        on_progress: Optional[Callable[[int, int, str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Sequentially downloads all matching endpoints in the catalog,
        adhering to rate-limiting delays.
        """
        endpoints_to_run = []
        for name, meta in self.catalog.items():
            if categories and meta["category"] not in categories:
                continue
            endpoints_to_run.append(name)

        total = len(endpoints_to_run)
        logger.info("Starting download of %d endpoints...", total)

        results: Dict[str, Any] = {
            "total": total,
            "succeeded": 0,
            "empty": 0,
            "deprecated": 0,
            "error": 0,
            "skipped": 0,
            "endpoints": {},
        }

        for idx, ep_name in enumerate(endpoints_to_run, 1):
            try:
                res = self.download_endpoint(ep_name, force=force)
                st = res["status"].lower()
                if st == "success":
                    results["succeeded"] += 1
                elif st == "empty":
                    results["empty"] += 1
                elif st == "deprecated":
                    results["deprecated"] += 1
                elif st == "skipped":
                    results["skipped"] += 1
                else:
                    results["error"] += 1

                results["endpoints"][ep_name] = res

                if on_progress:
                    on_progress(idx, total, ep_name, res)

                # Polite delay between requests to prevent rate limiting
                if delay > 0 and res["status"] != "SKIPPED":
                    time.sleep(delay)

            except Exception as e:
                logger.error("Unexpected failure downloading %s: %s", ep_name, e)
                results["error"] += 1
                results["endpoints"][ep_name] = {"endpoint_name": ep_name, "status": "ERROR", "error_message": str(e)}
                if on_progress:
                    on_progress(idx, total, ep_name, {"status": "ERROR", "error_message": str(e)})

        return results
