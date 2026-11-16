"""Point d'entrée de l'application Streamlit SantéScope (Personne D)."""

from __future__ import annotations

import streamlit as st

from src.ui.pages import (
    afficher_accessibilite_apl,
    afficher_methodologie,
    afficher_offre_soins,
    afficher_population,
    afficher_relations_territoriales,
    afficher_synthese_statique,
    afficher_vue_ensemble,
)
from src.ui.prototype_data import PALETTE, charger_donnees_ui


def injecter_style_global() -> None:
    """Applique les ajustements CSS pour les cartes KPI et les encarts de lecture."""
    st.markdown(
        f"""
        <style>
        div[data-testid="stMetric"] {{
            background-color: {PALETTE["bleu_pale"]};
            border-left: 4px solid {PALETTE["petrole"]};
            padding: 12px 16px;
            border-radius: 6px;
        }}
        .encart-constat {{
            background-color: #FFFFFF;
            border: 1px solid #D3E4E2;
            border-left: 4px solid {PALETTE["turquoise"]};
            padding: 14px 18px;
            border-radius: 6px;
            line-height: 1.5;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialiser_session_state() -> None:
    """Initialise les paramètres de filtrage persistants dans st.session_state."""
    if "filtres_appliques" not in st.session_state:
        st.session_state["filtres_appliques"] = {
            "region": "Toutes les régions",
            "departement": "Tous",
            "profession": "Médecin généraliste",
            "exclure_paris": False,
        }


def afficher_barre_laterale(df_brut, info_source: str, url_page_active: str) -> None:
    """Affiche le formulaire de filtres groupés (st.form) dans la barre latérale."""
    with st.sidebar:
        st.markdown("## 🩺 SantéScope")
        st.caption("Population, territoires et offre de soins")
        st.info(f"Données actives : {info_source}", icon="📂")

        if url_page_active == "synthese-analyses":
            st.warning(
                "Onglet statique : les graphiques sont figés sur les 100 départements "
                "et ignorent les filtres.",
                icon="🔒",
            )
            return

        if url_page_active == "methodologie":
            st.caption("Aucun filtre n'est requis sur la page Méthodologie.")
            return

        f = st.session_state["filtres_appliques"]
        regions = ["Toutes les régions"] + sorted(df_brut["nom_region"].dropna().unique().tolist())
        professions = sorted(df_brut["profession"].dropna().unique().tolist())

        reg_defaut = f["region"] if f["region"] in regions else "Toutes les régions"
        prof_defaut = f["profession"] if f["profession"] in professions else professions[0]

        deps_uniques = (
            df_brut[["code_dep", "nom_dep"]]
            .drop_duplicates()
            .sort_values("code_dep")
        )
        options_dep = ["Tous"] + [
            f"{row.code_dep} - {row.nom_dep}" for row in deps_uniques.itertuples()
        ]
        index_dep_actuel = next(
            (i for i, opt in enumerate(options_dep) if opt.startswith(f"{f['departement']} -")),
            0,
        )

        with st.form("form_filtres_globaux"):
            st.subheader("Filtres d'analyse")
            sel_reg = st.selectbox("Région", regions, index=regions.index(reg_defaut))
            sel_dep_label = st.selectbox("Cibler un département", options_dep, index=index_dep_actuel)
            sel_prof = st.selectbox("Profession", professions, index=professions.index(prof_defaut))
            sel_paris = st.checkbox("Exclure Paris (75)", value=f["exclure_paris"])

            c1, c2 = st.columns(2)
            btn_appliquer = c1.form_submit_button("Appliquer", use_container_width=True)
            btn_reset = c2.form_submit_button("Réinitialiser", use_container_width=True)

        if btn_appliquer:
            code_dep_choisi = "Tous" if sel_dep_label == "Tous" else sel_dep_label.split(" - ")[0]
            st.session_state["filtres_appliques"] = {
                "region": sel_reg,
                "departement": code_dep_choisi,
                "profession": sel_prof,
                "exclure_paris": sel_paris,
            }
            st.rerun()

        if btn_reset:
            st.session_state["filtres_appliques"] = {
                "region": "Toutes les régions",
                "departement": "Tous",
                "profession": professions[0],
                "exclure_paris": False,
            }
            st.rerun()


def main() -> None:
    """Configure l'application multi-pages et exécute la page active."""
    st.set_page_config(page_title="SantéScope", page_icon="🩺", layout="wide")
    injecter_style_global()
    initialiser_session_state()

    df_brut, info_source = charger_donnees_ui()
    filtres = st.session_state["filtres_appliques"]

    pages = [
        st.Page(
            lambda: afficher_vue_ensemble(df_brut, filtres, info_source),
            title="01 · Vue d'ensemble",
            icon="🧭",
            url_path="vue-ensemble",
        ),
        st.Page(
            lambda: afficher_population(df_brut, filtres),
            title="02 · Population",
            icon="🏘️",
            url_path="population",
        ),
        st.Page(
            lambda: afficher_offre_soins(df_brut, filtres),
            title="03 · Offre de soins",
            icon="🩺",
            url_path="offre-soins",
        ),
        st.Page(
            lambda: afficher_accessibilite_apl(df_brut, filtres),
            title="04 · Accessibilité (APL)",
            icon="📍",
            url_path="accessibilite-apl",
        ),
        st.Page(
            lambda: afficher_relations_territoriales(df_brut, filtres),
            title="05 · Relations territoriales",
            icon="📈",
            url_path="relations-territoriales",
        ),
        st.Page(
            lambda: afficher_synthese_statique(df_brut),
            title="06 · Synthèse & Analyses",
            icon="📊",
            url_path="synthese-analyses",
        ),
        st.Page(
            afficher_methodologie,
            title="07 · Méthodologie",
            icon="📚",
            url_path="methodologie",
        ),
    ]

    page_active = st.navigation(pages)
    afficher_barre_laterale(
        df_brut,
        info_source=info_source,
        url_page_active=page_active.url_path,
    )
    page_active.run()


if __name__ == "__main__":
    main()