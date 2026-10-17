"""
clustering.py - Unsupervised Position & Role Clustering with 3D t-SNE Dimensionality Reduction.

Extracts multi-dimensional player profiling features, scans for optimal cluster count (k)
via Silhouette analysis and Inertia Elbow method, fits K-Means, computes 3D t-SNE coordinates,
profiles cluster archetypes with automated naming, and generates interactive Plotly 3D visualizations.
"""

import os
import logging
import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import threadpoolctl
    _orig_make = threadpoolctl._ThreadpoolInfo._make_module_from_path

    def _safe_make(self, filepath):
        try:
            return _orig_make(self, filepath)
        except Exception:
            return None

    threadpoolctl._ThreadpoolInfo._make_module_from_path = _safe_make
except Exception:
    pass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, silhouette_samples
import plotly.express as px
import plotly.graph_objects as go

from .database import NBADatabase
from .box_lebron import _to_decimal, BoxLEBRONModel

logger = logging.getLogger(__name__)

# Tactical Feature Columns used for Unsupervised Clustering
CLUSTERING_FEATURES = [
    "usg_pct",
    "ts_pct",
    "pts_per_36",
    "fga_per_36",
    "fg3a_rate",
    "ft_rate",
    "ast_pct",
    "tm_tov_pct",
    "ast_to_ratio",
    "oreb_pct",
    "dreb_pct",
    "reb_pct",
    "stl_per_36",
    "blk_per_36",
    "pf_per_36",
    "box_lebron",
    "o_lebron",
    "d_lebron",
]


class PositionClusteringModel:
    """
    Unsupervised learning engine that clusters NBA players into modern role-based
    positions and projects high-dimensional performance vectors into 3D t-SNE space.
    """

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()
        self.lebron_model = BoxLEBRONModel(db=self.db)
        self.df: pd.DataFrame = pd.DataFrame()
        self.X_scaled: Optional[np.ndarray] = None
        self.scaler = StandardScaler()
        self.kmeans_model: Optional[KMeans] = None
        self.k_optimal: int = 7
        self.cluster_profiles: Dict[int, Dict[str, Any]] = {}
        self.tsne_coords: Optional[np.ndarray] = None

    def fetch_player_data(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
        min_minutes: float = 300.0,
    ) -> pd.DataFrame:
        """Pulls comprehensive box, advanced, and LEBRON stats for players in a season."""
        # Ensure Box LEBRON ratings exist for the season
        lebron_df = self.db.query_df(
            "SELECT * FROM box_lebron_ratings WHERE season = ? AND season_type = ?",
            (season, season_type),
        )
        if lebron_df.empty:
            logger.info("Box LEBRON ratings not found for %s. Computing now...", season)
            self.lebron_model.save_season_box_lebron(season=season, season_type=season_type)

        query = """
        SELECT 
            pss.player_id,
            p.full_name as player_name,
            pss.season,
            pss.season_type,
            pss.team_abbreviation,
            pss.age,
            pss.gp,
            pss.min as min_pg,
            pss.fga,
            pss.fgm,
            pss.fg_pct,
            pss.fg3a,
            pss.fg3m,
            pss.fg3_pct,
            pss.fta,
            pss.ftm,
            pss.ft_pct,
            pss.oreb,
            pss.dreb,
            pss.reb,
            pss.ast,
            pss.stl,
            pss.blk,
            pss.tov,
            pss.pf,
            pss.pts,
            pas.off_rating,
            pas.def_rating,
            pas.net_rating,
            pas.ast_pct,
            pas.ast_to,
            pas.ast_ratio,
            pas.oreb_pct,
            pas.dreb_pct,
            pas.reb_pct,
            pas.tm_tov_pct,
            pas.efg_pct,
            pas.ts_pct,
            pas.usg_pct,
            pas.pace,
            pas.pie,
            pas.poss,
            blr.o_lebron,
            blr.d_lebron,
            blr.box_lebron,
            blr.wins_added,
            blr.offensive_archetype,
            blr.defensive_archetype
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        LEFT JOIN player_advanced_stats pas 
            ON pss.player_id = pas.player_id 
            AND pss.season = pas.season 
            AND pss.season_type = pas.season_type
        LEFT JOIN box_lebron_ratings blr
            ON pss.player_id = blr.player_id
            AND pss.season = blr.season
            AND pss.season_type = blr.season_type
        WHERE pss.season = ? AND pss.season_type = ?
        """
        df = self.db.query_df(query, (season, season_type))
        if df.empty:
            raise ValueError(f"No player stats found in database for season {season} ({season_type})")

        # Derived metrics
        df["gp"] = df["gp"].fillna(1).apply(lambda v: max(float(v), 1.0))
        df["min_pg"] = df["min_pg"].fillna(0.0).apply(lambda v: max(float(v), 1.0))
        df["total_minutes"] = np.round(df["min_pg"] * df["gp"], 1)

        # Filter minimum minutes
        df = df[df["total_minutes"] >= min_minutes].copy().reset_index(drop=True)

        # Normalize percentages to decimal
        df["usg_pct"] = df["usg_pct"].apply(lambda v: _to_decimal(v, 0.18))
        df["ts_pct"] = df["ts_pct"].apply(lambda v: _to_decimal(v, 0.55))
        df["ast_pct"] = df["ast_pct"].apply(lambda v: _to_decimal(v, 0.12))
        df["tm_tov_pct"] = df["tm_tov_pct"].apply(lambda v: _to_decimal(v, 0.10))
        df["oreb_pct"] = df["oreb_pct"].apply(lambda v: _to_decimal(v, 0.04))
        df["dreb_pct"] = df["dreb_pct"].apply(lambda v: _to_decimal(v, 0.14))
        df["reb_pct"] = df["reb_pct"].apply(lambda v: _to_decimal(v, 0.09))
        df["fg_pct"] = df["fg_pct"].apply(lambda v: _to_decimal(v, 0.45))
        df["fg3_pct"] = df["fg3_pct"].apply(lambda v: _to_decimal(v, 0.35))

        # Per 36 volume metrics
        df["pts_per_36"] = np.round((df["pts"].fillna(0.0) / df["min_pg"]) * 36.0, 1)
        df["fga_per_36"] = np.round((df["fga"].fillna(0.0) / df["min_pg"]) * 36.0, 1)
        df["stl_per_36"] = np.round((df["stl"].fillna(0.0) / df["min_pg"]) * 36.0, 2)
        df["blk_per_36"] = np.round((df["blk"].fillna(0.0) / df["min_pg"]) * 36.0, 2)
        df["pf_per_36"] = np.round((df["pf"].fillna(0.0) / df["min_pg"]) * 36.0, 1)

        # Shot distribution ratios
        fga = df["fga"].fillna(1.0).apply(lambda v: max(float(v), 0.1))
        df["fg3a_rate"] = np.round(df["fg3a"].fillna(0.0) / fga, 3)
        df["ft_rate"] = np.round(df["fta"].fillna(0.0) / fga, 3)

        # Assist to turnover ratio
        tov = df["tov"].fillna(0.1).apply(lambda v: max(float(v), 0.1))
        df["ast_to_ratio"] = np.round(df["ast"].fillna(0.0) / tov, 2)

        # Fill LEBRON metrics if null
        df["o_lebron"] = df["o_lebron"].fillna(0.0)
        df["d_lebron"] = df["d_lebron"].fillna(0.0)
        df["box_lebron"] = df["box_lebron"].fillna(0.0)

        self.df = df
        return df

    def find_optimal_k(
        self,
        k_range: Tuple[int, int] = (3, 12),
        season: str = "2023-24",
        season_type: str = "Regular Season",
        min_minutes: float = 300.0,
    ) -> Dict[str, Any]:
        """
        Scans k across k_range and computes Inertia (Elbow) and Silhouette Scores
        to find the optimal number of clusters.
        """
        if self.df.empty or "season" not in self.df.columns or self.df.iloc[0]["season"] != season:
            self.fetch_player_data(season=season, season_type=season_type, min_minutes=min_minutes)

        X = self.df[CLUSTERING_FEATURES].values
        self.X_scaled = self.scaler.fit_transform(X)

        inertias: List[float] = []
        silhouette_scores_list: List[float] = []
        k_values = list(range(k_range[0], k_range[1] + 1))

        best_k = k_range[0]
        max_sil = -1.0

        for k in k_values:
            km = KMeans(n_clusters=k, random_state=42, n_init=20)
            labels = km.fit_predict(self.X_scaled)
            inertias.append(float(np.round(km.inertia_, 2)))

            sil = float(silhouette_score(self.X_scaled, labels))
            silhouette_scores_list.append(float(np.round(sil, 4)))

            if sil > max_sil:
                max_sil = sil
                best_k = k

        self.k_optimal = best_k
        return {
            "season": season,
            "sample_size": len(self.df),
            "k_values": k_values,
            "inertias": inertias,
            "silhouette_scores": silhouette_scores_list,
            "optimal_k": best_k,
            "max_silhouette_score": round(max_sil, 4),
        }

    def fit_clusters(
        self,
        k: Optional[int] = None,
        season: str = "2023-24",
        season_type: str = "Regular Season",
        min_minutes: float = 300.0,
    ) -> pd.DataFrame:
        """
        Fits K-Means on player feature space and assigns cluster IDs.
        """
        if self.df.empty:
            self.fetch_player_data(season=season, season_type=season_type, min_minutes=min_minutes)

        X = self.df[CLUSTERING_FEATURES].values
        self.X_scaled = self.scaler.fit_transform(X)

        n_clusters = k or self.k_optimal
        self.k_optimal = n_clusters

        self.kmeans_model = KMeans(n_clusters=n_clusters, random_state=42, n_init=25)
        self.df["cluster_id"] = self.kmeans_model.fit_predict(self.X_scaled)

        # Profile and assign human-readable archetype names
        self.profile_clusters()
        self.df["cluster_name"] = self.df["cluster_id"].apply(
            lambda cid: self.cluster_profiles.get(cid, {}).get("name", f"Cluster {cid}")
        )
        return self.df

    def compute_3d_tsne(
        self,
        perplexity: float = 30.0,
        learning_rate: float = 200.0,
        n_iter: int = 1500,
    ) -> pd.DataFrame:
        """
        Optimizes 3D t-SNE projection from high-dimensional feature space.
        Uses PCA initialization for stable global geometry.
        """
        if self.X_scaled is None or self.df.empty:
            raise ValueError("Must run fit_clusters() before computing t-SNE.")

        # Adjust perplexity if sample size is small
        n_samples = len(self.df)
        eff_perplexity = min(perplexity, max(float(n_samples // 4), 5.0))

        tsne = TSNE(
            n_components=3,
            perplexity=eff_perplexity,
            learning_rate=learning_rate,
            n_iter=n_iter,
            init="pca",
            random_state=42,
        )
        self.tsne_coords = tsne.fit_transform(self.X_scaled)

        self.df["tsne_x"] = np.round(self.tsne_coords[:, 0], 3)
        self.df["tsne_y"] = np.round(self.tsne_coords[:, 1], 3)
        self.df["tsne_z"] = np.round(self.tsne_coords[:, 2], 3)

        return self.df

    def profile_clusters(self) -> Dict[int, Dict[str, Any]]:
        """
        Analyzes cluster centroids relative to league baseline to generate
        descriptive names, attribute traits, and representative flagship players.
        """
        if "cluster_id" not in self.df.columns or self.df.empty:
            return {}

        profiles = {}
        lg_means = self.df[CLUSTERING_FEATURES].mean()
        lg_stds = self.df[CLUSTERING_FEATURES].std().replace(0, 1.0)

        for cid in sorted(self.df["cluster_id"].unique()):
            cluster_df = self.df[self.df["cluster_id"] == cid]
            centroid = cluster_df[CLUSTERING_FEATURES].mean()

            # Z-scores of centroid relative to league distribution
            z_scores = ((centroid - lg_means) / lg_stds).to_dict()

            # Identify flagship players (highest minutes and impact in cluster)
            top_players = cluster_df.sort_values(by=["box_lebron", "total_minutes"], ascending=[False, False])
            flagships = top_players.head(4)["player_name"].tolist()

            # Rule-based archetype naming using centroid Z-scores
            name, desc, key_attributes = self._determine_cluster_identity(z_scores, centroid)

            profiles[int(cid)] = {
                "cluster_id": int(cid),
                "name": name,
                "description": desc,
                "count": len(cluster_df),
                "pct_of_league": round((len(cluster_df) / len(self.df)) * 100, 1),
                "flagship_players": flagships,
                "key_attributes": key_attributes,
                "centroid_stats": {
                    "usg_pct": round(float(centroid["usg_pct"]) * 100, 1),
                    "ts_pct": round(float(centroid["ts_pct"]) * 100, 1),
                    "pts_per_36": round(float(centroid["pts_per_36"]), 1),
                    "ast_pct": round(float(centroid["ast_pct"]) * 100, 1),
                    "reb_pct": round(float(centroid["reb_pct"]) * 100, 1),
                    "fg3a_rate": round(float(centroid["fg3a_rate"]) * 100, 1),
                    "stl_per_36": round(float(centroid["stl_per_36"]), 2),
                    "blk_per_36": round(float(centroid["blk_per_36"]), 2),
                    "box_lebron": round(float(centroid["box_lebron"]), 2),
                    "o_lebron": round(float(centroid["o_lebron"]), 2),
                    "d_lebron": round(float(centroid["d_lebron"]), 2),
                },
                "z_scores": {k: round(float(v), 2) for k, v in z_scores.items()},
            }

        self.cluster_profiles = profiles
        return profiles

    def _determine_cluster_identity(
        self, z: Dict[str, float], c: pd.Series
    ) -> Tuple[str, str, List[str]]:
        """Determines basketball-savvy name and attributes from centroid Z-scores and raw values."""
        z_ast = z.get("ast_pct", 0.0)
        z_usg = z.get("usg_pct", 0.0)
        z_reb = z.get("reb_pct", 0.0)
        z_dreb = z.get("dreb_pct", 0.0)
        z_3pa = z.get("fg3a_rate", 0.0)
        z_blk = z.get("blk_per_36", 0.0)
        z_stl = z.get("stl_per_36", 0.0)
        z_pts = z.get("pts_per_36", 0.0)
        z_leb = z.get("box_lebron", 0.0)

        raw_usg = float(c.get("usg_pct", 0.18))
        raw_ast = float(c.get("ast_pct", 0.12))
        raw_reb = float(c.get("reb_pct", 0.08))
        raw_3pa = float(c.get("fg3a_rate", 0.35))
        raw_blk = float(c.get("blk_per_36", 0.5))
        raw_stl = float(c.get("stl_per_36", 1.0))
        raw_ts = float(c.get("ts_pct", 0.55))
        raw_leb = float(c.get("box_lebron", 0.0))

        # 1. Heliocentric MVP Engine & High-Usage Hub (Elite USG, High AST, High Net Impact)
        if raw_usg >= 0.25 and raw_ast >= 0.20 and (raw_leb >= 0.3 or z_usg > 1.0):
            return (
                "Heliocentric MVP Engine & Focal Hub",
                "Superstar offensive engines who command elite usage, orchestrate half-court scoring, and drive team-wide offensive efficiency.",
                ["Elite Scoring & Creation Load", "Primary Ball Initiation", "High-Leverage Shotmaking", "All-NBA Net Impact"],
            )

        # 2. Two-Way Mobile Big & Stretch Anchor (High REB, Moderate-to-High USG, Rim Protection)
        if raw_reb >= 0.11 and raw_usg >= 0.18 and raw_3pa >= 0.15:
            return (
                "Two-Way Mobile Big & Stretch Anchor",
                "High-impact modern frontcourt anchors capable of rim deterrence, defensive glass dominance, and frontcourt scoring.",
                ["Two-Way Frontcourt Presence", "Rim Protection & Deterrence", "Defensive Rebound Dominance", "Inside-Out Scoring Threat"],
            )

        # 3. Post Playmaker & Interior Engine (High REB, High AST)
        if (raw_reb >= 0.11 and raw_ast >= 0.15) or (raw_usg >= 0.26 and raw_reb >= 0.10):
            return (
                "Post Playmaker & Interior Engine",
                "Dominant frontcourt focal points who command the offense through low-post scoring, playmaking vision, and elite rebounding load.",
                ["Post Creation & Isolation", "Passing Hub from Elbow / Low Post", "Dominant Glass Control", "All-NBA Net Impact"],
            )

        # 4. Rim-Protecting Roll Anchor (High BLK, High REB, Low 3PA)
        if (raw_blk >= 1.4 or z_blk > 0.8) and raw_reb >= 0.12 and raw_3pa <= 0.20:
            return (
                "Rim-Protecting Roll Anchor",
                "Interior defensive anchors who deter rim attempts, control defensive glass, and finish high-percentage pick-and-roll lobs.",
                ["Elite Rim Protection & Deterrence", "Defensive Rebounding", "High-Efficiency Pick & Roll Finishing", "Low Perimeter Volume"],
            )

        # 5. Floor-Spacing Stretch Big (Frontcourt with high 3PA rate and rim deterrence)
        if raw_reb >= 0.09 and raw_3pa >= 0.30 and (raw_blk >= 0.8 or z_blk > 0.3):
            return (
                "Floor-Spacing Stretch Big",
                "Versatile frontcourt players who pull opposing rim protectors out of the paint with 3-point gravity while providing interior help.",
                ["Perimeter Floor Spacing", "Pick-and-Pop Shooting", "Help-Side Shot Blocking", "Defensive Rebounding"],
            )

        # 6. Primary Playmaker / Floor General (High AST%, High Pass Creation)
        if raw_ast >= 0.21 or (z_ast > 1.0 and raw_3pa >= 0.30):
            return (
                "Primary Playmaker / Floor General",
                "Floor generals who control game tempo, orchestrate pick-and-roll sets, and generate high-value open looks for teammates.",
                ["Elite Assist Creation", "Pick-and-Roll Orchestration", "Floor General Tempo Control", "High Assist-to-Turnover Ratio"],
            )

        # 7. Dynamic Perimeter Scorer / Slasher (High USG%, High Scoring, Rim Pressure)
        if raw_usg >= 0.22 and (z_pts > 0.5 or z_usg > 0.8):
            return (
                "Dynamic Shot Creator / Slasher",
                "High-volume perimeter scoring threats who attack off the dribble, create self-generated looks, and pressure defenses at the rim.",
                ["Three-Level Shot Creation", "Dribble Penetration & Rim Pressure", "Foul Drawing / Free Throw Generation", "High Scoring Load"],
            )

        # 8. 3-and-D Movement Specialist (High 3PA Rate, Efficient Shooting, Low USG)
        if raw_3pa >= 0.50 and raw_ts >= 0.55 and raw_usg <= 0.18:
            return (
                "3-and-D Movement Specialist",
                "Elite off-ball perimeter specialists who generate gravity through relocation, catch-and-shoot 3-pointers, and perimeter spacing.",
                ["High 3-Point Attempt Rate", "Catch-and-Shoot Accuracy", "Off-Ball Relocation Gravity", "Low Turnover Liability"],
            )

        # 9. Point-of-Attack Defensive Disruptor (High Steal Rate, High Perimeter Activity)
        if raw_stl >= 1.4 or (z_stl > 0.8 and raw_ast >= 0.14):
            return (
                "Point-of-Attack Defensive Disruptor",
                "Tenacious perimeter ball-hawks who disrupt opponent initiators with point-of-attack ball pressure, deflections, and transition pushes.",
                ["Point-of-Attack Ball Pressure", "Steal & Deflection Creation", "Fastbreak Ignition", "High Defensive Energy"],
            )

        # 10. Defensive Wing / Slashing Forward (Moderate Rebounding, Wing Spacing)
        if raw_reb >= 0.07 and raw_3pa >= 0.35 and raw_usg <= 0.18:
            return (
                "Versatile 3-and-D Wing",
                "Switchable wing defenders who provide supplemental floor spacing, weakside cut finishing, and positional defensive flexibility.",
                ["Switchable Perimeter Defense", "Spot-Up 3-Point Spacing", "Transition Rim Running", "Positional Flexibility"],
            )

        # 11. Low-Usage Connector / Bench Glue Guy (Default fallback)
        return (
            "Low-Usage Glue Guy / Connector",
            "Reliable complementary rotation players who fill specific tactical gaps with ball movement, spot-up spacing, and positional defense.",
            ["Low-Usage Efficiency", "Connective Ball Movement", "Positional Flexibility", "Role Discipline"],
        )

    def generate_3d_plot_html(
        self,
        output_file: Optional[str] = None,
        title: str = "NBA Player Positions: 3D t-SNE Unsupervised Clustering",
    ) -> str:
        """
        Generates an interactive Plotly 3D scatter chart with custom tooltips,
        cluster color palettes, and camera controls.
        """
        if "tsne_x" not in self.df.columns or self.df.empty:
            raise ValueError("Must run fit_clusters() and compute_3d_tsne() before generating plot.")

        df_plot = self.df.copy()

        # Build informative hover text
        hover_text = []
        for _, row in df_plot.iterrows():
            txt = (
                f"<b>{row['player_name']}</b> ({row.get('team_abbreviation', 'NBA')})<br>"
                f"<b>Role Archetype:</b> {row.get('cluster_name', 'N/A')}<br>"
                f"<b>Minutes:</b> {row.get('total_minutes', 0):.0f} ({row.get('gp', 0)} GP)<br>"
                f"<b>PPG / USG%:</b> {row.get('pts', 0):.1f} PPG | {row.get('usg_pct', 0)*100:.1f}%<br>"
                f"<b>AST% / REB%:</b> {row.get('ast_pct', 0)*100:.1f}% | {row.get('reb_pct', 0)*100:.1f}%<br>"
                f"<b>3PA Rate:</b> {row.get('fg3a_rate', 0)*100:.1f}% ({row.get('fg3_pct', 0)*100:.1f}% 3P%)<br>"
                f"<b>Box LEBRON:</b> {row.get('box_lebron', 0):+.2f} (O: {row.get('o_lebron', 0):+.2f}, D: {row.get('d_lebron', 0):+.2f})<br>"
                f"<b>3D Coords:</b> ({row['tsne_x']:.2f}, {row['tsne_y']:.2f}, {row['tsne_z']:.2f})"
            )
            hover_text.append(txt)

        df_plot["hover_info"] = hover_text

        # Distinct color palette for up to 12 clusters
        palette = [
            "#3B82F6", "#EF4444", "#10B981", "#F59E0B",
            "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
            "#F97316", "#6366F1", "#14B8A6", "#E11D48"
        ]

        fig = px.scatter_3d(
            df_plot,
            x="tsne_x",
            y="tsne_y",
            z="tsne_z",
            color="cluster_name",
            color_discrete_sequence=palette,
            hover_name="player_name",
            custom_data=["hover_info"],
            title=title,
            labels={
                "tsne_x": "t-SNE Dimension 1",
                "tsne_y": "t-SNE Dimension 2",
                "tsne_z": "t-SNE Dimension 3",
                "cluster_name": "Discovered Position Archetype",
            },
        )

        fig.update_traces(
            hovertemplate="%{customdata[0]}<extra></extra>",
            marker=dict(size=4.5, opacity=0.85, line=dict(width=0.5, color="#FFFFFF")),
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0F172A",
            plot_bgcolor="#0F172A",
            font=dict(family="Inter, -apple-system, sans-serif", color="#E2E8F0", size=12),
            legend=dict(
                title=dict(text="<b>Role Archetypes</b>", font=dict(size=13, color="#F8FAFC")),
                bgcolor="rgba(15, 23, 42, 0.8)",
                bordercolor="rgba(148, 163, 184, 0.2)",
                borderwidth=1,
                itemsizing="constant",
            ),
            scene=dict(
                xaxis=dict(backgroundcolor="#1E293B", gridcolor="#334155", showbackground=True),
                yaxis=dict(backgroundcolor="#1E293B", gridcolor="#334155", showbackground=True),
                zaxis=dict(backgroundcolor="#1E293B", gridcolor="#334155", showbackground=True),
            ),
            margin=dict(l=20, r=20, t=60, b=20),
        )

        html_str = fig.to_html(include_plotlyjs="cdn", full_html=True)
        if output_file:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_str)
            logger.info("Saved 3D clustering visualization to: %s", output_file)

        return html_str

    def save_to_db(self) -> int:
        """Upserts clustering results and 3D t-SNE coordinates into the database."""
        if "cluster_id" not in self.df.columns or "tsne_x" not in self.df.columns:
            raise ValueError("Must run fit_clusters() and compute_3d_tsne() before saving to database.")

        records = []
        now = datetime.datetime.utcnow().isoformat()

        for _, row in self.df.iterrows():
            records.append({
                "player_id": int(row["player_id"]),
                "season": str(row["season"]),
                "season_type": str(row.get("season_type", "Regular Season")),
                "player_name": str(row["player_name"]),
                "team_abbreviation": str(row.get("team_abbreviation", "")),
                "gp": int(row.get("gp", 0)),
                "min": float(row.get("total_minutes", 0.0)),
                "cluster_id": int(row["cluster_id"]),
                "cluster_name": str(row.get("cluster_name", f"Cluster {row['cluster_id']}")),
                "tsne_x": float(row.get("tsne_x", 0.0)),
                "tsne_y": float(row.get("tsne_y", 0.0)),
                "tsne_z": float(row.get("tsne_z", 0.0)),
                "usg_pct": float(row.get("usg_pct", 0.0)),
                "ts_pct": float(row.get("ts_pct", 0.0)),
                "ast_pct": float(row.get("ast_pct", 0.0)),
                "reb_pct": float(row.get("reb_pct", 0.0)),
                "oreb_pct": float(row.get("oreb_pct", 0.0)),
                "dreb_pct": float(row.get("dreb_pct", 0.0)),
                "fg3a_rate": float(row.get("fg3a_rate", 0.0)),
                "stl_per_36": float(row.get("stl_per_36", 0.0)),
                "blk_per_36": float(row.get("blk_per_36", 0.0)),
                "box_lebron": float(row.get("box_lebron", 0.0)),
                "o_lebron": float(row.get("o_lebron", 0.0)),
                "d_lebron": float(row.get("d_lebron", 0.0)),
                "updated_at": now,
            })

        inserted = self.db.upsert_rows(
            table_name="player_position_clusters",
            rows=records,
            conflict_keys=["player_id", "season", "season_type"],
        )
        logger.info("Saved %d player position cluster records to database.", inserted)
        return inserted
