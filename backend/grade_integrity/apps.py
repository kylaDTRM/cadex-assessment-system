from django.apps import AppConfig


class GradeIntegrityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "grade_integrity"

    def ready(self):
        pass
