"""Dashboard SantéScope alimenté par les résultats réels Insee et BPE."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent
FICHIER_ANALYSE = BASE_DIR / "resultats" / "analyse_departements.csv"
URL_GEOJSON_DEPARTEMENTS = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-avec-outre-mer.geojson"
)
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
    fig = styliser(fig)
    pops_valides = valeurs["population_2023"].dropna()
    pops_valides = pops_valides[pops_valides > 0]
    if not pops_valides.empty:
        pop_max = float(pops_valides.max())
        repere_pops = sorted(
            {
                float(pops_valides.min()),
                float(pops_valides.median()),
                pop_max,
            }
        )
        for idx, pop_val in enumerate(repere_pops):
            diametre = max(4.0, 22.0 * np.sqrt(pop_val / pop_max))
            fig.add_scatter(
                x=[None],
                y=[None],
                mode="markers",
                name=f"{pop_val:,.0f}".replace(",", " "),
                legendgroup="population",
                legendgrouptitle_text="Population (hab.)" if idx == 0 else None,
                marker={
                    "size": diametre,
                    "color": COULEURS["petrole"],
                    "opacity": 0.7,
                },
                showlegend=True,
            )
    fig.update_layout(
        margin={"t": 68},
        legend={"itemsizing": "trace"},
    )
    return fig


def iterer_coordonnees_geojson(coordonnees):
    if (
        isinstance(coordonnees, list)
        and len(coordonnees) == 2
        and all(isinstance(valeur, (int, float)) for valeur in coordonnees)
    ):
        yield float(coordonnees[0]), float(coordonnees[1])
        return

    if isinstance(coordonnees, list):
        for element in coordonnees:
            yield from iterer_coordonnees_geojson(element)


@st.cache_data(show_spinner=False)
def charger_geojson_departements() -> dict:
    with urlopen(URL_GEOJSON_DEPARTEMENTS, timeout=20) as reponse:
        geojson = json.load(reponse)

    if not isinstance(geojson, dict) or not isinstance(geojson.get("features"), list):
        raise ValueError("Le fichier géographique des départements est invalide.")
    for feature in geojson["features"]:
        if (
            not isinstance(feature, dict)
            or not feature.get("properties", {}).get("code")
            or not feature.get("geometry", {}).get("coordinates")
        ):
            raise ValueError("Une géométrie départementale est incomplète.")
    return geojson


def afficher_carte_offre(
    donnees: pd.DataFrame,
    region: str,
    departement_focus: str,
) -> None:
    donnees_carte = donnees.copy()

    if donnees_carte.empty:
        st.warning("Aucun département n’est disponible pour ce périmètre.")
        return

    try:
        geojson = charger_geojson_departements()
    except (OSError, ValueError) as erreur:
        st.error(f"Impossible de charger les contours des départements : {erreur}")
        return

    donnees_par_departement = {
        str(ligne.code_dep): ligne
        for ligne in donnees_carte.itertuples(index=False)
    }
    densites = donnees_carte["densite_100k"].dropna()
    densite_min = densites.min() if not densites.empty else 0
    densite_max = densites.max() if not densites.empty else 0
    features_carte = []
    for feature in geojson["features"]:
        code = str(feature["properties"]["code"])
        ligne = donnees_par_departement.get(code)
        if ligne is None and region != "Toutes les régions":
            continue
        densite = ligne.densite_100k if ligne is not None else None
        nb_lieux = ligne.nb_lieux if ligne is not None else None
        proprietes = {
            **feature["properties"],
            "densite_affichee": (
                f"{densite:.1f}" if pd.notna(densite) else "Non disponible"
            ),
            "lieux_affiches": (
                f"{nb_lieux:,.0f}".replace(",", " ")
                if pd.notna(nb_lieux)
                else "Non disponible"
            ),
        }
        features_carte.append({**feature, "properties": proprietes})

    if not features_carte:
        st.warning("Aucun contour départemental n’est disponible pour ce périmètre.")
        return

    carte = folium.Map(
        location=[46.603354, 1.888334],
        zoom_start=6,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    def styliser_departement(feature):
        code = str(feature["properties"]["code"])
        ligne = donnees_par_departement.get(code)
        densite = ligne.densite_100k if ligne is not None else None
        if densite is None or pd.isna(densite) or densite_max <= 0:
            couleur = "#E5EAEC"
            opacite = 0.35
        else:
            ratio = min(max(densite / densite_max, 0), 1)
            couleur = "#{:02X}{:02X}{:02X}".format(
                *(
                    round(clair + (fonce - clair) * ratio)
                    for clair, fonce in zip((191, 232, 226), (20, 106, 120))
                )
            )
            opacite = 0.4 + 0.5 * ratio

        selectionne = code == departement_focus
        return {
            "fillColor": couleur,
            "fillOpacity": opacite,
            "color": COULEURS["ambre"] if selectionne else "#687A80",
            "weight": 2.5 if selectionne else 0.8,
        }

    folium.GeoJson(
        {"type": "FeatureCollection", "features": features_carte},
        style_function=styliser_departement,
        tooltip=folium.GeoJsonTooltip(
            fields=["nom", "densite_affichee", "lieux_affiches"],
            aliases=["Département :", "Densité / 100 000 hab. :", "Lieux BPE :"],
            sticky=True,
        ),
    ).add_to(carte)

    coordonnees = [
        point
        for feature in features_carte
        for point in iterer_coordonnees_geojson(
            feature["geometry"]["coordinates"]
        )
    ]
    longitudes, latitudes = zip(*coordonnees)
    carte.fit_bounds(
        [
            [min(latitudes), min(longitudes)],
            [max(latitudes), max(longitudes)],
        ],
        padding=(24, 24),
    )

    legende = f"""
    <div style="
        position: fixed; bottom: 28px; right: 16px; z-index: 9999;
        width: 230px; padding: 10px 12px; background: white;
        border: 1px solid #AAB7BB; border-radius: 5px;
        box-shadow: 0 1px 5px rgba(0,0,0,.25); font-size: 12px;
    ">
      <strong>Densité (lieux / 100 000 hab.)</strong>
      <div style="
        height: 12px; margin: 7px 0 3px;
        background: linear-gradient(to right, #BFE8E2, #146A78);
      "></div>
      <div style="display: flex; justify-content: space-between;">
        <span>{densite_min:.1f}</span><span>{densite_max:.1f}</span>
      </div>
      <div style="margin-top: 5px;">Gris : donnée indisponible</div>
      <div>
        <span style="
          display: inline-block; width: 11px; height: 11px;
          border: 2px solid {COULEURS['ambre']}; vertical-align: middle;
        "></span>
        Département sélectionné
      </div>
    </div>
    """
    carte.get_root().html.add_child(folium.Element(legende))

    st_folium(carte, height=500, use_container_width=True, returned_objects=[])
    st.caption(
        "Chaque département est coloré selon la densité observée de la profession sélectionnée. "
        "La teinte va du clair (densité faible) au foncé (densité élevée) ; les zones grises "
        "n’ont pas de valeur disponible. Survolez un département pour voir les détails."
    )


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
                use_container_width=True,
                config={"displayModeBar": False},
                key="overview-density",
            )
        with droite:
            st.plotly_chart(
                graphique_professions(base_region),
                use_container_width=True,
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
                use_container_width=True,
                config={"displayModeBar": False},
                key="population-concentration",
            )
        with droite:
            fig_dispersion = px.scatter(
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
                legend={
                    "title_text": "Population (hab.)",
                    "itemsizing": "trace",
                    "itemclick": False,
                    "itemdoubleclick": False,
                },
            )
            pops_valides = population_region["population_2023"].dropna()
            pops_valides = pops_valides[pops_valides > 0]
            if not pops_valides.empty:
                pop_max = float(pops_valides.max())
                repere_pops = sorted(
                    {
                        float(pops_valides.min()),
                        float(pops_valides.median()),
                        pop_max,
                    }
                )
                for pop_val in repere_pops:
                    diametre = max(4.0, 22.0 * np.sqrt(pop_val / pop_max))
                    fig_dispersion.add_scatter(
                        x=[None],
                        y=[None],
                        mode="markers",
                        name=f"{pop_val:,.0f}".replace(",", " "),
                        marker={
                            "size": diametre,
                            "color": COULEURS["turquoise"],
                            "opacity": 0.7,
                        },
                        showlegend=True,
                    )
            st.plotly_chart(
                fig_dispersion,
                use_container_width=True,
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
            afficher_carte_offre(offre, region, departement_focus)
            st.plotly_chart(
                graphique_densites(observee, departement_focus),
                use_container_width=True,
                config={"displayModeBar": False},
                key="offer-density",
            )
        st.plotly_chart(
            graphique_professions(base_region),
            use_container_width=True,
            config={"displayModeBar": False},
            key="offer-professions",
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
                use_container_width=True,
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
        st.dataframe(extrait, use_container_width=True, hide_index=True)
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
