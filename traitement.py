"""Préparation complète des données Insee 2023 et BPE 2025."""

from pathlib import Path
import math
import shutil
from urllib.request import urlopen

import pandas as pd

DOSSIER = Path(__file__).resolve().parent
DONNEES = DOSSIER / "data"
RESULTATS = DOSSIER / "resultats"
FICHIER_BPE = DONNEES / "BPE25.parquet"
URL_BPE = "https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.parquet"
PROFESSIONS_BPE = {
    "D265": "Médecin généraliste",
    "D277": "Chirurgien-dentiste",
    "D279": "Kinésithérapeute",
    "D281": "Infirmier",
}
PROFESSIONS = list(PROFESSIONS_BPE.values())


def lire_donnees_population():
    """Lit les tables Insee des départements et des communes."""
    departements = pd.read_csv(
        DONNEES / "donnees_departements.csv",
        sep=";",
        dtype={"DEP": str, "REG": str},
    )
    communes = pd.read_csv(
        DONNEES / "donnees_communes.csv",
        sep=";",
        dtype={"DEP": str, "COM": str},
    )
    return departements, communes


def preparer_communes(communes):
    """Regroupe les arrondissements de Paris, Lyon et Marseille."""
    communes = communes[["DEP", "COM", "Commune", "PMUN"]].copy()

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
    return communes.rename(
        columns={
            "DEP": "code_dep",
            "COM": "code_com",
            "Commune": "nom_commune",
            "PMUN": "population_commune",
        }
    )


def calculer_indicateurs_population(communes):
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
        lignes.append(
            {
                "code_dep": code_dep,
                "nb_communes_calcule": nb_communes,
                "population_calculee": population,
                "pct_plus_grande_commune": populations.iloc[0] / population * 100,
                "pct_population_top_10pct_communes": populations.head(nb_top).sum() / population * 100,
                "pct_petites_communes": len(petites) / nb_communes * 100,
                "pct_population_petites_communes": petites.sum() / population * 100,
            }
        )
    return pd.DataFrame(lignes)


def joindre_population(departements, indicateurs):
    """Joint les indicateurs aux départements et contrôle les résultats."""
    departements = departements[
        ["DEP", "Département", "REG", "Région", "PMUN", "NBCOM"]
    ].rename(
        columns={
            "DEP": "code_dep",
            "Département": "nom_dep",
            "REG": "code_reg",
            "Région": "nom_region",
            "PMUN": "population_2023",
            "NBCOM": "nb_communes",
        }
    )
    if departements["code_dep"].duplicated().any():
        raise ValueError("Un département apparaît plusieurs fois dans le fichier Insee.")

    resultat = departements.merge(
        indicateurs,
        on="code_dep",
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    controles = resultat[
        [
            "code_dep",
            "nom_dep",
            "population_2023",
            "population_calculee",
            "nb_communes",
            "nb_communes_calcule",
            "_merge",
        ]
    ].copy()
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
    return resultat.drop(
        columns=["_merge", "population_calculee", "nb_communes_calcule"]
    )


def traiter_population():
    """Calcule et enregistre les tables démographiques préparées."""
    departements, communes = lire_donnees_population()
    communes = preparer_communes(communes)
    indicateurs = calculer_indicateurs_population(communes)
    resultat = joindre_population(departements, indicateurs)
    communes.to_csv(RESULTATS / "communes_preparees.csv", index=False)
    resultat.to_csv(RESULTATS / "demographie_departements.csv", index=False)

    print("Population : traitement terminé")
    print("Départements :", len(resultat))
    print("Communes :", len(communes))
    print("Habitants :", int(resultat["population_2023"].sum()))
    print("Contrôle : voir resultats/controle_population.csv")


def est_parquet(chemin):
    """Vérifie les signatures de début et de fin d'un fichier Parquet."""
    if not chemin.exists() or chemin.stat().st_size < 8:
        return False
    with chemin.open("rb") as fichier:
        if fichier.read(4) != b"PAR1":
            return False
        fichier.seek(-4, 2)
        return fichier.read(4) == b"PAR1"


def telecharger_bpe():
    """Télécharge la BPE Insee dans le dossier data/ après validation."""
    DONNEES.mkdir(parents=True, exist_ok=True)
    temporaire = FICHIER_BPE.with_suffix(".parquet.tmp")
    try:
        with urlopen(URL_BPE, timeout=60) as reponse, temporaire.open("wb") as sortie:
            shutil.copyfileobj(reponse, sortie)
        if not est_parquet(temporaire):
            raise ValueError("La réponse téléchargée n'est pas un fichier Parquet valide.")
        temporaire.replace(FICHIER_BPE)
    except Exception as erreur:
        temporaire.unlink(missing_ok=True)
        raise RuntimeError(f"Impossible de télécharger la BPE depuis {URL_BPE}.") from erreur


def lire_bpe():
    """Lit uniquement le département et le type d'équipement du Parquet."""
    if not est_parquet(FICHIER_BPE):
        print("Fichier BPE absent ou invalide : téléchargement depuis l'Insee...")
        telecharger_bpe()
    return pd.read_parquet(FICHIER_BPE, columns=["DEP", "TYPEQU"])


def compter_lieux_bpe(bpe):
    """Compte les lieux d'exercice de chaque profession par département."""
    bpe = bpe.copy()
    bpe["DEP"] = bpe["DEP"].astype("string").str.strip().str.upper().str.zfill(2)
    bpe["TYPEQU"] = bpe["TYPEQU"].astype("string").str.strip().str.upper()
    sante = bpe[bpe["TYPEQU"].isin(PROFESSIONS_BPE)].copy()
    if sante.empty:
        raise ValueError("Aucun code de profession attendu dans ce fichier BPE.")
    if sante["DEP"].isna().any():
        raise ValueError("Des lieux de soins n'ont pas de département.")

    codes_absents = set(PROFESSIONS_BPE) - set(sante["TYPEQU"])
    if codes_absents:
        raise ValueError(f"Codes BPE absents : {sorted(codes_absents)}")

    sante["profession"] = sante["TYPEQU"].map(PROFESSIONS_BPE)
    offre = sante.groupby(["DEP", "profession"]).size().reset_index(name="nb_lieux")
    offre = offre.rename(columns={"DEP": "code_dep"})
    if offre["nb_lieux"].sum() != len(sante):
        raise ValueError("Le nombre de lieux a changé pendant le comptage.")

    couverture = bpe[["DEP"]].dropna().drop_duplicates()
    couverture = couverture.rename(columns={"DEP": "code_dep"})
    return offre, couverture, len(sante)


def traiter_bpe():
    """Calcule et enregistre les comptages BPE et la couverture territoriale."""
    donnees_bpe = lire_bpe()
    offre, couverture, nombre = compter_lieux_bpe(donnees_bpe)
    offre.to_csv(RESULTATS / "comptages_bpe.csv", index=False)
    couverture.to_csv(RESULTATS / "couverture_bpe.csv", index=False)
    print("BPE : traitement terminé")
    print("Lieux d'exercice retenus :", nombre)
    print("Départements présents dans la BPE :", len(couverture))
    print("Fichiers : resultats/comptages_bpe.csv et couverture_bpe.csv")


def lire_donnees_jointure():
    """Lit les tables préparées par les étapes population et BPE."""
    demographie = pd.read_csv(
        RESULTATS / "demographie_departements.csv",
        dtype={"code_dep": str, "code_reg": str},
    )
    bpe = pd.read_csv(RESULTATS / "comptages_bpe.csv", dtype={"code_dep": str})
    couverture = pd.read_csv(RESULTATS / "couverture_bpe.csv", dtype={"code_dep": str})
    return demographie, bpe, couverture


def joindre_tables(demographie, bpe, couverture):
    """Joint démographie et BPE, puis calcule les densités pour 100 000 habitants."""
    if demographie["code_dep"].duplicated().any():
        raise ValueError("Il y a des doublons dans les départements Insee.")
    if bpe.duplicated(["code_dep", "profession"]).any():
        raise ValueError("Il y a des doublons dans les comptages BPE.")

    tableaux = []
    for profession in PROFESSIONS:
        tableau = demographie.copy()
        tableau["profession"] = profession
        tableaux.append(tableau)
    grille = pd.concat(tableaux, ignore_index=True)
    resultat = grille.merge(
        bpe,
        on=["code_dep", "profession"],
        how="left",
        validate="one_to_one",
    )
    if len(resultat) != len(grille):
        raise ValueError("La jointure a modifié le nombre de lignes.")

    resultat["bpe_disponible"] = resultat["code_dep"].isin(couverture["code_dep"])
    zero = resultat["bpe_disponible"] & resultat["nb_lieux"].isna()
    resultat.loc[zero, "nb_lieux"] = 0
    resultat["statut_offre"] = "non_couvert"
    resultat.loc[resultat["bpe_disponible"], "statut_offre"] = "observe"
    resultat.loc[zero, "statut_offre"] = "zero_observe"
    resultat["densite_100k"] = (
        resultat["nb_lieux"] / resultat["population_2023"] * 100000
    )

    sans_population = bpe[~bpe["code_dep"].isin(demographie["code_dep"])]
    sans_population.to_csv(RESULTATS / "bpe_sans_population.csv", index=False)
    if resultat.duplicated(["code_dep", "profession"]).any():
        raise ValueError("La jointure contient des doublons.")

    print("Lignes avant la jointure :", len(grille))
    print("Lignes après la jointure :", len(resultat))
    print("Départements BPE sans population :", sans_population["code_dep"].unique().tolist())
    print("Lignes dont le département est absent de la BPE :", (~resultat["bpe_disponible"]).sum())
    return resultat


def traiter_jointure():
    """Crée la table finale à transmettre aux autres membres du groupe."""
    demographie, bpe, couverture = lire_donnees_jointure()
    resultat = joindre_tables(demographie, bpe, couverture)
    resultat.to_csv(RESULTATS / "analyse_departements.csv", index=False)
    print("Table finale : resultats/analyse_departements.csv")


def main():
    """Exécute le pipeline complet dans l'ordre requis."""
    RESULTATS.mkdir(parents=True, exist_ok=True)
    print("1/3 - Préparation de la population")
    traiter_population()
    print("\n2/3 - Comptage des lieux de soins BPE")
    traiter_bpe()
    print("\n3/3 - Jointure et calcul des densités")
    traiter_jointure()
    print("\nTraitement des données terminé.")


if __name__ == "__main__":
    main()
