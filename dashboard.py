"""Dashboard SantéScope alimenté par les résultats réels Insee et BPE."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent
FICHIER_ANALYSE = BASE_DIR / "resultats" / "analyse_departements.csv"
COULEURS = {
    "encre": "#18343B",
    "petrole": "#146A78",
    "turquoise": "#42A69B",
    "ambre": "#D99442",
    "fond": "#F3F8F7",
    "grille": "#DCE8E6",
}
COLONNES_REQUISES = {
    "code_dep",
    "nom_dep",
    "nom_region",
    "population_2023",
    "nb_communes",
    "pct_plus_grande_commune",
    "pct_population_top_10pct_communes",
    "pct_petites_communes",
    "pct_population_petites_communes",
    "profession",
    "nb_lieux",
    "bpe_disponible",
    "densite_100k",
}
COLONNES_NUMERIQUES = [
    "population_2023",
    "nb_communes",
    "pct_plus_grande_commune",
    "pct_population_top_10pct_communes",
    "pct_petites_communes",
    "pct_population_petites_communes",
    "nb_lieux",
    "densite_100k",
]


@st.cache_data(show_spinner=False)
def charger_donnees() -> pd.DataFrame:
    """Charge et valide la table réelle produite par le pipeline."""
    if not FICHIER_ANALYSE.exists():
        raise FileNotFoundError(
            "La table resultats/analyse_departements.csv est absente. "
            "Lance d'abord le pipeline de préparation des données."
        )

    donnees = pd.read_csv(
        FICHIER_ANALYSE,
        dtype={"code_dep": "string", "code_reg": "string"},
    )
    manquantes = COLONNES_REQUISES - set(donnees.columns)
    if manquantes:
        raise ValueError(
            "Colonnes manquantes dans analyse_departements.csv : "
            + ", ".join(sorted(manquantes))
        )

    donnees["code_dep"] = donnees["code_dep"].str.strip()
    donnees["nom_dep"] = donnees["nom_dep"].astype("string").str.strip()
    donnees["nom_region"] = donnees["nom_region"].astype("string").str.strip()
    donnees["profession"] = donnees["profession"].astype("string").str.strip()
    for colonne in COLONNES_NUMERIQUES:
        donnees[colonne] = pd.to_numeric(donnees[colonne], errors="coerce")
    donnees["bpe_disponible"] = (
        donnees["bpe_disponible"].astype("string").str.lower().map({"true": True, "false": False})
    )

    if donnees.duplicated(["code_dep", "profession"]).any():
        raise ValueError("La table contient plusieurs lignes pour un département et une profession.")
    return donnees


def styliser(fig, hauteur: int = 430):
    fig.update_layout(
        height=hauteur,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Georgia, serif", "color": COULEURS["encre"]},
        margin={"t": 54, "b": 36, "l": 30, "r": 20},
        legend={"orientation": "h", "y": 1.08, "x": 1, "xanchor": "right"},
    )
    fig.update_xaxes(showgrid=True, gridcolor=COULEURS["grille"], zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def filtrer_region(donnees: pd.DataFrame, region: str) -> pd.DataFrame:
    if region == "Toutes les régions":
        return donnees.copy()
    return donnees[donnees["nom_region"] == region].copy()


def graphique_densites(donnees: pd.DataFrame, departement_focus: str) -> object:
    valeurs = donnees.dropna(subset=["densite_100k"]).nlargest(12, "densite_100k").copy()
    valeurs = valeurs.sort_values("densite_100k")
    valeurs["Repère"] = np.where(
        valeurs["code_dep"] == departement_focus, "Département choisi", "Autres"
    )
    fig = px.bar(
        valeurs,
        x="densite_100k",
        y="nom_dep",
        orientation="h",
        color="Repère",
        color_discrete_map={
            "Autres": COULEURS["petrole"],
            "Département choisi": COULEURS["ambre"],
        },
        hover_data={"code_dep": True, "nb_lieux": True, "densite_100k": ":.1f"},
        labels={"densite_100k": "Lieux pour 100 000 habitants", "nom_dep": ""},
    )
    return styliser(fig)


def graphique_concentration(donnees: pd.DataFrame):
    valeurs = donnees.drop_duplicates("code_dep").nlargest(
        15, "pct_population_top_10pct_communes"
    ).sort_values("pct_population_top_10pct_communes")
    fig = px.bar(
        valeurs,
        x="pct_population_top_10pct_communes",
        y="nom_dep",
        orientation="h",
        color="pct_population_top_10pct_communes",
        color_continuous_scale=[COULEURS["fond"], COULEURS["turquoise"], COULEURS["petrole"]],
        hover_data={"code_dep": True, "nb_communes": True},
        labels={
            "pct_population_top_10pct_communes": "Part de population (%)",
            "nom_dep": "",
        },
    )
    return styliser(fig)


def graphique_professions(donnees: pd.DataFrame):
    fig = px.box(
        donnees.dropna(subset=["densite_100k"]),
        x="profession",
        y="densite_100k",
        color="profession",
        points="all",
        hover_name="nom_dep",
        color_discrete_sequence=[COULEURS["petrole"], COULEURS["turquoise"], COULEURS["ambre"], "#7695A0"],
        labels={"profession": "", "densite_100k": "Lieux pour 100 000 habitants"},
    )
    return styliser(fig, hauteur=390)


def graphique_relation(donnees: pd.DataFrame, departement_focus: str):
    valeurs = donnees.dropna(
        subset=["pct_population_top_10pct_communes", "densite_100k"]
    ).copy()
    valeurs["Repère"] = np.where(
        valeurs["code_dep"] == departement_focus, "Département choisi", "Départements"
    )
    fig = px.scatter(
        valeurs,
        x="pct_population_top_10pct_communes",
        y="densite_100k",
        color="Repère",
        size="population_2023",
        size_max=22,
        hover_name="nom_dep",
        hover_data={"code_dep": True, "nom_region": True, "population_2023": ":,"},
        color_discrete_map={
            "Départements": COULEURS["petrole"],
            "Département choisi": COULEURS["ambre"],
        },
        labels={
            "pct_population_top_10pct_communes": "Population dans les 10 % de communes les plus peuplées (%)",
            "densite_100k": "Lieux BPE pour 100 000 habitants",
        },
    )
    if len(valeurs) >= 3 and valeurs["pct_population_top_10pct_communes"].nunique() > 1:
        pente, ordonnee = np.polyfit(
            valeurs["pct_population_top_10pct_communes"], valeurs["densite_100k"], 1
        )
        axe_x = np.linspace(
            valeurs["pct_population_top_10pct_communes"].min(),
            valeurs["pct_population_top_10pct_communes"].max(),
            50,
        )
        fig.add_scatter(
            x=axe_x,
            y=pente * axe_x + ordonnee,
            mode="lines",
            name="Tendance descriptive",
            line={"color": COULEURS["ambre"], "dash": "dash"},
        )
    return styliser(fig)


def afficher_dashboard() -> None:
    st.set_page_config(page_title="SantéScope", page_icon="S", layout="wide")
    st.markdown(
        f"""
        <style>
        .stApp {{ background: linear-gradient(145deg, #F3F8F7 0%, #FFFFFF 55%, #E8F2F0 100%); }}
        h1, h2, h3 {{ color: {COULEURS['encre']}; font-family: Georgia, serif; }}
        div[data-testid="stMetric"] {{
            background: #FFFFFF; border-top: 3px solid {COULEURS['turquoise']};
            padding: 12px 15px; border-radius: 4px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("SantéScope")
    st.caption("Population communale et offre de soins observée | Insee 2023 · BPE 2025")

    try:
        donnees = charger_donnees()
    except (FileNotFoundError, ValueError) as erreur:
        st.error(str(erreur))
        st.code("python __init__.py", language="powershell")
        return

    regions = ["Toutes les régions"] + sorted(donnees["nom_region"].dropna().unique().tolist())
    professions = sorted(donnees["profession"].dropna().unique().tolist())
    departements = donnees[["code_dep", "nom_dep"]].drop_duplicates().sort_values("code_dep")
    options_dep = {
        f"{ligne.code_dep} · {ligne.nom_dep}": ligne.code_dep
        for ligne in departements.itertuples(index=False)
    }
    profession_defaut = "Médecin généraliste" if "Médecin généraliste" in professions else professions[0]

    st.sidebar.subheader("Périmètre")
    with st.sidebar.form("form_filtres"):
        region = st.selectbox("Région", regions, index=0, key="filtre_region")
        profession = st.selectbox(
            "Profession",
            professions,
            index=professions.index(profession_defaut),
            key="filtre_profession",
        )
        focus_label = st.selectbox(
            "Mettre en évidence",
            ["Aucun"] + list(options_dep),
            index=0,
            key="filtre_departement",
        )
        st.form_submit_button("Appliquer", type="primary", width="stretch")
    departement_focus = options_dep.get(focus_label, "")
    st.sidebar.divider()
    st.sidebar.caption("Source affichée : resultats/analyse_departements.csv")
    st.sidebar.caption("Les indicateurs APL ne sont pas inclus dans les données disponibles.")

    base_region = filtrer_region(donnees, region)
    population_region = base_region.drop_duplicates("code_dep")
    offre = base_region[base_region["profession"] == profession].copy()
    observee = offre[offre["bpe_disponible"].fillna(False) & offre["densite_100k"].notna()].copy()

    st.markdown(f"### {region} · {profession}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Population", f"{population_region['population_2023'].sum():,.0f}".replace(",", " "))
    k2.metric("Départements", f"{len(population_region)}")
    k3.metric("Lieux BPE observés", f"{observee['nb_lieux'].sum():,.0f}".replace(",", " "))
    densite_mediane = observee["densite_100k"].median()
    k4.metric("Densité médiane", "Indisponible" if pd.isna(densite_mediane) else f"{densite_mediane:.1f} / 100k")

    tab_apercu, tab_population, tab_offre, tab_relation, tab_donnees = st.tabs(
        ["Vue d'ensemble", "Population", "Offre de soins", "Relations", "Données"]
    )

    with tab_apercu:
        gauche, droite = st.columns([1.15, 1])
        with gauche:
            st.plotly_chart(
                graphique_densites(observee, departement_focus),
                width="stretch",
                config={"displayModeBar": False},
                key="overview-density",
            )
        with droite:
            st.plotly_chart(
                graphique_professions(base_region),
                width="stretch",
                config={"displayModeBar": False},
                key="overview-professions",
            )
        st.info(
            "Les graphiques utilisent les comptages BPE et populations réellement présents dans "
            "la table préparée. La BPE mesure des lieux d'exercice, pas des effectifs de praticiens."
        )

    with tab_population:
        st.subheader("Concentration de la population entre communes")
        gauche, droite = st.columns([1.1, 1])
        with gauche:
            st.plotly_chart(
                graphique_concentration(population_region),
                width="stretch",
                config={"displayModeBar": False},
                key="population-concentration",
            )
        with droite:
            st.plotly_chart(
                px.scatter(
                    population_region,
                    x="pct_plus_grande_commune",
                    y="pct_petites_communes",
                    size="population_2023",
                    size_max=22,
                    hover_name="nom_dep",
                    hover_data={"code_dep": True, "nb_communes": True},
                    labels={
                        "pct_plus_grande_commune": "Population dans la plus grande commune (%)",
                        "pct_petites_communes": "Communes de moins de 500 habitants (%)",
                    },
                    color_discrete_sequence=[COULEURS["turquoise"]],
                ).update_layout(
                    height=430,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                ),
                width="stretch",
                config={"displayModeBar": False},
                key="population-dispersion",
            )
        st.caption(
            "Le découpage communal décrit la concentration administrative ; il ne mesure ni les distances "
            "ni les temps d'accès."
        )

    with tab_offre:
        st.subheader(f"Densité observée · {profession}")
        if observee.empty:
            st.warning("Aucune donnée BPE observée pour ce périmètre.")
        else:
            st.plotly_chart(
                graphique_densites(observee, departement_focus),
                width="stretch",
                config={"displayModeBar": False},
                key="offer-density",
            )
        st.plotly_chart(
            graphique_professions(base_region),
            width="stretch",
            config={"displayModeBar": False},
            key="offer-professions",
        )
        st.info(
            "APL DREES indisponible : aucune valeur simulée n'est affichée. "
            "La comparaison BPE–APL sera activée lorsque les données APL réelles seront intégrées."
        )

    with tab_relation:
        st.subheader("Concentration communale et densité de lieux de soins")
        if len(observee) >= 3:
            correlation = stats.spearmanr(
                observee["pct_population_top_10pct_communes"], observee["densite_100k"]
            ).statistic
            sans_paris = observee[observee["code_dep"] != "75"]
            correlation_sans_paris = (
                stats.spearmanr(
                    sans_paris["pct_population_top_10pct_communes"], sans_paris["densite_100k"]
                ).statistic
                if len(sans_paris) >= 3
                else np.nan
            )
            c1, c2 = st.columns(2)
            c1.metric("Spearman · périmètre affiché", f"{correlation:.2f}")
            c2.metric("Spearman · hors Paris", "Indisponible" if pd.isna(correlation_sans_paris) else f"{correlation_sans_paris:.2f}")
            st.plotly_chart(
                graphique_relation(observee, departement_focus),
                width="stretch",
                config={"displayModeBar": False},
                key="territorial-relation",
            )
        else:
            st.warning("Au moins trois départements observés sont nécessaires pour calculer une corrélation.")
        st.caption("Corrélation descriptive : elle ne démontre pas de lien de causalité.")

    with tab_donnees:
        st.subheader("Table des données réelles")
        colonnes = [
            "code_dep",
            "nom_dep",
            "nom_region",
            "population_2023",
            "nb_communes",
            "pct_population_top_10pct_communes",
            "profession",
            "nb_lieux",
            "densite_100k",
            "statut_offre",
        ]
        extrait = base_region[base_region["profession"] == profession][colonnes].sort_values(
            "code_dep"
        )
        st.dataframe(extrait, width="stretch", hide_index=True)
        st.download_button(
            "Télécharger le tableau CSV",
            data=extrait.to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name="santescope_donnees_reelles.csv",
            mime="text/csv",
        )


def main() -> None:
    afficher_dashboard()


if __name__ == "__main__":
    main()
