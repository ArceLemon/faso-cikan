
import os
import re
import sys


def main(source: str, destination: str) -> None:
    with open(source, encoding="utf-8") as f:
        texte = f.read()

    manquantes = set()

    def remplacer(m: re.Match) -> str:
        nom = m.group(1)
        if nom not in os.environ:
            manquantes.add(nom)
            return ""
        return os.environ[nom]

    resultat = re.sub(r"\$\{([A-Z0-9_]+)\}", remplacer, texte)
    if manquantes:
        sys.exit("Variables manquantes : " + ", ".join(sorted(manquantes)))

    with open(destination, "w", encoding="utf-8") as f:
        f.write(resultat)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
