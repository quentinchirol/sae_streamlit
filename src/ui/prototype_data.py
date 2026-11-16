"""Chargement des données (réelles Insee depuis data/ + BPE/APL abstraits) et graphiques (Personne D)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

# Racine du dépôt : sae_streamlit/
BASE_DIR = Path(__file__).resolve().parents[2]
DOSSIER_DATA = BASE_DIR / "data"
FICHIER_ANALYSE_A = BASE_DIR / "resultats" / "analyse_departements.csv"

PALETTE = {
    "fond": "#F7FAF9",
    "texte": "#18343B",
    "petrole": "#146A78",
    "turquoise": "#42A69B",
    "bleu_pale": "#E0F1F0",
    "ambre": "#D99442",
}

PROFESSIONS_CFG = {
    "Médecin généraliste": (88.0, 14.0, 3.6, 0.7, "Consultations / hab. standardisé"),
    "Infirmier": (145.0, 32.0, 112.0, 24.0, "ETP / 100 000 hab. standardisés"),
    "Kinésithérapeute": (95.0, 22.0, 78.0, 18.0, "ETP / 100 000 hab. standardisés"),
    "Chirurgien-dentiste": (62.0, 15.0, 54.0, 12.0, "ETP / 100 000 hab. standardisés"),
}

# Coordonnées approximatives des centroïdes départementaux pour la carte de maquette
CENTROIDS_DEP = {
    "01": (5.35, 46.10), "02": (3.56, 49.56), "03": (3.19, 46.39), "04": (6.24, 44.10),
    "05": (6.26, 44.66), "06": (7.12, 43.94), "07": (4.42, 44.75), "08": (4.64, 49.61),
    "09": (1.50, 42.92), "10": (4.16, 48.30), "11": (2.41, 43.10), "12": (2.68, 44.28),
    "13": (5.09, 43.54), "14": (-0.36, 49.10), "15": (2.67, 45.05), "16": (0.20, 45.72),
    "17": (-0.82, 45.90), "18": (2.49, 47.07), "19": (1.88, 45.36), "2A": (8.99, 41.86),
    "2B": (9.21, 42.40), "21": (4.77, 47.42), "22": (-2.86, 48.44), "23": (2.02, 46.09),
    "24": (0.74, 45.15), "25": (6.36, 47.17), "26": (5.17, 44.68), "27": (0.99, 49.11),
    "28": (1.37, 48.39), "29": (-4.06, 48.26), "30": (4.18, 43.99), "31": (1.17, 43.36),
    "32": (0.45, 43.69), "33": (-0.58, 44.83), "34": (3.37, 43.58), "35": (-1.64, 48.15),
    "36": (1.58, 46.78), "37": (0.69, 47.26), "38": (5.58, 45.26), "39": (5.70, 46.73),
    "40": (-0.78, 43.97), "41": (1.43, 47.62), "42": (4.17, 45.73), "43": (3.81, 45.08),
    "44": (-1.68, 47.36), "45": (2.34, 47.91), "46": (1.60, 44.62), "47": (0.46, 44.37),
    "48": (3.50, 44.52), "49": (-0.56, 47.39), "50": (-1.33, 49.08), "51": (4.24, 48.95),
    "52": (5.23, 48.11), "53": (-0.66, 48.15), "54": (6.16, 48.79), "55": (5.38, 49.01),
    "56": (-2.81, 47.85), "57": (6.66, 49.04), "58": (3.50, 47.12), "59": (3.22, 50.45),
    "60": (2.43, 49.41), "61": (0.13, 48.62), "62": (2.29, 50.49), "63": (3.15, 45.73),
    "64": (-0.76, 43.26), "65": (0.16, 43.05), "66": (2.52, 42.60), "67": (7.55, 48.67),
    "68": (7.27, 47.86), "69": (4.64, 45.87), "70": (6.09, 47.64), "71": (4.54, 46.65),
    "72": (0.22, 47.92), "73": (6.44, 45.48), "74": (6.43, 46.03), "75": (2.35, 48.86),
    "76": (1.03, 49.66), "77": (2.93, 48.63), "78": (1.84, 48.82), "79": (-0.32, 46.56),
    "80": (2.28, 49.96), "81": (2.17, 43.79), "82": (1.28, 44.08), "83": (6.24, 43.44),
    "84": (5.18, 44.01), "85": (-1.30, 46.67), "86": (0.46, 46.56), "87": (1.24, 45.89),
    "88": (6.38, 48.20), "89": (3.56, 47.84), "90": (6.93, 47.63), "91": (2.24, 48.52),
    "92": (2.25, 48.85), "93": (2.48, 48.92), "94": (2.47, 48.78), "95": (2.13, 49.08),
    "971": (-4.50, 42.20), "972": (-3.50, 42.20), "973": (-2.50, 42.20), "974": (-1.50, 42.20),
}


def _calculer_demographie_depuis_data() -> pd.DataFrame:
    """Calcule la table démographique des 100 départements depuis data/*.csv."""
    departements = pd.read_csv(
        DOSSIER_DATA / "donnees_departements.csv",
        sep=";",
        dtype={"DEP": str, "REG": str},
    )
    communes = pd.read_csv(
        DOSSIER_DATA / "donnees_communes.csv",
        sep=";",
        dtype={"DEP": str, "COM": str},
    )

    # Regroupement des arrondissements de Paris, Lyon et Marseille (cf. population.py)
    communes = communes[["DEP", "COM", "Commune", "PMUN"]].copy()
    for num in range(1, 21):
        communes.loc[communes["COM"] == f"751{num:02d}", "COM"] = "75056"
    for num in range(1, 10):
        communes.loc[communes["COM"] == f"6938{num}", "COM"] = "69123"
    for num in range(1, 17):
        communes.loc[communes["COM"] == f"132{num:02d}", "COM"] = "13055"

    communes_agg = communes.groupby(["DEP", "COM"], as_index=False)["PMUN"].sum()

    lignes_conc = []
    for code_dep, groupe in communes_agg.groupby("DEP"):
        pops = groupe["PMUN"].sort_values(ascending=False)
        pop_tot = float(pops.sum())
        nb_com = len(pops)
        nb_top = max(1, math.ceil(nb_com * 0.10))
        petites = pops[pops < 500]
        lignes_conc.append(
            {
                "code_dep": str(code_dep).strip().zfill(2),
                "pct_plus_grande_commune": float(pops.iloc[0] / pop_tot * 100),
                "pct_population_top_10pct_communes": float(pops.head(nb_top).sum() / pop_tot * 100),
                "pct_petites_communes": float(len(petites) / nb_com * 100),
                "pct_population_petites_communes": float(petites.sum() / pop_tot * 100),
            }
        )

    df_conc = pd.DataFrame(lignes_conc)
    df_dep = departements[["DEP", "Département", "REG", "Région", "PMUN", "NBCOM"]].rename(
        columns={
            "DEP": "code_dep",
            "Département": "nom_dep",
            "REG": "code_reg",
            "Région": "nom_region",
            "PMUN": "population_2023",
            "NBCOM": "nb_communes",
        }
    )
    df_dep["code_dep"] = df_dep["code_dep"].str.strip().str.zfill(2)
    df_dep["code_reg"] = df_dep["code_reg"].str.strip().str.zfill(2)
    return df_dep.merge(df_conc, on="code_dep", how="left", validate="one_to_one")


def _ajouter_bpe_et_apl_abstraits(df_demo: pd.DataFrame) -> pd.DataFrame:
    """Génère les variables BPE et APL simulées pour chaque profession sur la base démographique."""
    rng = np.random.default_rng(42)
    lignes = []
    for row in df_demo.itertuples():
        for prof, (d_moy, d_std, apl_moy, apl_std, unite_apl) in PROFESSIONS_CFG.items():
            effet_conc = ((row.pct_population_top_10pct_communes - 50.0) / 100.0) * (d_std * 0.85)
            densite = max(15.0, round(rng.normal(d_moy + effet_conc, d_std), 1))
            nb_lieux = int(round((densite * row.population_2023) / 100_000))
            apl = max(0.5, round((densite / d_moy) * apl_moy + rng.normal(0, apl_std * 0.35), 2))
            couverture = round(rng.uniform(96.5, 100.0), 1)

            lignes.append(
                {
                    "code_dep": row.code_dep,
                    "nom_dep": row.nom_dep,
                    "code_reg": row.code_reg,
                    "nom_region": row.nom_region,
                    "population_2023": int(row.population_2023),
                    "nb_communes": int(row.nb_communes),
                    "pct_plus_grande_commune": float(row.pct_plus_grande_commune),
                    "pct_population_top_10pct_communes": float(row.pct_population_top_10pct_communes),
                    "pct_petites_communes": float(row.pct_petites_communes),
                    "pct_population_petites_communes": float(row.pct_population_petites_communes),
                    "profession": prof,
                    "nb_lieux": nb_lieux,
                    "bpe_disponible": True,
                    "statut_offre": "simule_maquette",
                    "densite_100k": densite,
                    "apl_2024": apl,
                    "unite_apl": unite_apl,
                    "couverture_pop_pct": couverture,
                }
            )
    return pd.DataFrame(lignes)


def _completer_apl_sur_table_a(df_a: pd.DataFrame) -> pd.DataFrame:
    """Complète la table réelle de la Partie A avec des colonnes APL simulées tant que B n'est pas fusionnée."""
    rng = np.random.default_rng(42)
    df = df_a.copy()
    if "apl_2024" not in df.columns:
        apl_vals, unites, couvertures = [], [], []
        for row in df.itertuples():
            d_moy, _, apl_moy, apl_std, unite = PROFESSIONS_CFG.get(
                row.profession, (90.0, 15.0, 50.0, 10.0, "ETP / 100 000 hab. standardisés")
            )
            ratio = (row.densite_100k / d_moy) if pd.notna(row.densite_100k) else 1.0
            apl_vals.append(max(0.5, round(ratio * apl_moy + rng.normal(0, apl_std * 0.35), 2)))
            unites.append(unite)
            couvertures.append(round(rng.uniform(96.5, 100.0), 1))
        df["apl_2024"] = apl_vals
        df["unite_apl"] = unites
        df["couverture_pop_pct"] = couvertures
    return df


@st.cache_data
def charger_donnees_ui() -> tuple[pd.DataFrame, str]:
    """Charge les données disponibles dans l'arborescence (resultats/ > data/ > repli abstrait).

    Returns:
        tuple[pd.DataFrame, str]: Table analytique et libellé de la source active.
    """
    if FICHIER_ANALYSE_A.exists():
        df_reel = pd.read_csv(FICHIER_ANALYSE_A, dtype={"code_dep": str, "code_reg": str})
        df_reel["code_dep"] = df_reel["code_dep"].str.strip().str.zfill(2)
        return _completer_apl_sur_table_a(df_reel), "resultats/analyse_departements.csv (Insee + BPE réels)"

    if (DOSSIER_DATA / "donnees_departements.csv").exists() and (DOSSIER_DATA / "donnees_communes.csv").exists():
        df_demo = _calculer_demographie_depuis_data()
        return _ajouter_bpe_et_apl_abstraits(df_demo), "data/*.csv (100 dép. Insee réels + BPE/APL abstraits)"

    # Repli minimal si aucun CSV n'est présent
    df_repli = pd.DataFrame(
        [
            ("75", "Paris", "11", "Île-de-France", 2103778, 1, 100.0, 100.0, 0.0, 0.0),
            ("79", "Deux-Sèvres", "75", "Nouvelle-Aquitaine", 375415, 256, 16.0, 49.0, 47.0, 12.0),
            ("69", "Rhône", "84", "Auvergne-Rhône-Alpes", 1907982, 287, 27.0, 69.0, 25.0, 5.0),
            ("23", "Creuse", "75", "Nouvelle-Aquitaine", 115529, 256, 11.0, 39.0, 79.0, 32.0),
        ],
        columns=[
            "code_dep", "nom_dep", "code_reg", "nom_region", "population_2023",
            "nb_communes", "pct_plus_grande_commune", "pct_population_top_10pct_communes",
            "pct_petites_communes", "pct_population_petites_communes",
        ],
    )
    return _ajouter_bpe_et_apl_abstraits(df_repli), "Jeu abstrait minimal (repli)"


@st.cache_data
def generer_geojson_maquette(codes_presents: tuple[str, ...]) -> dict:
    """Construit un GeoJSON schématique aux positions réelles des départements pour l'aperçu carte."""
    features = []
    for idx, code_dep in enumerate(sorted(codes_presents)):
        if code_dep in CENTROIDS_DEP:
            lon, lat = CENTROIDS_DEP[code_dep]
        else:
            lon = -4.0 + (idx % 12) * 1.1
            lat = 42.0 + (idx // 12) * 0.9

        delta = 0.14 if code_dep in {"75", "92", "93", "94"} else 0.34
        polygone = [
            [lon - delta, lat - delta],
            [lon + delta, lat - delta],
            [lon + delta, lat + delta],
            [lon - delta, lat + delta],
            [lon - delta, lat - delta],
        ]
        features.append(
            {
                "type": "Feature",
                "id": code_dep,
                "properties": {"code": code_dep},
                "geometry": {"type": "Polygon", "coordinates": [polygone]},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def calculer_correlations(df: pd.DataFrame, col_x: str, col_y: str) -> dict[str, float | int]:
    """Calcule les corrélations de Spearman et Pearson sur le sous-échantillon actif."""
    propre = df[[col_x, col_y]].dropna()
    n = len(propre)
    if n < 3:
        return {"n": n, "spearman": float("nan"), "p_spearman": float("nan"), "pearson": float("nan")}
    rho, p_val = stats.spearmanr(propre[col_x], propre[col_y])
    r_pear, _ = stats.pearsonr(propre[col_x], propre[col_y])
    return {"n": n, "spearman": float(rho), "p_spearman": float(p_val), "pearson": float(r_pear)}


def styliser_figure(fig: go.Figure, titre: str, sous_titre: str = "") -> go.Figure:
    """Applique la charte visuelle SantéScope à une figure Plotly."""
    titre_html = f"<b>{titre}</b>"
    if sous_titre:
        titre_html += f"<br><span style='font-size:12px;color:#4A656C'>{sous_titre}</span>"
    fig.update_layout(
        title={"text": titre_html, "x": 0.01, "xanchor": "left"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": PALETTE["texte"], "family": "sans-serif"},
        margin={"t": 62, "b": 36, "l": 40, "r": 20},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E2ECEA", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#E2ECEA", zeroline=False)
    return fig


def fig_carte_choroplethe(
    df: pd.DataFrame,
    col_val: str,
    titre: str,
    label_val: str,
    est_pct: bool = False,
) -> go.Figure:
    """Génère la carte choroplèthe départementale (maquette avec GeoJSON schématique)."""
    geojson = generer_geojson_maquette(tuple(df["code_dep"].unique()))
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="code_dep",
        featureidkey="properties.code",
        color=col_val,
        hover_name="nom_dep",
        hover_data={"code_dep": True, "nom_region": True, col_val: ":.1f"},
        color_continuous_scale=[PALETTE["bleu_pale"], PALETTE["turquoise"], PALETTE["petrole"]],
        labels={col_val: label_val},
    )
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    if est_pct:
        fig.update_layout(coloraxis_colorbar={"ticksuffix": " %"})
    return styliser_figure(fig, titre, "Carte schématique (sera remplacée par le GeoJSON officiel de C)")


def fig_classement_barres(
    df: pd.DataFrame,
    col_val: str,
    titre: str,
    label_val: str,
    dep_focus: str = "Tous",
    est_pct: bool = False,
) -> go.Figure:
    """Classement horizontal des départements (extrêmes) avec mise en évidence du focus."""
    df_valide = df.dropna(subset=[col_val]).sort_values(col_val, ascending=True).copy()
    if len(df_valide) > 12:
        extremes = pd.concat([df_valide.head(6), df_valide.tail(6)])
        if dep_focus != "Tous":
            extremes = pd.concat([extremes, df_valide[df_valide["code_dep"] == dep_focus]])
        df_valide = extremes.drop_duplicates("code_dep").sort_values(col_val, ascending=True)

    df_valide["etiquette"] = df_valide["nom_dep"] + " (" + df_valide["code_dep"] + ")"
    df_valide["Selection"] = np.where(
        df_valide["code_dep"] == dep_focus,
        "Département ciblé",
        "Autres départements",
    )
    fig = px.bar(
        df_valide,
        x=col_val,
        y="etiquette",
        orientation="h",
        color="Selection",
        color_discrete_map={
            "Autres départements": PALETTE["petrole"],
            "Département ciblé": PALETTE["ambre"],
        },
        labels={col_val: label_val, "etiquette": ""},
        text_auto=".1f",
    )
    if est_pct:
        fig.update_xaxes(ticksuffix=" %")
    return styliser_figure(fig, titre, "Comparaison des valeurs extrêmes du périmètre actif")


def fig_nuage_territorial(
    df: pd.DataFrame,
    col_x: str,
    col_y: str,
    label_x: str,
    label_y: str,
    titre: str,
    dep_focus: str = "Tous",
    droite_tendance: bool = False,
) -> go.Figure:
    """Nuage de points central reliant structure démographique et offre/accessibilité."""
    df_plot = df.dropna(subset=[col_x, col_y]).copy()
    conditions = [
        df_plot["code_dep"] == dep_focus,
        df_plot["code_dep"] == "75",
    ]
    choix = ["Département ciblé", "Paris (75)"]
    df_plot["Categorie"] = np.select(conditions, choix, default="Départements")

    fig = px.scatter(
        df_plot,
        x=col_x,
        y=col_y,
        size="population_2023",
        color="Categorie",
        color_discrete_map={
            "Départements": PALETTE["petrole"],
            "Paris (75)": PALETTE["ambre"],
            "Département ciblé": PALETTE["turquoise"],
        },
        hover_name="nom_dep",
        hover_data={
            "code_dep": True,
            "nom_region": True,
            "population_2023": ":,",
            col_x: ":.1f",
            col_y: ":.2f",
            "Categorie": False,
        },
        labels={col_x: label_x, col_y: label_y},
        size_max=30,
    )
    fig.update_xaxes(ticksuffix=" %")

    if droite_tendance and len(df_plot) >= 3:
        pente, ordonnee = np.polyfit(df_plot[col_x], df_plot[col_y], 1)
        x_vals = np.linspace(df_plot[col_x].min(), df_plot[col_x].max(), 50)
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=pente * x_vals + ordonnee,
                mode="lines",
                name="Droite descriptive OLS",
                line={"color": PALETTE["ambre"], "dash": "dash", "width": 2},
            )
        )

    return styliser_figure(fig, titre, "Taille des bulles proportionnelle à la population Insee 2023")


def fig_boxplot_professions(df_tout: pd.DataFrame, region: str) -> go.Figure:
    """Distribution des densités BPE par profession sur le périmètre régional."""
    df_sub = df_tout if region == "Toutes les régions" else df_tout[df_tout["nom_region"] == region]
    fig = px.box(
        df_sub.dropna(subset=["densite_100k"]),
        x="profession",
        y="densite_100k",
        points="all",
        hover_name="nom_dep",
        color_discrete_sequence=[PALETTE["petrole"]],
        labels={"profession": "", "densite_100k": "Densité BPE (lieux / 100 000 hab.)"},
    )
    return styliser_figure(
        fig,
        "Dispersion départementale par profession",
        f"Périmètre : {region} • BPE 2025 / Population 2023",
    )


def fig_confrontation_bpe_apl(df: pd.DataFrame, dep_focus: str = "Tous") -> go.Figure:
    """Graphique bivarié BPE (X) vs APL (Y) sur deux axes d'unités distinctes."""
    df_plot = df.dropna(subset=["densite_100k", "apl_2024"]).copy()
    unite_apl = df_plot["unite_apl"].iloc[0] if not df_plot.empty else "Unité APL"
    df_plot["Focus"] = np.where(df_plot["code_dep"] == dep_focus, "Département ciblé", "Autres")
    fig = px.scatter(
        df_plot,
        x="densite_100k",
        y="apl_2024",
        color="Focus",
        color_discrete_map={"Autres": PALETTE["petrole"], "Département ciblé": PALETTE["ambre"]},
        hover_name="nom_dep",
        hover_data={"code_dep": True, "couverture_pop_pct": ":.1f", "Focus": False},
        labels={
            "densite_100k": "Densité BPE 2025 (lieux / 100 000 hab.)",
            "apl_2024": f"APL DREES 2024 ({unite_apl})",
        },
    )
    return styliser_figure(
        fig,
        "Densité de lieux (BPE) vs accessibilité potentielle (APL)",
        "Chaque axe conserve son unité propre • Repérage des départements divergents",
    )