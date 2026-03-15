from django import template

register = template.Library()


CATEGORY_ICON_MAP = {
    "Groceries": "🛒",
    "Transport": "🚇",
    "Travel": "🚇",
    "Eating Out": "🍽️",
    "Shopping": "🛍️",
    "Utilities": "💡",
    "Education": "📚",
    "Health and Wellness": "🧘",
    "Entertainment": "🎬",
    "Bills": "💵",
    "Salary": "💼",
}


@register.filter
def category_icon(category_name):
    if not category_name:
        return "•"
    return CATEGORY_ICON_MAP.get(category_name, "•")