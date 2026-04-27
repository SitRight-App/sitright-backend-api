from dataclasses import dataclass

VALID_CLASSES = {"adequate", "forward_slouch", "excessive_recline", "indeterminate"}


@dataclass(frozen=True)
class Recommendation:
    title: str
    description: str


_DATA: dict[str, list[Recommendation]] = {
    "forward_slouch": [
        Recommendation(
            "Ajusta la altura del monitor",
            "Sube el monitor a la altura de los ojos para evitar inclinar el cuello hacia adelante.",
        ),
        Recommendation(
            "Ejercicios de extensión cervical",
            "Inclina la cabeza hacia atrás suavemente, mantén 5 segundos. Repite 3 veces.",
        ),
        Recommendation(
            "Activa el respaldo lumbar",
            "Asegúrate de que el respaldo soporte la curva natural de tu espalda baja.",
        ),
        Recommendation(
            "Pausa activa",
            "Levántate y camina 2 minutos cada 30 minutos para evitar la fatiga muscular.",
        ),
    ],
    "excessive_recline": [
        Recommendation(
            "Ajusta el ángulo del respaldo",
            "Inclina el respaldo entre 95° y 110°. Evita reclinarte completamente.",
        ),
        Recommendation(
            "Apoya los pies en el suelo",
            "Ambos pies deben estar completamente apoyados. Usa un reposapiés si es necesario.",
        ),
        Recommendation(
            "Verifica la distancia al escritorio",
            "Acércate al escritorio. Los codos deben quedar a 90° con los brazos relajados.",
        ),
        Recommendation(
            "Estiramiento de cadera",
            "De pie, adelanta una pierna y lleva la cadera hacia adelante. Mantén 15 segundos.",
        ),
    ],
    "adequate": [
        Recommendation(
            "¡Excelente postura!",
            "Mantén esta posición. Recuerda hacer una pausa activa cada 30 minutos.",
        ),
        Recommendation(
            "Hidratación",
            "Aprovecha que tu postura es correcta para levantarte a beber agua en 30 minutos.",
        ),
    ],
    "indeterminate": [
        Recommendation(
            "Verifica el chaleco",
            "El sistema no puede clasificar tu postura con certeza. Asegúrate de que el chaleco esté bien colocado y los sensores estén en contacto con el torso.",
        ),
    ],
}


class GetRecommendationsHandler:
    def execute(self, posture_class: str) -> list[Recommendation]:
        if posture_class not in VALID_CLASSES:
            raise ValueError(f"Clase postural inválida: '{posture_class}'. Valores válidos: {VALID_CLASSES}")
        return _DATA[posture_class]
