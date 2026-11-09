"""Partie A - Préparation des populations Insee 2023."""

from pathlib import Path
import math
import pandas as pd

DOSSIER = Path(__file__).resolve().parent
DONNEES = DOSSIER / "donnees"
RESULTATS = DOSSIER / "resultats"


def lire_donnees():
    """Lit les deux CSV Insee et renvoie les départements et les communes."""
    departements = pd.read_csv(
        DONNEES / "donnees_departements.csv",
        sep=";",
        dtype={"DEP": str, "REG": str}
    )
    communes = pd.read_csv(
        DONNEES / "donnees_communes.csv",
        sep=";",
        dtype={"DEP": str, "COM": str}
    )
    return departements, communes


def preparer_communes(communes):
    """Regroupe les arrondissements de Paris, Lyon et Marseille."""
    communes = communes[["DEP", "COM", "Commune", "PMUN"]].copy()

    # Les fichiers Insee détaillent ces villes par arrondissement.
    # On les regroupe pour compter chaque commune une seule fois.
    for numero in range(1, 21):
        communes.loc[communes["COM"] == f"751{numero:02d}", "COM"] = "75056"
    for numero in range(1, 10):
        communes.loc[communes["COM"] == f"6938{numero}", "COM"] = "69123"
    for numero in range(1, 17):
        communes.loc[communes["COM"] == f"132{numero:02d}", "COM"] = "13055"

    communes.loc[communes["COM"] == "75056", "Commune"] = "Paris"
    communes.loc[communes["COM"] == "69123", "Commune"] = "Lyon"
    communes.loc[communes["COM"] == "13055", "Commune"] = "Marseille"

    communes = communes.groupby(
        ["DEP", "COM", "Commune"], as_index=False
    )["PMUN"].sum()

    return communes.rename(columns={
        "DEP": "code_dep",
        "COM": "code_com",
        "Commune": "nom_commune",
        "PMUN": "population_commune"
    })


def calculer_indicateurs(communes):
    """Calcule les indicateurs de concentration pour chaque département."""
    lignes = []

    for code_dep, groupe in communes.groupby("code_dep"):
        populations = groupe["population_commune"].sort_values(ascending=False)
        population = populations.sum()
        nb_communes = len(populations)

        if population <= 0:
            raise ValueError(f"Population nulle pour le département {code_dep}")

        nb_top = max(1, math.ceil(nb_communes * 0.10))
        petites = populations[populations < 500]

        lignes.append({
            "code_dep": code_dep,
            "nb_communes_calcule": nb_communes,
            "population_calculee": population,
            "pct_plus_grande_commune": populations.iloc[0] / population * 100,
            "pct_population_top_10pct_communes": populations.head(nb_top).sum() / population * 100,
            "pct_petites_communes": len(petites) / nb_communes * 100,
            "pct_population_petites_communes": petites.sum() / population * 100
        })

    return pd.DataFrame(lignes)


def faire_jointure(departements, indicateurs):
    """Joint les indicateurs aux départements et contrôle les résultats."""
    departements = departements[[
        "DEP", "Département", "REG", "Région", "PMUN", "NBCOM"
    ]].rename(columns={
        "DEP": "code_dep",
        "Département": "nom_dep",
        "REG": "code_reg",
        "Région": "nom_region",
        "PMUN": "population_2023",
        "NBCOM": "nb_communes"
    })

    if departements["code_dep"].duplicated().any():
        raise ValueError("Un département apparaît plusieurs fois dans le fichier Insee.")

    resultat = departements.merge(
        indicateurs, on="code_dep", how="left",
        validate="one_to_one", indicator=True
    )

    # Contrôle ligne par ligne : population, communes et correspondance.
    controles = resultat[[
        "code_dep", "nom_dep", "population_2023", "population_calculee",
        "nb_communes", "nb_communes_calcule", "_merge"
    ]].copy()
    controles["ecart_population"] = (
        controles["population_2023"] - controles["population_calculee"]
    )
    controles["ecart_communes"] = (
        controles["nb_communes"] - controles["nb_communes_calcule"]
    )
    controles.to_csv(RESULTATS / "controle_population.csv", index=False)

    if (resultat["_merge"] != "both").any():
        raise ValueError("Certains départements ne sont pas dans le fichier communes.")
    if (controles["ecart_population"] != 0).any():
        raise ValueError("Les populations communales et départementales diffèrent.")
    if (controles["ecart_communes"] != 0).any():
        raise ValueError("Les nombres de communes diffèrent.")

    return resultat.drop(columns=["_merge", "population_calculee", "nb_communes_calcule"])


def main():
    """Lance le traitement et enregistre les trois CSV préparés."""
    RESULTATS.mkdir(exist_ok=True)
    departements, communes = lire_donnees()
    communes = preparer_communes(communes)
    indicateurs = calculer_indicateurs(communes)
    resultat = faire_jointure(departements, indicateurs)

    communes.to_csv(RESULTATS / "communes_preparees.csv", index=False)
    resultat.to_csv(RESULTATS / "demographie_departements.csv", index=False)

    print("Population : traitement terminé")
    print("Départements :", len(resultat))
    print("Communes :", len(communes))
    print("Habitants :", int(resultat["population_2023"].sum()))
    print("Contrôle : voir resultats/controle_population.csv")


if __name__ == "__main__":
    main()
