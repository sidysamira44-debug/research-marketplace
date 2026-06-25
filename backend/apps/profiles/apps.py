from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.profiles"
    verbose_name = "پروفایل‌ها"

    def ready(self):
        import apps.profiles.signals  # noqa: F401
