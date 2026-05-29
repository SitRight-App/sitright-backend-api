from dataclasses import dataclass, field

VALID_CLASSES = {"adequate", "forward_slouch", "excessive_recline", "indeterminate"}


@dataclass(frozen=True)
class RecommendationStep:
    body: str
    meta: str


@dataclass(frozen=True)
class Recommendation:
    id: str
    title: str
    description: str
    category: str
    icon: str
    frequency_label: str
    number: str
    posture_classes: tuple[str, ...]
    is_featured: bool = False
    featured_tagline: str | None = None
    featured_title_emphasis: str | None = None
    featured_body: str | None = None
    steps: tuple[RecommendationStep, ...] = field(default_factory=tuple)


_CATALOG: tuple[Recommendation, ...] = (
    Recommendation(
        id="lumbar-flexor-stretch",
        number="№ 01",
        title="Estiramiento de cadera flexora",
        description="Estiramiento de 90 segundos que relaja el psoas, principal responsable de inclinaciones pélvicas postprandiales.",
        category="lumbar",
        icon="lumbar-stretch",
        frequency_label="≈ 90 s · cuando se detecte desviación lumbar",
        posture_classes=("excessive_recline", "forward_slouch"),
        is_featured=True,
        featured_tagline="Recomendación del día · basada en tu lumbar",
        featured_title_emphasis="de cadera flexora.",
        featured_body=(
            "Detectamos que tu zona lumbar acumuló minutos de desviación durante la "
            "jornada. Este estiramiento de 90 segundos relaja el psoas — el principal "
            "responsable de inclinaciones pélvicas postprandiales."
        ),
        steps=(
            RecommendationStep("Ponte de pie con los pies separados al ancho de los hombros.", "Tiempo: 5 s"),
            RecommendationStep("Da un paso adelante con la pierna izquierda y flexiona la rodilla a 90°.", "Mantener: 25 s"),
            RecommendationStep("Empuja la cadera hacia adelante manteniendo el torso recto y la mirada al frente.", "Sentir el estiramiento en el psoas anterior"),
            RecommendationStep("Cambia de pierna y repite la misma secuencia.", "Mantener: 25 s"),
        ),
    ),
    Recommendation(
        id="lumbar-respaldo",
        number="№ 02",
        title="Apoyo lumbar contra el respaldo",
        description="Apoya la espalda completamente contra el respaldo durante 60 segundos cada hora.",
        category="lumbar",
        icon="lumbar-slouch",
        frequency_label="≈ 1 min · 6×/día",
        posture_classes=("excessive_recline", "forward_slouch"),
    ),
    Recommendation(
        id="cervical-retract",
        number="№ 03",
        title="Retracción cervical doble mentón",
        description="Lleva el mentón hacia atrás manteniendo la mirada al frente. Repite 10 veces.",
        category="cervical",
        icon="cervical-retract",
        frequency_label="≈ 30 s · 5×/día",
        posture_classes=("forward_slouch",),
    ),
    Recommendation(
        id="monitor-altura",
        number="№ 04",
        title="Ajuste de altura del monitor",
        description="El borde superior debe quedar a la altura de tus ojos. Usa una resma de papel si hace falta.",
        category="general",
        icon="monitor",
        frequency_label="≈ 2 min · una vez",
        posture_classes=("forward_slouch", "excessive_recline", "adequate"),
    ),
    Recommendation(
        id="pausa-activa",
        number="№ 05",
        title="Pausa activa de 5 minutos",
        description="Cada 45 min de trabajo continuo, levántate y camina al menos 30 metros.",
        category="general",
        icon="pause",
        frequency_label="cada 45 min",
        posture_classes=("adequate", "forward_slouch", "excessive_recline"),
    ),
    Recommendation(
        id="cojin-lumbar",
        number="№ 06",
        title="Cojín lumbar de soporte",
        description="Coloca un cojín o toalla enrollada en la curvatura lumbar entre vértebras L1—L5.",
        category="lumbar",
        icon="lumbar-cushion",
        frequency_label="uso continuo",
        posture_classes=("excessive_recline", "forward_slouch"),
    ),
    Recommendation(
        id="cervical-rotar",
        number="№ 07",
        title="Rotaciones cervicales suaves",
        description="Gira la cabeza lentamente 5 veces a cada lado. Mantén hombros relajados.",
        category="cervical",
        icon="cervical-rotate",
        frequency_label="≈ 45 s · 4×/día",
        posture_classes=("forward_slouch",),
    ),
    Recommendation(
        id="apoyo-plantar",
        number="№ 08",
        title="Apoyo plantar firme",
        description="Asegura que ambos pies toquen el suelo o usa un reposapiés. Rodillas a 90°.",
        category="general",
        icon="foot-support",
        frequency_label="configuración inicial",
        posture_classes=("excessive_recline", "forward_slouch", "adequate"),
    ),
    Recommendation(
        id="pelvis-neutra",
        number="№ 09",
        title="Pelvis neutra al sentarte",
        description="Empuja los glúteos hacia el respaldo, no resbales hacia el frente del asiento.",
        category="lumbar",
        icon="pelvis-neutral",
        frequency_label="cada cambio de postura",
        posture_classes=("forward_slouch", "excessive_recline"),
    ),
    Recommendation(
        id="hidratacion",
        number="№ 10",
        title="Hidratación frecuente",
        description="Bebe 250ml de agua cada hora. La deshidratación reduce elasticidad muscular.",
        category="general",
        icon="hydration",
        frequency_label="≈ 6—8 vasos / día",
        posture_classes=("adequate", "forward_slouch", "excessive_recline"),
    ),
    Recommendation(
        id="indeterminate-fix-vest",
        number="№ 11",
        title="Verifica el chaleco",
        description="El sistema no puede clasificar tu postura con certeza. Asegúrate de que el chaleco esté bien colocado y los sensores estén en contacto con el torso.",
        category="general",
        icon="vest-check",
        frequency_label="al detectar señal incierta",
        posture_classes=("indeterminate",),
    ),
)


class GetRecommendationsHandler:
    """Filtra el catálogo por clase postural (uso del dashboard)."""

    def execute(self, posture_class: str) -> list[Recommendation]:
        if posture_class not in VALID_CLASSES:
            raise ValueError(
                f"Clase postural inválida: '{posture_class}'. Valores válidos: {VALID_CLASSES}"
            )
        return [r for r in _CATALOG if posture_class in r.posture_classes]


class GetAllRecommendationsHandler:
    """Devuelve el catálogo completo de recomendaciones (uso de /recommendations)."""

    def execute(self) -> list[Recommendation]:
        return list(_CATALOG)
