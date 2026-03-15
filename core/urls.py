from django.urls import path

from .views import (
    confirm_amex_import,
    confirm_lloyds_import,
    confirm_santander_import,
    home,
    import_amex_csv,
    import_lloyds_csv,
    import_santander_csv,
    transactions_drilldown,
)

urlpatterns = [
    path("", home, name="home"),
    path("transactions/", transactions_drilldown, name="transactions_drilldown"),
    path("import/lloyds/", import_lloyds_csv, name="import_lloyds_csv"),
    path(
        "import/lloyds/confirm/",
        confirm_lloyds_import,
        name="confirm_lloyds_import",
    ),
    path("import/santander/", import_santander_csv, name="import_santander_csv"),
    path(
        "import/santander/confirm/",
        confirm_santander_import,
        name="confirm_santander_import",
    ),
    path("import/amex/", import_amex_csv, name="import_amex_csv"),
    path(
        "import/amex/confirm/",
        confirm_amex_import,
        name="confirm_amex_import",
    ),
]
