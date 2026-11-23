
"""Lance les trois traitements de la partie A dans le bon ordre."""

from pathlib import Path
import subprocess
import sys

import traitement

DOSSIER_RESULTATS = Path(__file__).resolve().parent / "resultats"
FICHIERS_RESULTATS = (
    "analyse_departements.csv",
    "bpe_sans_population.csv",
    "communes_preparees.csv",
    "controle_population.csv",
    "demographie_departements.csv",
    "comptages_bpe.csv",
    "couverture_bpe.csv",
)


def main():
    """Prépare les données si nécessaire, puis lance le dashboard."""
    manquants = [
        nom for nom in FICHIERS_RESULTATS
        if not (DOSSIER_RESULTATS / nom).is_file()
    ]
    if manquants:
        print("Préparation des données : fichiers de résultats manquants.")
        print("Fichiers à produire :", ", ".join(manquants))
        traitement.main()
    else:
        print("Les fichiers de résultats sont déjà présents : préparation ignorée.")

    print("\nDonnées prêtes.")
    dashboard = Path(__file__).resolve().with_name("dashboard.py")
    print("\nLancement du dashboard SantéScope")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(dashboard)],
        check=True,
    )


if __name__ == "__main__":
    main()
