# SantéScope — Offre de soins par département en France

**Projet Streamlit · BUT 3 Science des Données · Parcours VCOD · 2026**

> **État du projet : en cours de développement.** Ce README décrit le périmètre retenu, les données actuellement disponibles, l'organisation prévue et les étapes à réaliser. Les parties non encore implémentées sont indiquées comme telles.

## 1. Présentation du projet

L'offre de soins n'est pas répartie de manière uniforme en France : certains départements disposent de davantage de lieux d'exercice de professionnels de santé que d'autres. Ces différences peuvent être analysées à l'aide de données publiques, à condition de tenir compte de la population des territoires comparés.

Notre projet consiste à développer une **application interactive avec Python et Streamlit** pour étudier cette répartition à l'échelle départementale.

### Problématique

**Dans quelle mesure l'offre de soins libérale varie-t-elle selon les départements français, et comment identifier des territoires présentant des profils d'offre similaires ?**

L'objectif est de :

- mesurer le nombre de lieux d'exercice par département et par profession ;
- calculer des densités pour **100 000 habitants** ;
- comparer les départements et les professions ;
- représenter les résultats sur une carte ;
- proposer, si les données le permettent, une typologie descriptive des territoires ;
- présenter des conclusions **et les limites de l'analyse**.

Le projet s'inscrit dans le cas proposé par l'enseignant autour d'un éventuel *zonier* en assurance santé. **Notre typologie, si elle est construite, ne constitue pas un tarif d'assurance** : les seules données d'offre de soins ne suffisent pas à estimer les dépenses ou les dépassements d'honoraires.

## 2. Équipe et répartition des tâches

| Membre | Mission principale | Fichiers / travaux prévus |
|---|---|---|
| **[Ton prénom et ton nom] — Personne A** | **Collecte, préparation et contrôle des données** | `src/data_loader.py`, `scripts/preparer_donnees.py`, contrôles des jointures et documentation des sources |
| [Prénom Nom] — Personne B | Calculs et analyse statistique | `src/calculs.py`, densités, classements, interprétations |
| [Prénom Nom] — Personne C | Graphiques et cartographie | `src/graphiques.py`, figures et carte GeoJSON |
| [Prénom Nom] — Personne D | Streamlit et intégration | `app.py`, navigation, filtres, gestion d'état |

La relecture du code, les tests, le support de présentation et la préparation de l'oral sont réalisés collectivement. Chaque membre doit pouvoir expliquer les grandes étapes du projet, y compris les parties développées par les autres.

## 3. Sources de données

Le projet doit croiser **au moins deux sources statistiques distinctes**. Le référentiel géographique utilisé pour la carte ne compte pas comme deuxième source.

| Source | Millésime | Utilité | Accès |
|---|---|---|---|
| **Base permanente des équipements (BPE), Insee** | 2025 | Lieux d'exercice et types d'équipements, notamment les codes `DEP` et `TYPEQU` | [Page Insee](https://www.insee.fr/fr/statistiques/8217525) · [Parquet](https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.parquet) |
| **Populations de référence par département, Insee** | 2023 | Population utilisée pour le calcul des densités | [Page Insee](https://www.insee.fr/fr/statistiques/8680726) · [Archive `ensemble.zip`](https://www.insee.fr/fr/statistiques/fichier/8680726/ensemble.zip) |
| **Contours des départements (GeoJSON)** | À vérifier selon le fichier retenu | Fond géographique pour la carte | [france-geojson](https://github.com/gregoiredavid/france-geojson) · [data.gouv.fr](https://www.data.gouv.fr/datasets/contours-administratifs) |

Nomenclature officielle des équipements : [BPE 2025 — `TYPEQU`](https://www.insee.fr/fr/metadonnees/source/fichier/BPE25_liste_hierarchisee_TYPEQU.html).

**État des sources :** les fichiers CSV de population listés ci-dessous ont été transmis pour le projet. Le fichier BPE Parquet et le GeoJSON ne font **pas** partie des fichiers transmis lors de la rédaction initiale de ce README ; leur téléchargement et leur contrôle restent à effectuer.

### 3.1. Fichiers de population déjà reçus

Tous les fichiers CSV vérifiés sont encodés en UTF-8 et utilisent le séparateur `;`.

| Fichier | Niveau géographique / rôle | Nombre de lignes constaté |
|---|---|---:|
| `donnees_departements.csv` | **Population par département — fichier principal pour la jointure** | **100** |
| `donnees_regions.csv` | Population par région | 17 |
| `donnees_arrondissements.csv` | Population par arrondissement | 333 |
| `donnees_cantons.csv` | Population par canton | 2 042 |
| `donnees_communes.csv` | Population par commune | 34 900 |
| `donnees_communes_deleguees.csv` | Communes déléguées / associées | 2 627 |
| `donnees_fractions_cantonales.csv` | Fractions cantonales | 693 |
| `donnees_collectivites.csv` | Certaines collectivités distinctes des départements étudiés | 4 |
| `metadonnees.csv` | Description des variables et modalités | 39 143 |

Ces volumes correspondent aux **fichiers reçus et inspectés**, pas à des données calculées par l'application. Ils sont susceptibles de changer si un autre millésime ou une autre extraction est utilisé.

### 3.2. Colonnes utiles de `donnees_departements.csv`

| Colonne d'origine | Signification | Utilisation |
|---|---|---|
| `REG` | Code région | Regroupement régional |
| `Région` | Nom de la région | Filtres / affichage |
| `DEP` | Code département | **Clé de jointure** avec la BPE |
| `Département` | Nom du département | Filtres / affichage |
| `NBARR` | Nombre d'arrondissements | Information descriptive (facultative) |
| `NBCAN` | Nombre de cantons | Information descriptive (facultative) |
| `NBCOM` | Nombre de communes | Information descriptive (facultative) |
| `PMUN` | **Population municipale** | **Dénominateur des densités** |
| `PTOT` | Population totale | Contexte, non utilisée à la place de `PMUN` dans les densités |

**Contrôles déjà réalisés sur le fichier reçu :**

- 100 lignes et **100 codes `DEP` distincts** ;
- aucun doublon sur `DEP` ;
- codes département à traiter comme du **texte**, pas des nombres ;
- présence notamment de `2A`, `2B`, `971`, `972`, `973` et `974` ;
- **absence de Mayotte (`976`)** dans cette extraction départementale.

Le périmètre définitif devra être fixé après comparaison avec les codes de la BPE et du GeoJSON. Un département sans population comparable ne doit pas recevoir une densité calculée artificiellement.

## 4. Ma mission — Personne A : données et jointures

Mon rôle est de livrer aux autres membres du groupe une **table fiable, documentée et directement exploitable** par l'application Streamlit.

### Étape A1 — Récupération et inventaire

- [ ] Télécharger la BPE 2025 au format Parquet et sa nomenclature `TYPEQU`.
- [x] Récupérer les fichiers CSV de population transmis pour le projet.
- [ ] Télécharger et sélectionner un GeoJSON des départements compatible avec le périmètre.
- [ ] Consigner les liens, noms exacts, millésimes et dates de téléchargement.
- [ ] Conserver une copie **inchangée** des fichiers sources dans `data/raw/` et `data/geo/`.

### Étape A2 — Exploration et contrôle des sources

- [ ] Afficher le nombre de lignes, de colonnes et les types de variables.
- [ ] Repérer les valeurs manquantes, codes non reconnus et doublons éventuels.
- [ ] Vérifier la signification des codes `TYPEQU` à partir de la nomenclature officielle.
- [ ] Sélectionner les professions retenues pour l'étude.
- [ ] Définir précisément le périmètre géographique commun aux sources.

### Étape A3 — Harmonisation des données

- [ ] Conserver les codes département au format texte (`01`, `2A`, `2B`, `971`, etc.).
- [ ] Supprimer les espaces superflus et harmoniser les majuscules si nécessaire.
- [ ] Vérifier les populations municipales (`PMUN`) : valeurs manquantes, nulles ou négatives.
- [ ] Ne pas confondre absence de valeur et valeur égale à zéro.
- [ ] Normaliser les noms de colonnes **dans la table de travail seulement**, sans modifier les sources originales.

### Étape A4 — Agrégation de la BPE

- [ ] Filtrer les types d'équipements correspondant aux professions sélectionnées.
- [ ] Compter les observations par `DEP` et profession (`TYPEQU`).
- [ ] Vérifier que les totaux agrégés correspondent aux observations conservées.
- [ ] Documenter le fait que la BPE compte des **lieux d'exercice** et non nécessairement des professionnels uniques.

### Étape A5 — Jointure et vérifications

- [ ] Joindre les comptages BPE à la population départementale sur `DEP`.
- [ ] Vérifier l'unicité de la population par département (`many_to_one` si jointure depuis les comptages).
- [ ] Comparer les nombres de lignes **avant et après** jointure.
- [ ] Lister les codes sans correspondance dans **les deux sens**.
- [ ] Traiter explicitement les écarts de périmètre, notamment `976` si présent dans la BPE.
- [ ] Vérifier qu'une absence de données n'est pas automatiquement transformée en zéro.
- [ ] Enregistrer les résultats des contrôles pour la soutenance.

### Étape A6 — Livraison aux autres membres

- [ ] Exporter une table nettoyée, idéalement en Parquet : `data/processed/donnees_finales.parquet`.
- [ ] Documenter les colonnes finales, leurs types, leurs unités et leurs sources.
- [ ] Transmettre le fichier à la personne B pour les indicateurs.
- [ ] Vérifier avec la personne C que les codes de la table correspondent au GeoJSON.
- [ ] Vérifier avec la personne D que la table se charge correctement dans Streamlit.
- [ ] Faire relire les contrôles par un autre membre.

## 5. Méthode de préparation des données

Le traitement prévu suit les étapes ci-dessous :

```text
BPE 2025 (Parquet)                    Population 2023 (CSV)
        |                                      |
        v                                      v
Sélection des codes TYPEQU            Lecture et contrôle de PMUN
        |                                      |
        v                                      v
Comptage par DEP + profession         Contrôle d'unicité de DEP
        |                                      |
        +-------------- jointure -------------+
                           |
                           v
                Contrôles de correspondance
                           |
                           v
                 Table analytique finale
                           |
                           v
             Calcul des densités / Streamlit
```

### 5.1. Lecture correcte des CSV

Les codes département doivent rester des chaînes de caractères. Exemple de lecture :

```python
import pandas as pd

population = pd.read_csv(
    "data/raw/donnees_departements.csv",
    sep=";",
    dtype={"DEP": "string", "REG": "string"},
    encoding="utf-8"
)

print(population.shape)
print(population[["DEP", "Département", "PMUN"]].head())
print("Départements distincts :", population["DEP"].nunique())
print("Doublons DEP :", population["DEP"].duplicated().sum())
```

Ce bloc est un **exemple de contrôle**. Le script final devra être placé dans `scripts/preparer_donnees.py`, découpé en fonctions avec docstrings et appelé depuis une fonction `main()`.

### 5.2. Jointure prévue

La clé commune est le **code département**. Les étapes de jointure seront réalisées avec `pandas.merge`, en contrôlant les correspondances et les cardinalités. La structure analytique cible est :

| Colonne finale prévue | Description |
|---|---|
| `code_departement` | Code du département, conservé en texte |
| `departement` | Nom du département |
| `code_region` | Code de la région |
| `region` | Nom de la région |
| `profession` | Libellé de la profession |
| `code_typequ` | Code de la BPE |
| `nombre_lieux` | Nombre de lieux d'exercice observés |
| `population` | Population municipale (2023) |
| `densite_100k` | Nombre de lieux pour 100 000 habitants |

Le nombre final de lignes dépendra du périmètre, du nombre de professions retenues et de la méthode utilisée pour représenter les combinaisons sans observation.

### 5.3. Indicateur principal

La densité sera calculée ainsi :

```text
Densité pour 100 000 habitants
    = (nombre de lieux d'exercice / population municipale) × 100 000
```

**Précision méthodologique :** une densité de lieux d'exercice n'est ni une densité de médecins uniques, ni un indicateur complet d'accessibilité aux soins.

## 6. Organisation prévue du dépôt

```text
projet-streamlit-sante/
├── app.py                       # Application Streamlit (à développer)
├── README.md                    # Documentation du projet
├── requirements.txt             # Dépendances Python (à compléter)
├── .gitignore                   # Fichiers locaux à exclure
├── data/
│   ├── raw/                     # Sources statistiques originales
│   ├── geo/                     # GeoJSON des départements
│   └── processed/               # Table analytique produite après traitement
├── src/
│   ├── __init__.py
│   ├── data_loader.py            # Lecture, nettoyage, contrôles (Personne A)
│   ├── calculs.py                # Indicateurs (Personne B)
│   └── graphiques.py             # Cartes et graphiques (Personne C)
├── scripts/
│   └── preparer_donnees.py      # Pipeline de préparation (Personne A)
├── tests/
│   └── test_controles.py        # Tests de qualité des données
└── presentation/
    └── soutenance.pptx          # Support de soutenance (à produire)
```

Cette arborescence décrit la **cible du dépôt** : la présence de ces dossiers ou fichiers ne signifie pas qu'ils ont déjà été créés.

## 7. Installation et lancement (une fois l'application intégrée)

### Prérequis

- Python (version exacte à fixer et tester par le groupe) ;
- Git pour contribuer au dépôt ;
- les bibliothèques indiquées dans `requirements.txt`.

### Installation

Dans le dossier du projet :

```bash
python -m venv .venv
```

**Sous Windows PowerShell :**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Sous macOS / Linux :**

```bash
source .venv/bin/activate
```

Installer ensuite les dépendances :

```bash
python -m pip install -r requirements.txt
```

### Préparation des données

Lorsque le script de préparation sera disponible, placer les fichiers sources dans `data/raw/`, puis exécuter :

```bash
python scripts/preparer_donnees.py
```

Le script devra produire `data/processed/donnees_finales.parquet` et afficher ou enregistrer le résultat des contrôles de jointure.

### Lancement de Streamlit

Lorsque `app.py` sera intégré :

```bash
python -m streamlit run app.py
```

**Important :** ces commandes décrivent le fonctionnement attendu de la version finale ; elles ne garantissent pas le lancement d'un dépôt encore incomplet.

## 8. Travail collaboratif sur GitHub

Pour éviter les conflits, chacun travaille sur une branche dédiée à sa partie. Pour la **Personne A** :

```bash
git checkout -b feature/preparation-donnees
```

Une fois les fichiers préparés :

```bash
git add README.md src/data_loader.py scripts/preparer_donnees.py
git commit -m "Ajout de la préparation et des contrôles des données"
git push -u origin feature/preparation-donnees
```

Créer ensuite une **pull request** vers la branche principale et faire relire les modifications par un autre membre.

**Ne pas envoyer le fichier brut `BPE25.parquet` sur GitHub :** le fichier annoncé par le sujet dépasse la limite de taille habituelle d'un fichier GitHub. Documenter plutôt son téléchargement officiel ; ne versionner les exports préparés que si leur taille et les règles du dépôt le permettent. Exclure également `.venv/` et les fichiers temporaires avec `.gitignore`.

## 9. Fonctionnalités prévues de l'application

- Vue d'ensemble avec indicateurs synthétiques ;
- filtres par département, région et profession ;
- carte des densités par département ;
- classements et comparaisons entre professions ;
- comparaison de deux départements ;
- typologie descriptive en zones, si l'analyse est suffisamment solide ;
- commentaires des résultats et rappel des limites.

L'application utilisera au minimum deux méthodes avancées parmi `st.form`, `st.session_state` et `st.cache_data`. L'équipe prévoit d'utiliser les trois si elles répondent à de vrais besoins.

## 10. Limites connues et précautions

- **BPE :** les observations décrivent des lieux d'exercice ; un même praticien peut être compté sur plusieurs sites et les médecins salariés des hôpitaux ne sont pas inclus dans les catégories libérales.
- **Millésimes :** la BPE 2025 est rapprochée de la population de référence 2023.
- **Périmètre :** l'extraction départementale actuellement reçue contient 100 départements et n'inclut pas Mayotte (`976`).
- **Accès aux soins :** la densité départementale ne mesure pas directement les distances, délais de rendez-vous ni les besoins des habitants.
- **Zonage :** une classification construite à partir de ces indicateurs reste descriptive et ne correspond pas à une tarification assurantielle démontrée.

Ces limites seront prises en compte dans les interprétations et présentées lors de la soutenance.

## 11. Calendrier et rendu

| Date | Étape |
|---|---|
| 4 novembre 2026 | Lancement du projet et constitution des groupes |
| 16 novembre 2026 | Date limite de validation d'un sujet libre (si applicable) |
| **30 novembre 2026** | **Dépôt sur Updago avant la soutenance et présentation du projet** |

Livrables attendus : code Python, `README.md`, `requirements.txt`, données ou liens de récupération, et présentation PowerPoint avec les noms des membres.

La soutenance dure **20 minutes par groupe** : environ 6 minutes de présentation, 6 minutes de démonstration et 6 minutes de questions techniques (avec une marge sur le temps restant).

---

**Projet réalisé dans le cadre du BUT 3 Science des Données — VCOD.**

*À compléter avant le rendu : noms des membres, version Python testée, fichiers effectivement intégrés, résultats des contrôles, procédure de reproduction validée sur un autre ordinateur et éventuelle licence du dépôt.*
