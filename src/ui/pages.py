"""Définition des six pages de l'application Streamlit SantéScope (Personne D)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.prototype_data import (
    calculer_correlations,
    fig_boxplot_professions,
    fig_carte_choroplethe,
    fig_classement_barres,
    fig_confrontation_bpe_apl,
    fig_nuage_territorial,
)


def _afficher_encart_interpretation(
    observation: str,
    chiffre: str,
    interpretation: str,
    limite: str,
) -> None:
    """Affiche le bloc d'analyse standardisé en quatre rubriques sous les graphiques."""
    st.markdown(
        f"""
        <div class="encart-constat">
            <strong>Lecture analytique</strong><br>
            • <strong>Observation :</strong> {observation}<br>
            • <strong>Chiffre :</strong> {chiffre}<br>
            • <strong>Interprétation :</strong> {interpretation}<br>
            • <strong>Limite :</strong> {limite}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _filtrer_base(df_brut: pd.DataFrame, filtres: dict) -> pd.DataFrame:
    """Applique les filtres globaux de région, profession et exclusion de Paris."""
    df = df_brut[df_brut["profession"] == filtres["profession"]].copy()
    if filtres["region"] != "Toutes les régions":
        df = df[df["nom_region"] == filtres["region"]]
    if filtres["exclure_paris"]:
        df = df[df["code_dep"] != "75"]
    return df


def afficher_vue_ensemble(df_brut: pd.DataFrame, filtres: dict, info_source: str) -> None:
    """Page 01 : Vue d'ensemble nationale ou régionale."""
    st.title("01 · Vue d'ensemble")
    st.caption("Question : À quoi ressemble la répartition nationale de l'offre de soins ?")

    df = _filtrer_base(df_brut, filtres)
    if df.empty:
        st.warning("Aucun département disponible pour ce périmètre.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Population (Insee 2023)", f"{int(df['population_2023'].sum()):,}".replace(",", " "))
    k2.metric("Départements inclus", f"{len(df)}")
    k3.metric("Lieux d'exercice (BPE 2025)", f"{int(df['nb_lieux'].sum()):,}".replace(",", " "))
    k4.metric("Densité BPE médiane", f"{df['densite_100k'].median():.1f} / 100k")

    st.divider()

    col_g, col_d = st.columns([1.2, 1])
    with col_g:
        st.plotly_chart(
            fig_carte_choroplethe(
                df,
                "densite_100k",
                f"Densité BPE : {filtres['profession']}",
                "Lieux / 100k hab.",
            ),
            use_container_width=True,
        )
    with col_d:
        st.plotly_chart(
            fig_classement_barres(
                df,
                "densite_100k",
                "Extrêmes départementaux (densité BPE)",
                "Lieux / 100 000 hab.",
                dep_focus=filtres["departement"],
            ),
            use_container_width=True,
        )

    _afficher_encart_interpretation(
        observation="Les écarts de densité de lieux d'exercice varient fortement d'un département à l'autre.",
        chiffre=f"Médiane de {df['densite_100k'].median():.1f} lieux pour 100 000 hab. (source : {info_source}).",
        interpretation="Ce cadrage pose le socle descriptif avant de croiser structure démographique et accessibilité.",
        limite="Millésimes hétérogènes (Population 2023, BPE 2025) ; aucune conclusion causale possible.",
    )


def afficher_population(df_brut: pd.DataFrame, filtres: dict) -> None:
    """Page 02 : Concentration et dispersion démographique (Axe A1)."""
    st.title("02 · Concentration de la population")
    st.caption("Question : Où la population est-elle concentrée dans quelques communes ou dispersée ?")

    df_pop = df_brut.drop_duplicates("code_dep").copy()
    if filtres["region"] != "Toutes les régions":
        df_pop = df_pop[df_pop["nom_region"] == filtres["region"]]
    if filtres["exclure_paris"]:
        df_pop = df_pop[df_pop["code_dep"] != "75"]

    if df_pop.empty:
        st.warning("Aucun département disponible pour ce périmètre.")
        return

    indicateurs_pop = {
        "Part des 10 % de communes les plus peuplées (%)": "pct_population_top_10pct_communes",
        "Part de la plus grande commune (%)": "pct_plus_grande_commune",
        "Part de petites communes < 500 hab. (%)": "pct_petites_communes",
    }
    choix_ind_pop = st.radio(
        "Indicateur de structure communale :",
        list(indicateurs_pop.keys()),
        horizontal=True,
    )
    col_ind = indicateurs_pop[choix_ind_pop]

    k1, k2, k3 = st.columns(3)
    k1.metric("Communes totalisées", f"{int(df_pop['nb_communes'].sum()):,}".replace(",", " "))
    k2.metric("Médiane de l'indicateur", f"{df_pop[col_ind].median():.1f} %")
    k3.metric("Maximum observé", f"{df_pop[col_ind].max():.1f} %")

    col_g, col_d = st.columns([1.2, 1])
    with col_g:
        st.plotly_chart(
            fig_carte_choroplethe(
                df_pop,
                col_ind,
                f"Carte : {choix_ind_pop}",
                "Part (%)",
                est_pct=True,
            ),
            use_container_width=True,
        )
    with col_d:
        st.plotly_chart(
            fig_classement_barres(
                df_pop,
                col_ind,
                "Classement des départements",
                choix_ind_pop,
                dep_focus=filtres["departement"],
                est_pct=True,
            ),
            use_container_width=True,
        )

    _afficher_encart_interpretation(
        observation="La concentration communale oppose les départements polarisés par une métropole aux départements à habitat dispersé.",
        chiffre=f"Médiane de {df_pop[col_ind].median():.1f} % sur le périmètre affiché (données Insee 2023 issues de data/).",
        interpretation="Paris (100,0 % sur une seule commune après regroupement des arrondissements) justifie une analyse de sensibilité.",
        limite="La taille communale mesure un maillage administratif, pas la superficie en km² ni le temps de trajet.",
    )


def afficher_offre_soins(df_brut: pd.DataFrame, filtres: dict) -> None:
    """Page 03 : Offre de soins BPE 2025 (Axe A2)."""
    st.title("03 · Offre de soins (BPE 2025)")
    st.caption("Question : Où observe-t-on des densités de lieux d'exercice plus élevées ou plus faibles ?")

    df = _filtrer_base(df_brut, filtres)
    if df.empty:
        st.warning("Aucun département disponible pour ce périmètre.")
        return

    col_g, col_d = st.columns([1.15, 1])
    with col_g:
        st.plotly_chart(
            fig_carte_choroplethe(
                df,
                "densite_100k",
                f"Densité BPE — {filtres['profession']}",
                "Lieux / 100k hab.",
            ),
            use_container_width=True,
        )
    with col_d:
        st.plotly_chart(
            fig_boxplot_professions(df_brut, filtres["region"]),
            use_container_width=True,
        )

    st.plotly_chart(
        fig_classement_barres(
            df,
            "densite_100k",
            f"Classement départemental — {filtres['profession']}",
            "Densité BPE (lieux / 100 000 hab.)",
            dep_focus=filtres["departement"],
        ),
        use_container_width=True,
    )

    _afficher_encart_interpretation(
        observation="La dispersion interdépartementale varie nettement selon la profession étudiée.",
        chiffre=f"Étendue de {df['densite_100k'].min():.1f} à {df['densite_100k'].max():.1f} lieux / 100 000 hab.",
        interpretation="Les profils territoriaux diffèrent entre soins de premier recours et professions paramédicales.",
        limite="La BPE recense des lieux d'exercice libéral, et non un décompte d'équivalents temps plein.",
    )


def afficher_accessibilite_apl(df_brut: pd.DataFrame, filtres: dict) -> None:
    """Page 04 : Accessibilité potentielle localisée DREES 2024 (Axe A3)."""
    st.title("04 · Accessibilité potentielle (APL 2024)")
    st.caption("Question : Une densité BPE élevée implique-t-elle nécessairement une bonne accessibilité ?")

    df = _filtrer_base(df_brut, filtres)
    if df.empty:
        st.warning("Aucun département disponible pour ce périmètre.")
        return

    unite_apl = df["unite_apl"].iloc[0]
    k1, k2, k3 = st.columns(3)
    k1.metric("APL médiane (2024)", f"{df['apl_2024'].median():.2f}")
    k2.metric("Unité réglementaire", unite_apl)
    k3.metric("Couverture population moyenne", f"{df['couverture_pop_pct'].mean():.1f} %")

    col_g, col_d = st.columns([1.15, 1])
    with col_g:
        st.plotly_chart(
            fig_carte_choroplethe(
                df,
                "apl_2024",
                f"Carte APL 2024 — {filtres['profession']}",
                unite_apl,
            ),
            use_container_width=True,
        )
    with col_d:
        st.plotly_chart(
            fig_confrontation_bpe_apl(df, dep_focus=filtres["departement"]),
            use_container_width=True,
        )

    _afficher_encart_interpretation(
        observation="À densité BPE comparable, plusieurs départements affichent des niveaux d'APL distincts.",
        chiffre=f"Couverture moyenne de {df['couverture_pop_pct'].mean():.1f} % de la population communale appariée.",
        interpretation="L'APL intègre la distance aux communes voisines, l'activité réelle et la structure par âge.",
        limite="Unité distincte de la BPE : ne jamais additionner ni comparer directement les deux valeurs brutes.",
    )


def afficher_relations_territoriales(df_brut: pd.DataFrame, filtres: dict) -> None:
    """Page 05 : Croisement concentration démographique et offre/accès (Axe A4)."""
    st.title("05 · Relations territoriales")
    st.caption("Question : La concentration de la population est-elle associée à l'offre ou à l'APL ?")

    df = _filtrer_base(df_brut, filtres)
    if df.empty:
        st.warning("Aucun département disponible pour ce périmètre.")
        return

    unite_apl = df["unite_apl"].iloc[0]
    c_opt1, c_opt2 = st.columns([1.5, 1])
    with c_opt1:
        axe_y_choix = st.radio(
            "Variable étudiée en ordonnée (Y) :",
            ["Densité BPE 2025 (lieux / 100 000 hab.)", f"APL DREES 2024 ({unite_apl})"],
            horizontal=True,
        )
    with c_opt2:
        afficher_droite = st.checkbox("Afficher la droite descriptive (OLS)", value=False)

    col_y = "densite_100k" if "Densité" in axe_y_choix else "apl_2024"

    stats_actuel = calculer_correlations(df, "pct_population_top_10pct_communes", col_y)
    df_sans_paris = df[df["code_dep"] != "75"]
    stats_sans_paris = calculer_correlations(df_sans_paris, "pct_population_top_10pct_communes", col_y)

    col_g, col_d = st.columns([1.45, 1])
    with col_g:
        st.plotly_chart(
            fig_nuage_territorial(
                df,
                col_x="pct_population_top_10pct_communes",
                col_y=col_y,
                label_x="Part de population dans les 10 % de communes les plus peuplées (%)",
                label_y=axe_y_choix,
                titre=f"Concentration démographique vs {axe_y_choix.split('(')[0].strip()}",
                dep_focus=filtres["departement"],
                droite_tendance=afficher_droite,
            ),
            use_container_width=True,
        )

    with col_d:
        st.subheader("Analyse de sensibilité")
        st.metric(
            f"Spearman périmètre actif (n = {stats_actuel['n']})",
            f"ρ = {stats_actuel['spearman']:.2f}",
            delta=f"Pearson r = {stats_actuel['pearson']:.2f}",
            delta_color="off",
        )
        st.metric(
            f"Spearman hors Paris (n = {stats_sans_paris['n']})",
            f"ρ = {stats_sans_paris['spearman']:.2f}",
            delta=f"{stats_sans_paris['spearman'] - stats_actuel['spearman']:+.2f} vs échantillon actif",
            delta_color="off",
        )
        st.info(
            "Le coefficient de Spearman est privilégié car il résiste mieux aux départements "
            "atypiques comme Paris."
        )

    with st.expander("Voir le tableau des départements du périmètre et exporter"):
        colonnes_affichees = [
            "code_dep",
            "nom_dep",
            "nom_region",
            "population_2023",
            "pct_population_top_10pct_communes",
            "densite_100k",
            "apl_2024",
            "statut_offre",
        ]
        st.dataframe(df[colonnes_affichees], use_container_width=True, hide_index=True)
        csv_export = df[colonnes_affichees].to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger cet extrait (CSV)",
            data=csv_export,
            file_name=f"santescope_{filtres['profession'].lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )

    _afficher_encart_interpretation(
        observation="Association statistique entre concentration communale et densité/accessibilité de soins.",
        chiffre=f"Spearman ρ = {stats_actuel['spearman']:.2f} (n = {stats_actuel['n']} départements).",
        interpretation="Permet d'évaluer si les pôles urbains concentrent davantage de lieux d'exercice.",
        limite="Association statistique transversale uniquement : aucune conclusion causale autorisée.",
    )


def afficher_methodologie() -> None:
    """Page 06 : Documentation méthodologique, sources et limites."""
    st.title("06 · Méthodologie et limites")
    st.caption("Sources officielles, formules d'indicateurs et précautions d'interprétation.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sources croisées")
        st.markdown(
            """
            - **Population de référence (Insee 2023)** : `PMUN` et `NBCOM` depuis `data/`,
              réagrégation des arrondissements de Paris, Lyon et Marseille en 3 communes
              (`34 858` communes).
            - **Base permanente des équipements (BPE Insee 2025)** : lieux d'exercice libéral
              (`D265`, `D277`, `D279`, `D281`) rapportés à 100 000 habitants.
            - **Accessibilité potentielle localisée (DREES 2024)** : moyenne départementale
              pondérée par la population des communes appariées.
            """
        )

    with col2:
        st.subheader("Précautions méthodologiques")
        st.markdown(
            """
            - **Absence de causalité** : les corrélations observées sont purement descriptives.
            - **Hétérogénéité des unités** : les lieux BPE ne sont pas additionnables aux ETP
              ou consultations standardisées de l'APL.
            - **Champ géographique** : 100 départements Insee (Mayotte non inclus dans le fichier
              fourni).
            """
        )

    st.divider()
    st.subheader("Arborescence et répartition des modules")
    st.table(
        pd.DataFrame(
            [
                {"Membre": "Personne A (Imane)", "Bloc": "Population Insee, BPE 2025 et jointures", "Fichiers du dépôt": "population.py, bpe.py, jointure.py, __init__.py"},
                {"Membre": "Personne B (Quentin)", "Bloc": "APL DREES 2024 et analyses statistiques", "Fichiers du dépôt": "src/data/apl.py, src/analysis/ (à intégrer)"},
                {"Membre": "Personne C (Deonna)", "Bloc": "Cartographie GeoJSON et graphiques Plotly", "Fichiers du dépôt": "src/viz/ (à intégrer)"},
                {"Membre": "Personne D (Alexan)", "Bloc": "Architecture Streamlit, filtres et intégration", "Fichiers du dépôt": "app.py, src/ui/pages.py, src/ui/prototype_data.py"},
            ]
        )
    )