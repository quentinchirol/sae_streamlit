"""Partie A - Comptage des lieux de soins dans la BPE 2025."""

from pathlib import Path
import pandas as pd

DOSSIER = Path(__file__).resolve().parent
FICHIER_BPE = DOSSIER / "donnees" / "BPE25.parquet"
RESULTATS = DOSSIER / "resultats"

# Codes des quatre professions de santé retenues (nomenclature BPE 2025).
PROFESSIONS = {
    "D265": "Médecin généraliste",
    "D277": "Chirurgien-dentiste",
    "D279": "Kinésithérapeute",
    "D281": "Infirmier"
}


def lire_bpe():
    """Lit uniquement le département et le type d'équipement du Parquet."""
    if not FICHIER_BPE.exists():
        raise FileNotFoundError(
            "BPE25.parquet est absent. Place le fichier dans le dossier donnees/."
        )
    return pd.read_parquet(FICHIER_BPE, columns=["DEP", "TYPEQU"])


def compter_lieux(bpe):
    """Compte les lieux d'exercice de chaque profession par département."""
    bpe = bpe.copy()
    bpe["DEP"] = bpe["DEP"].astype("string").str.strip().str.upper().str.zfill(2)
    bpe["TYPEQU"] = bpe["TYPEQU"].astype("string").str.strip().str.upper()

    # Une ligne de la BPE correspond à un équipement ou lieu d'exercice.
    sante = bpe[bpe["TYPEQU"].isin(PROFESSIONS)].copy()
    if sante.empty:
        raise ValueError("Aucun code de profession attendu dans ce fichier BPE.")
    if sante["DEP"].isna().any():
        raise ValueError("Des lieux de soins n'ont pas de département.")

    codes_absents = set(PROFESSIONS) - set(sante["TYPEQU"])
    if codes_absents:
        raise ValueError(f"Codes BPE absents : {sorted(codes_absents)}")

    sante["profession"] = sante["TYPEQU"].map(PROFESSIONS)
    offre = sante.groupby(["DEP", "profession"]).size().reset_index(name="nb_lieux")
    offre = offre.rename(columns={"DEP": "code_dep"})

    if offre["nb_lieux"].sum() != len(sante):
        raise ValueError("Le nombre de lieux a changé pendant le comptage.")

    # On conserve aussi les départements présents dans la BPE complète.
    couverture = bpe[["DEP"]].dropna().drop_duplicates()
    couverture = couverture.rename(columns={"DEP": "code_dep"})
    return offre, couverture, len(sante)


def main():
    """Enregistre les comptages BPE et la liste des départements couverts."""
    RESULTATS.mkdir(exist_ok=True)
    bpe = lire_bpe()
    offre, couverture, nombre = compter_lieux(bpe)
    offre.to_csv(RESULTATS / "comptages_bpe.csv", index=False)
    couverture.to_csv(RESULTATS / "couverture_bpe.csv", index=False)
    print("BPE : traitement terminé")
    print("Lieux d'exercice retenus :", nombre)
    print("Départements présents dans la BPE :", len(couverture))
    print("Fichiers : resultats/comptages_bpe.csv et couverture_bpe.csv")


if __name__ == "__main__":
    main()
