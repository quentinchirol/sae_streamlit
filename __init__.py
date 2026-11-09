
"""Lance les trois traitements de la partie A dans le bon ordre."""

import population
import bpe
import jointure


def main():
    """Prépare la population, la BPE, puis réalise la jointure."""
    print("1/3 - Préparation de la population")
    population.main()

    print("\n2/3 - Comptage des lieux de soins BPE")
    bpe.main()

    print("\n3/3 - Jointure et calcul des densités")
    jointure.main()

    print("\nPartie A terminée !")


if __name__ == "__main__":
    main()
