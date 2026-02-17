"""
Databáze německých slov s českými překlady.
Každá kategorie má svůj seznam slov ve formátu:
  {"de": "německé slovo", "cz": "český překlad"}
"""

CATEGORIES = {
    "Čísla": [
        {"de": "eins", "cz": "jedna"},
        {"de": "zwei", "cz": "dva"},
        {"de": "drei", "cz": "tři"},
        {"de": "vier", "cz": "čtyři"},
        {"de": "fünf", "cz": "pět"},
        {"de": "sechs", "cz": "šest"},
        {"de": "sieben", "cz": "sedm"},
        {"de": "acht", "cz": "osm"},
        {"de": "neun", "cz": "devět"},
        {"de": "zehn", "cz": "deset"},
    ],
    "Barvy": [
        {"de": "rot", "cz": "červená"},
        {"de": "blau", "cz": "modrá"},
        {"de": "grün", "cz": "zelená"},
        {"de": "gelb", "cz": "žlutá"},
        {"de": "schwarz", "cz": "černá"},
        {"de": "weiß", "cz": "bílá"},
        {"de": "orange", "cz": "oranžová"},
        {"de": "lila", "cz": "fialová"},
        {"de": "braun", "cz": "hnědá"},
        {"de": "grau", "cz": "šedá"},
    ],
    "Zvířata": [
        {"de": "der Hund", "cz": "pes"},
        {"de": "die Katze", "cz": "kočka"},
        {"de": "das Pferd", "cz": "kůň"},
        {"de": "der Vogel", "cz": "pták"},
        {"de": "die Kuh", "cz": "kráva"},
        {"de": "das Schwein", "cz": "prase"},
        {"de": "der Fisch", "cz": "ryba"},
        {"de": "der Hase", "cz": "zajíc"},
        {"de": "die Maus", "cz": "myš"},
        {"de": "der Bär", "cz": "medvěd"},
        {"de": "der Löwe", "cz": "lev"},
        {"de": "der Elefant", "cz": "slon"},
    ],
    "Jídlo": [
        {"de": "das Brot", "cz": "chléb"},
        {"de": "der Apfel", "cz": "jablko"},
        {"de": "die Milch", "cz": "mléko"},
        {"de": "das Ei", "cz": "vejce"},
        {"de": "der Käse", "cz": "sýr"},
        {"de": "die Kartoffel", "cz": "brambor"},
        {"de": "die Tomate", "cz": "rajče"},
        {"de": "das Fleisch", "cz": "maso"},
        {"de": "der Kuchen", "cz": "dort / koláč"},
        {"de": "das Wasser", "cz": "voda"},
        {"de": "der Kaffee", "cz": "káva"},
        {"de": "das Bier", "cz": "pivo"},
    ],
    "Dny v týdnu": [
        {"de": "Montag", "cz": "pondělí"},
        {"de": "Dienstag", "cz": "úterý"},
        {"de": "Mittwoch", "cz": "středa"},
        {"de": "Donnerstag", "cz": "čtvrtek"},
        {"de": "Freitag", "cz": "pátek"},
        {"de": "Samstag", "cz": "sobota"},
        {"de": "Sonntag", "cz": "neděle"},
    ],
    "Základní fráze": [
        {"de": "Hallo", "cz": "Ahoj"},
        {"de": "Guten Morgen", "cz": "Dobré ráno"},
        {"de": "Guten Tag", "cz": "Dobrý den"},
        {"de": "Guten Abend", "cz": "Dobrý večer"},
        {"de": "Auf Wiedersehen", "cz": "Na shledanou"},
        {"de": "Danke", "cz": "Díky"},
        {"de": "Bitte", "cz": "Prosím"},
        {"de": "Entschuldigung", "cz": "Promiňte"},
        {"de": "Ja", "cz": "Ano"},
        {"de": "Nein", "cz": "Ne"},
    ],
    "Rodina": [
        {"de": "die Mutter", "cz": "matka"},
        {"de": "der Vater", "cz": "otec"},
        {"de": "die Schwester", "cz": "sestra"},
        {"de": "der Bruder", "cz": "bratr"},
        {"de": "die Großmutter", "cz": "babička"},
        {"de": "der Großvater", "cz": "dědeček"},
        {"de": "die Tochter", "cz": "dcera"},
        {"de": "der Sohn", "cz": "syn"},
        {"de": "die Frau", "cz": "žena / manželka"},
        {"de": "der Mann", "cz": "muž / manžel"},
    ],
}

# Úrovně — které kategorie se odemknou při dosažení dané úrovně
LEVEL_UNLOCK = {
    1: ["Čísla"],
    2: ["Barvy"],
    3: ["Zvířata"],
    4: ["Jídlo"],
    5: ["Dny v týdnu"],
    6: ["Základní fráze"],
    7: ["Rodina"],
}

POINTS_PER_LEVEL = 100  # Body potřebné k posunu na další úroveň


def get_unlocked_words(level: int) -> list[dict]:
    """Vrátí seznam všech slov dostupných pro danou úroveň."""
    words = []
    for lvl, cats in LEVEL_UNLOCK.items():
        if lvl <= level:
            for cat in cats:
                words.extend(CATEGORIES[cat])
    return words


def get_wrong_answers(correct: dict, level: int, count: int = 3) -> list[str]:
    """
    Vrátí `count` špatných českých odpovědí pro danou otázku.
    Vybírá z odemčených slov, aby byly odpovědi relevantní.
    """
    import random
    pool = get_unlocked_words(level)
    wrong = [w["cz"] for w in pool if w["cz"] != correct["cz"]]
    if len(wrong) < count:
        # Doplníme ze všech slov pokud je pool příliš malý
        all_words = []
        for cat_words in CATEGORIES.values():
            all_words.extend(cat_words)
        wrong = [w["cz"] for w in all_words if w["cz"] != correct["cz"]]
    return random.sample(wrong, min(count, len(wrong)))
