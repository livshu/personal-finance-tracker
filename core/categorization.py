from core.models import Category


CATEGORY_RULES = {
    # Groceries
    "Tesco": "Groceries",
    "Sainsbury's": "Groceries",
    "M&S": "Groceries",

    # Shopping
    "Amazon": "Shopping",
    "Apple": "Shopping",
    "IKEA": "Shopping",
    "Oliver Bonas": "Shopping",
    "Zara Home": "Shopping",
    "Bershka": "Shopping",
    "Kurt Geiger": "Shopping",
    "Ann Summers": "Shopping",
    "Fortnum & Mason": "Shopping",
    "Papier": "Shopping",
    "Nespresso": "Shopping",
    "InPost": "Shopping",
    "Boots": "Shopping",
    "Deciem": "Shopping",
    "Kiehl's": "Shopping",

    # Transport / travel
    "Uber": "Transport",
    "Trainline": "Travel",
    "TfL": "Transport",

    # Eating out
    "Pret": "Eating Out",
    "Costa": "Eating Out",
    "Starbucks": "Eating Out",
    "Domino's": "Eating Out",
    "Pizza Hut": "Eating Out",
    "itsu": "Eating Out",
    "Wagamama": "Eating Out",
    "McDonald's": "Eating Out",
    "Rudy's": "Eating Out",
    "Blank Street": "Eating Out",
    "Kiss the Hippo": "Eating Out",

    # Bills / utilities
    "EDF Energy": "Utilities",

    # Entertainment / subscriptions
    "OpenAI": "Entertainment",
    "LinkedIn": "Entertainment",

    # Health / fitness
    "Treatwell": "Shopping",
    "Patient Zone": "Bills",

    # Education
    "Coursera": "Education",
    "Udemy": "Education",
    "Pearson VUE": "Education",
    "JobTestPrep": "Education",
    "DataCamp": "Education",
    "OpenAI": "Education",
    "LinkedIn": "Education",

    # Health and wellness:
    "Yogahaven": "Health and Wellness",
    "Yoga Union": "Health and Wellness",
}


def suggest_category_for_merchant(merchant_normalized: str):
    """
    Return a Category object for a normalized merchant if a rule exists.
    Otherwise return None.

    This only applies a category when there is an exact merchant rule match.
    """
    if not merchant_normalized:
        return None

    category_name = CATEGORY_RULES.get(merchant_normalized)
    if not category_name:
        return None

    try:
        return Category.objects.get(name=category_name)
    except Category.DoesNotExist:
        return None