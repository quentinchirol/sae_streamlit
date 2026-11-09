"""Partie A - Jointure entre démographie Insee et offre de soins BPE."""

from pathlib import Path
import pandas as pd

DOSSIER = Path(__file__).resolve().parent
RESULTATS = DOSSIER / "resultats"

PROFESSIONS = [
    "Médecin généraliste", "Chirurgien-dentiste",
    "Kinésithérapeute", "Infirmier"
]


def lire_donnees():
    """Lit les tables préparées par population.py et bpe.py."""
    demographie = pd.read_csv(
        RESULTATS / "demographie_departements.csv",
        dtype={"code_dep": str, "code_reg": str}
    )
    bpe = pd.read_csv(RESULTATS / "comptages_bpe.csv", dtype={"code_dep": str})
    couverture = pd.read_csv(RESULTATS / "couverture_bpe.csv", dtype={"code_dep": str})
    return demographie, bpe, couverture


def joindre_tables(demographie, bpe, couverture):
    """Joint les deux sources, puis calcule les densités pour 100 000 habitants."""
    if demographie["code_dep"].duplicated().any():
        raise ValueError("Il y a des doublons dans les départements Insee.")
    if bpe.duplicated(["code_dep", "profession"]).any():
        raise ValueError("Il y a des doublons dans les comptages BPE.")

    # Une ligne par département et par profession, même si le comptage est nul.
    tableaux = []
    for profession in PROFESSIONS:
        tableau = demographie.copy()
        tableau["profession"] = profession
        tableaux.append(tableau)
    grille = pd.concat(tableaux, ignore_index=True)

    avant = len(grille)
    resultat = grille.merge(
        bpe, on=["code_dep", "profession"], how="left", validate="one_to_one"
    )
    if len(resultat) != avant:
        raise ValueError("La jointure a modifié le nombre de lignes.")

    resultat["bpe_disponible"] = resultat["code_dep"].isin(couverture["code_dep"])

    # Ne pas confondre 'aucun lieu observé' et 'département absent de la BPE'.
    zero = resultat["bpe_disponible"] & resultat["nb_lieux"].isna()
    resultat.loc[zero, "nb_lieux"] = 0
    resultat["statut_offre"] = "non_couvert"
    resultat.loc[resultat["bpe_disponible"], "statut_offre"] = "observe"
    resultat.loc[zero, "statut_offre"] = "zero_observe"
    resultat["densite_100k"] = (
        resultat["nb_lieux"] / resultat["population_2023"] * 100000
    )

    # Codes BPE sans correspondance dans la population (ex. Mayotte).
    sans_population = bpe[~bpe["code_dep"].isin(demographie["code_dep"])]
    sans_population.to_csv(RESULTATS / "bpe_sans_population.csv", index=False)

    if resultat.duplicated(["code_dep", "profession"]).any():
        raise ValueError("La jointure contient des doublons.")

    print("Lignes avant la jointure :", avant)
    print("Lignes après la jointure :", len(resultat))
    print("Départements BPE sans population :", sans_population["code_dep"].unique().tolist())
    print("Lignes dont le département est absent de la BPE :", (~resultat["bpe_disponible"]).sum())
    return resultat


def main():
    """Crée la table finale à transmettre aux autres membres du groupe."""
    demographie, bpe, couverture = lire_donnees()
    resultat = joindre_tables(demographie, bpe, couverture)
    resultat.to_csv(RESULTATS / "analyse_departements.csv", index=False)
    print("Table finale : resultats/analyse_departements.csv")


if __name__ == "__main__":
    main()
