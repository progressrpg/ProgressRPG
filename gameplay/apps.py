from django.apps import AppConfig


class GameplayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gameplay"

    def ready(self):
        import gameplay.signals
        from events.listeners import listen_for_events
        from progression.models import PlayerActivity

        listen_for_events(PlayerActivity)
