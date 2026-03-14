from django.urls import path

from .views import confirm_lloyds_import, home, import_lloyds_csv

urlpatterns = [
    path("", home, name="home"),
    path("import/lloyds/", import_lloyds_csv, name="import_lloyds_csv"),
    path(
        "import/lloyds/confirm/",
        confirm_lloyds_import,
        name="confirm_lloyds_import",
    ),
]