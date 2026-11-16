import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Palette officielle SantéScope
PALETTE = {
    "fond": "#F7FAF9",
    "texte": "#18343B",
    "petrole": "#146A78",
    "turquoise": "#42A69B",
    "bleu_pale": "#E0F1F0",
    "ambre": "#D99442",
}


@st.cache_data
def generer_donnees_fictives() -> pd.DataFrame:
    """Génère une table fictive conforme au contrat analyse_departements.parquet.

    Returns:
        pd.DataFrame: Jeu de données simulé (1 ligne par département et profession).
    """
    rng = np.random.default_rng(42)

    departements = [
        ("01", "Ain", "84", "Auvergne-Rhône-Alpes", 671289, 393, 0.06, 0.42, 0.55),
        ("06", "Alpes-Maritimes", "93", "Provence-Alpes-Côte d'Azur", 1114579, 163, 0.31, 0.78, 0.41),
        ("13", "Bouches-du-Rhône", "93", "Provence-Alpes-Côte d'Azur", 2069811, 119, 0.42, 0.76, 0.12),
        ("17", "Charente-Maritime", "75", "Nouvelle-Aquitaine", 668160, 463, 0.12, 0.48, 0.52),
        ("23", "Creuse", "75", "Nouvelle-Aquitaine", 115529, 256, 0.11, 0.39, 0.79),
        ("29", "Finistère", "53", "Bretagne", 927912, 277, 0.15, 0.51, 0.24),
        ("2A", "Corse-du-Sud", "94", "Corse", 166045, 124, 0.45, 0.74, 0.68),
        ("2B", "Haute-Corse", "94", "Corse", 187180, 236, 0.25, 0.62, 0.74),
        ("31", "Haute-Garonne", "76", "Occitanie", 1454158, 586, 0.35, 0.73, 0.64),
        ("33", "Gironde", "75", "Nouvelle-Aquitaine", 1674980, 535, 0.16, 0.58, 0.38),
        ("35", "Ille-et-Vilaine", "53", "Bretagne", 1109232, 333, 0.20, 0.54, 0.22),
        ("44", "Loire-Atlantique", "52", "Pays de la Loire", 1473156, 207, 0.22, 0.59, 0.11),
        ("48", "Lozère", "76", "Occitanie", 76503, 152, 0.16, 0.45, 0.81),
        ("59", "Nord", "32", "Hauts-de-France", 2616909, 648, 0.09, 0.52, 0.29),
        ("67", "Bas-Rhin", "44", "Grand Est", 1156963, 514, 0.25, 0.57, 0.43),
        ("69", "Rhône", "84", "Auvergne-Rhône-Alpes", 1907982, 287, 0.27, 0.69, 0.25),
        ("75", "Paris", "11", "Île-de-France", 2103778, 1, 1.00, 1.00, 0.00),
        ("79", "Deux-Sèvres", "75", "Nouvelle-Aquitaine", 375415, 256, 0.16, 0.49, 0.47),
        ("85", "Vendée", "52", "Pays de la Loire", 706343, 255, 0.08, 0.41, 0.21),
        ("86", "Vienne", "75", "Nouvelle-Aquitaine", 438688, 266, 0.21, 0.55, 0.51),
        ("92", "Hauts-de-Seine", "11", "Île-de-France", 1647435, 36, 0.07, 0.24, 0.00),
        ("93", "Seine-Saint-Denis", "11", "Île-de-France", 1681725, 40, 0.07, 0.25, 0.00),
        ("971", "Guadeloupe", "01", "Guadeloupe", 383569, 32, 0.15, 0.38, 0.03),
        ("974", "La Réunion", "04", "La Réunion", 881348, 24, 0.18, 0.41, 0.00),
    ]

    professions_cfg = {
        "Médecins généralistes": (88.0, 14.0, 3.6, 0.7, "Consultations / hab. standardisé"),
        "Infirmiers": (145.0, 32.0, 112.0, 24.0, "ETP / 100 000 hab. standardisés"),
        "Masseurs-kinésithérapeutes": (95.0, 22.0, 78.0, 18.0, "ETP / 100 000 hab. standardisés"),
        "Chirurgiens-dentistes": (62.0, 15.0, 54.0, 12.0, "ETP / 100 000 hab. standardisés"),
    }

    lignes = []
    for code_dep, nom_dep, code_reg, nom_reg, pop, nb_com, p_max, p_top10, p_petites in departements:
        for prof, (d_moy, d_std, apl_moy, apl_std, unite_apl) in professions_cfg.items():
            # Simulation d'une légère association positive avec la concentration + bruit
            effet_conc = (p_top10 - 0.5) * (d_std * 0.8)
            densite = max(15.0, round(rng.normal(d_moy + effet_conc, d_std), 1))
            nb_lieux = int(round((densite * pop) / 100_000))

            # APL corrélée partiellement à la densité mais avec des écarts territoriaux
            apl = max(0.5, round((densite / d_moy) * apl_moy + rng.normal(0, apl_std * 0.45), 2))
            couverture = round(rng.uniform(96.5, 100.0), 1)

            lignes.append(
                {
                    "code_dep": code_dep,
                    "nom_dep": nom_dep,
                    "code_reg": code_reg,
                    "nom_reg": nom_reg,
                    "population_2023": int(pop),
                    "nb_communes": int(nb_com),
                    "part_plus_grande_commune": float(p_max),
                    "part_top_10pct_communes": float(p_top10),
                    "part_petites_communes": float(p_petites),
                    "profession": prof,
                    "nb_lieux": nb_lieux,
                    "densite_100k": densite,
                    "apl_2024": apl,
                    "unite_apl": unite_apl,
                    "couverture_pop_pct": couverture,
                }
            )

    return pd.DataFrame(lignes)


def styliser_figure(fig: go.Figure, titre: str, sous_titre: str = "") -> go.Figure:
    """Applique une mise en forme sobre et cohérente à une figure Plotly."""
    titre_complet = f"<b>{titre}</b>"
    if sous_titre:
        titre_complet += f"<br><span style='font-size:12px;color:#4A656C'>{sous_titre}</span>"

    fig.update_layout(
        title={"text": titre_complet, "x": 0.01, "xanchor": "left"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": PALETTE["texte"], "family": "sans-serif"},
        margin={"t": 65, "b": 40, "l": 45, "r": 20},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E2ECEA", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#E2ECEA", zeroline=False)
    return fig


def graphique_nuage_concentration(df: pd.DataFrame, col_y: str, label_y: str) -> go.Figure:
    """Graphique central : concentration démographique (X) vs offre ou APL (Y)."""
    df_plot = df.copy()
    df_plot["Profil"] = np.where(
        df_plot["code_dep"] == "75",
        "Cas atypique (Paris)",
        "Autres départements",
    )

    fig = px.scatter(
        df_plot,
        x="part_top_10pct_communes",
        y=col_y,
        size="population_2023",
        color="Profil",
        color_discrete_map={
            "Autres départements": PALETTE["petrole"],
            "Cas atypique (Paris)": PALETTE["ambre"],
        },
        hover_name="nom_dep",
        hover_data={
            "code_dep": True,
            "nom_reg": True,
            "population_2023": ":,",
            "part_top_10pct_communes": ":.1%",
            col_y: ":.2f",
            "Profil": False,
        },
        labels={
            "part_top_10pct_communes": "Part de population dans les 10 % de communes les plus peuplées",
            col_y: label_y,
        },
        size_max=34,
    )
    fig.update_xaxes(tickformat=".0%")
    return styliser_figure(
        fig,
        f"Concentration démographique et {label_y.split('(')[0].strip().lower()}",
        "Sources simulées : Insee 2023, BPE 2025, DREES-APL 2024 • Taille = population",
    )


def graphique_classement_departements(df: pd.DataFrame, col_val: str, label_val: str) -> go.Figure:
    """Classement horizontal des départements (Top 6 et Flop 6)."""
    df_trie = df.sort_values(col_val, ascending=True)
    if len(df_trie) > 12:
        df_sel = pd.concat([df_trie.head(6), df_trie.tail(6)]).drop_duplicates("code_dep")
    else:
        df_sel = df_trie

    mediane = df[col_val].median()
    df_sel = df_sel.copy()
    df_sel["Position"] = np.where(
        df_sel[col_val] >= mediane,
        "Au-dessus de la médiane",
        "En dessous de la médiane",
    )
    df_sel["etiquette"] = df_sel["nom_dep"] + " (" + df_sel["code_dep"] + ")"

    fig = px.bar(
        df_sel,
        x=col_val,
        y="etiquette",
        orientation="h",
        color="Position",
        color_discrete_map={
            "Au-dessus de la médiane": PALETTE["petrole"],
            "En dessous de la médiane": PALETTE["turquoise"],
        },
        labels={col_val: label_val, "etiquette": ""},
        text_auto=".1f",
    )
    fig.add_vline(x=mediane, line_dash="dash", line_color=PALETTE["ambre"])
    return styliser_figure(
        fig,
        "Écarts entre départements (extrêmes du périmètre)",
        f"Ligne pointillée : médiane du périmètre ({mediane:.1f})",
    )


def graphique_bpe_vs_apl(df: pd.DataFrame) -> go.Figure:
    """Confrontation BPE (X) vs APL (Y) sur deux axes distincts."""
    unite_apl = df["unite_apl"].iloc[0] if not df.empty else "Unité APL"
    fig = px.scatter(
        df,
        x="densite_100k",
        y="apl_2024",
        color="nom_reg",
        hover_name="nom_dep",
        labels={
            "densite_100k": "Densité BPE 2025 (lieux / 100 000 hab.)",
            "apl_2024": f"APL DREES 2024 ({unite_apl})",
            "nom_reg": "Région",
        },
        color_discrete_sequence=[
            PALETTE["petrole"],
            PALETTE["turquoise"],
            PALETTE["ambre"],
            "#2B4C59",
            "#68B0AB",
            "#8FC0A9",
        ],
    )
    return styliser_figure(
        fig,
        "Densité brute (BPE) vs accessibilité potentielle (APL)",
        "Chaque axe conserve son unité propre • Permet de repérer les cas divergents",
    )


def graphique_distribution_professions(df_tout: pd.DataFrame, region: str) -> go.Figure:
    """Boîtes à moustaches des densités BPE par profession sur la région choisie."""
    df_sub = df_tout if region == "Toutes les régions" else df_tout[df_tout["nom_reg"] == region]
    fig = px.box(
        df_sub,
        x="profession",
        y="densite_100k",
        points="all",
        hover_name="nom_dep",
        color_discrete_sequence=[PALETTE["petrole"]],
        labels={
            "profession": "",
            "densite_100k": "Densité BPE (lieux / 100 000 hab.)",
        },
    )
    return styliser_figure(
        fig,
        "Dispersion départementale de l'offre par profession",
        f"Périmètre : {region} • BPE 2025 / Population Insee 2023",
    )


def initialiser_etat() -> None:
    """Initialise les filtres appliqués dans st.session_state."""
    if "filtres" not in st.session_state:
        st.session_state["filtres"] = {
            "region": "Toutes les régions",
            "profession": "Médecins généralistes",
            "indicateur": "Densité BPE (lieux / 100 000 hab.)",
            "exclure_paris": False,
        }


def main() -> None:
    """Point d'entrée de la maquette UI SantéScope."""
    st.set_page_config(page_title="SantéScope — Prototype UI", page_icon="🩺", layout="wide")
    initialiser_etat()

    # Injection CSS légère pour les cartes KPI et encarts d'interprétation
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
            margin-top: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    df_brut = generer_donnees_fictives()
    regions = ["Toutes les régions"] + sorted(df_brut["nom_reg"].unique().tolist())
    professions = sorted(df_brut["profession"].unique().tolist())
    indicateurs = [
        "Densité BPE (lieux / 100 000 hab.)",
        "Accessibilité APL DREES 2024",
    ]

    # --- BARRE LATÉRALE : FORMULAIRE DE FILTRES ---
    with st.sidebar:
        st.title("🩺 SantéScope")
        st.caption("Maquette d'architecture UI • BUT 3 VCOD")

        with st.form("formulaire_filtres"):
            st.subheader("Périmètre d'analyse")
            choix_reg = st.selectbox(
                "Région",
                regions,
                index=regions.index(st.session_state["filtres"]["region"]),
            )
            choix_prof = st.selectbox(
                "Profession de santé",
                professions,
                index=professions.index(st.session_state["filtres"]["profession"]),
            )
            choix_ind = st.radio(
                "Indicateur principal",
                indicateurs,
                index=indicateurs.index(st.session_state["filtres"]["indicateur"]),
            )
            choix_paris = st.checkbox(
                "Exclure Paris (analyse de sensibilité)",
                value=st.session_state["filtres"]["exclure_paris"],
            )

            col_b1, col_b2 = st.columns(2)
            soumis = col_b1.form_submit_button("Appliquer", use_container_width=True)
            reinit = col_b2.form_submit_button("Réinitialiser", use_container_width=True)

        if soumis:
            st.session_state["filtres"] = {
                "region": choix_reg,
                "profession": choix_prof,
                "indicateur": choix_ind,
                "exclure_paris": choix_paris,
            }
            st.rerun()

        if reinit:
            st.session_state["filtres"] = {
                "region": "Toutes les régions",
                "profession": "Médecins généralistes",
                "indicateur": "Densité BPE (lieux / 100 000 hab.)",
                "exclure_paris": False,
            }
            st.rerun()

    # --- APPLICATION DES FILTRES DEPUIS SESSION_STATE ---
    f = st.session_state["filtres"]
    df_filtre = df_brut[df_brut["profession"] == f["profession"]].copy()

    if f["region"] != "Toutes les régions":
        df_filtre = df_filtre[df_filtre["nom_reg"] == f["region"]]
    if f["exclure_paris"]:
        df_filtre = df_filtre[df_filtre["code_dep"] != "75"]

    if df_filtre.empty:
        st.warning("Aucun département ne correspond aux filtres sélectionnés.")
        st.stop()

    # --- EN-TÊTE ET BANDEAU KPI ---
    st.header(f"Offre et accessibilité : {f['profession']}")
    st.caption(
        f"Périmètre actif : **{f['region']}** ({len(df_filtre)} départements) • "
        f"Paris exclu : **{'Oui' if f['exclure_paris'] else 'Non'}**"
    )

    unite_apl_courante = df_filtre["unite_apl"].iloc[0]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Population couverte (Insee 2023)", f"{df_filtre['population_2023'].sum():,}".replace(",", " "))
    k2.metric("Lieux d'exercice (BPE 2025)", f"{df_filtre['nb_lieux'].sum():,}".replace(",", " "))
    k3.metric("Densité BPE médiane", f"{df_filtre['densite_100k'].median():.1f} / 100k")
    k4.metric("APL médiane (DREES 2024)", f"{df_filtre['apl_2024'].median():.2f}", help=unite_apl_courante)

    st.divider()

    # --- GRILLE PRINCIPALE (2 COLONNES) ---
    col_val = "densite_100k" if "Densité" in f["indicateur"] else "apl_2024"
    label_val = (
        "Densité BPE (lieux / 100 000 hab.)"
        if col_val == "densite_100k"
        else f"APL 2024 ({unite_apl_courante})"
    )

    col_gauche, col_droite = st.columns([1.35, 1])

    with col_gauche:
        st.plotly_chart(
            graphique_nuage_concentration(df_filtre, col_val, label_val),
            use_container_width=True,
        )

    with col_droite:
        st.plotly_chart(
            graphique_classement_departements(df_filtre, col_val, label_val),
            use_container_width=True,
        )

    # --- GRILLE SECONDAIRE (COMPARAISON BPE/APL & PROFESSIONS) ---
    onglet_apl, onglet_prof, onglet_donnees = st.tabs(
        [
            "Confrontation BPE / APL",
            "Comparaison inter-professions",
            "Aperçu des données filtrées",
        ]
    )

    with onglet_apl:
        c1, c2 = st.columns([1.4, 1])
        with c1:
            st.plotly_chart(graphique_bpe_vs_apl(df_filtre), use_container_width=True)
        with c2:
            st.markdown(
                """
                <div class="encart-constat">
                <b>Structure d'interprétation (à remplir avec les résultats réels)</b><br><br>
                <b>1. Observation :</b> comparer l'alignement entre densité de lieux (X) et accessibilité potentielle (Y).<br>
                <b>2. Chiffre :</b> indiquer le coefficient de Spearman et la couverture démographique.<br>
                <b>3. Interprétation :</b> expliquer pourquoi une forte densité brute ne garantit pas une APL élevée (activité, structure par âge).<br>
                <b>4. Limite :</b> données simulées ici ; aucune conclusion causale possible sur données transversales.
                </div>
                """,
                unsafe_allow_html=True,
            )

    with onglet_prof:
        st.plotly_chart(
            graphique_distribution_professions(df_brut, f["region"]),
            use_container_width=True,
        )

    with onglet_donnees:
        st.dataframe(df_filtre, use_container_width=True, hide_index=True)
        csv = df_filtre.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger l'extrait filtré (CSV)",
            data=csv,
            file_name=f"santescope_{f['profession'].lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()