from core.models import Category


CATEGORY_RULES = {
    "Tesco": "Groceries",
    "Sainsbury's": "Groceries",
    "Amazon": "Shopping",
    "Uber": "Transport",
    "Trainline": "Transport",
    "Pret": "Eating Out",
    "Costa": "Eating Out",
    "Starbucks": "Eating Out",
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