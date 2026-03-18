import re


MERCHANT_RULES = [
    # Amazon / Apple
    ("AMAZON PRIME", "Amazon"),
    ("AMZNMKTPLACE", "Amazon"),
    ("AMAZON CO UK", "Amazon"),
    ("AMAZON", "Amazon"),
    ("AMZN", "Amazon"),
    ("APPLE COM BILL", "Apple"),

    # Transport
    ("TRAINLINE COM", "Trainline"),
    ("TRAINLINE", "Trainline"),
    ("TFL TRAVEL CHARGE", "TfL"),
    ("LUL TICKET MACHINE", "TfL"),
    ("TFL", "TfL"),
    ("LUL", "TfL"),

    # Groceries / household
    ("TESCO STORE", "Tesco"),
    ("TESCO", "Tesco"),
    ("SAINSBURY S", "Sainsbury's"),
    ("SAINSBURY", "Sainsbury's"),
    ("M S", "M&S"),
    ("MARKS SPENCER", "M&S"),
    ("IKEA LTD", "IKEA"),
    ("IKEA UK", "IKEA"),
    ("IKEA", "IKEA"),
    ("INPOST CO UK", "InPost"),
    ("INPOST", "InPost"),
    ("BOOTS OPTICIANS", "Boots"),
    ("BOOTS THE CHEMIST", "Boots"),
    ("BOOTS UK LTD", "Boots"),
    ("BOOTS", "Boots"),
    ("EDF UK CARD PAYMENTS", "EDF Energy"),
    ("CLAPHAM CONVENIENCE", "Clapham Convenience"),
    ("HANDY STORES", "Handy Stores"),
    ("SEVEN ELEVEN FOODS", "Seven Eleven Foods"),
    ("COMMON", "Common"),

    # Coffee / food / restaurants
    ("STARBUCKS", "Starbucks"),
    ("PRET", "Pret"),
    ("COSTA", "Costa"),
    ("DOMINOS PIZZA", "Domino's"),
    ("DOMINOS", "Domino's"),
    ("PIZZA HUT", "Pizza Hut"),
    ("ITSU", "itsu"),
    ("WAGAMAMA", "Wagamama"),
    ("MCDONALDS", "McDonald's"),
    ("RUDYS CLAPHAM", "Rudy's"),
    ("RUDYS", "Rudy's"),
    ("BLANK STREET", "Blank Street"),
    ("KISS THE HIPPO", "Kiss the Hippo"),
    ("DELIVEROO", "Deliveroo"),
    ("MARUGAME UDON", "Marugame Udon"),
    ("DUBH LINN GATE IRISH P", "Dubh Linn Gate"),

    # Health / fitness / beauty
    ("YOGAHAVEN", "Yogahaven"),
    ("YOGA UNION", "Yoga Union"),
    ("TREATWELL", "Treatwell"),
    ("DECIEM", "Deciem"),
    ("KIEHLS", "Kiehl's"),
    ("PATIENT ZONE", "Patient Zone"),

    # Shopping
    ("OLIVERBONAS", "Oliver Bonas"),
    ("ZARA HOME", "Zara Home"),
    ("BERSHKA", "Bershka"),
    ("KURT GEIGER", "Kurt Geiger"),
    ("ANN SUMMERS", "Ann Summers"),
    ("FORTNUMANDMASON", "Fortnum & Mason"),
    ("PAPIER", "Papier"),
    ("NESPRESSO", "Nespresso"),
    ("JOHN LEWIS", "John Lewis"),
    ("LOVEART", "LoveArt"),
    ("DUSK COM", "DUSK"),
    ("DUNELM SOFTFURNISHINGS", "Dunelm"),

    # Bills / housing
    ("H3G", "Three"),
    ("URBAN JUNGLE", "Urban Jungle"),
    ("LONDON BOROUGH OF LAMB", "Lambeth Council"),
    ("L B OF LAMBETH", "Lambeth Council"),

    ("STANDING ORDER VIA FASTER PAYMENT TO MARSH", "Marsh & Parsons"),
    ("STANDING ORDER TO MARSH", "Marsh & Parsons"),
    ("MARSH PARSONS", "Marsh & Parsons"),
    ("MARSH&PARSONS", "Marsh & Parsons"),
    ("MARSH AND PARSONS", "Marsh & Parsons"),

    # Learning / subscriptions / software
    ("DATACAMP", "DataCamp"),
    ("COURSERA", "Coursera"),
    ("UDEMY", "Udemy"),
    ("OPENAI", "OpenAI"),
    ("LINKEDINPREA", "LinkedIn"),
    ("LINKEDIN P", "LinkedIn"),
    ("WL VUE", "Pearson VUE"),
    ("BLS JOBTESTPREP", "JobTestPrep"),

    ("TRADING 212", "Trading 212"),
    ("MONEYBOX CLIENT", "Moneybox"),
    ("AMERICAN EXPRESS", "American Express"),
    ("CLUB LLOYDS FEE", "Club Lloyds Fee"),
    ("INTEREST GROSS", "Interest"),
    ("STRIPE", "Stripe"),
    ("INCENTIVE", "Incentive"),

]

def normalize_merchant(description_raw: str) -> str:
    """
    Convert a raw bank description into a cleaner merchant label.

    This is a lightweight first version:
    - trims whitespace
    - uppercases for matching
    - removes obvious punctuation noise
    - applies simple keyword rules
    - falls back to a cleaned title-cased version
    """
    cleaned = (description_raw or "").strip()

    if not cleaned:
        return ""

    normalized_for_matching = re.sub(r"[^A-Z0-9 ]+", " ", cleaned.upper())
    normalized_for_matching = re.sub(r"\s+", " ", normalized_for_matching).strip()

    for keyword, merchant_name in MERCHANT_RULES:
        if keyword in normalized_for_matching:
            return merchant_name

    fallback = re.sub(r"\s+", " ", cleaned).strip()
    return fallback.title()