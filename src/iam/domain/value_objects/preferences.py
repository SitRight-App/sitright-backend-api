from dataclasses import dataclass


@dataclass(frozen=True)
class Preferences:
    """Preferencias editables del trabajador.

    - `email_notifications`: si recibe notificaciones por correo (HU-12 AC3).
    - `alert_threshold_minutes`: minutos sostenidos en postura mala antes
      de mostrar la alerta (HU-08).
    - `break_reminder_minutes`: intervalo de uso continuo antes de sugerir
      una pausa activa. HU-12 AC4: default 60 min cuando el trabajador no
      define un valor.
    - `language`: locale de la UI.
    """

    email_notifications: bool = True
    alert_threshold_minutes: int = 30
    break_reminder_minutes: int = 60
    language: str = "es"
