"""Respuestas reusables para enriquecer la documentación OpenAPI/Swagger.

Cada constante encapsula un código HTTP con su descripción y un ejemplo
de body, listo para spread en el `responses=` del decorador del endpoint.
"""
from typing import Any

UNAUTHORIZED: dict[int, dict[str, Any]] = {
    401: {
        "description": "Token Bearer faltante, inválido o expirado.",
        "content": {
            "application/json": {
                "example": {"detail": "Falta header Authorization Bearer"}
            }
        },
    }
}

FORBIDDEN_ADMIN_ONLY: dict[int, dict[str, Any]] = {
    403: {
        "description": "El usuario no tiene rol `admin`.",
        "content": {
            "application/json": {
                "example": {"detail": "Se requiere rol administrador"}
            }
        },
    }
}

NOT_FOUND_USER: dict[int, dict[str, Any]] = {
    404: {
        "description": "Usuario no encontrado.",
        "content": {
            "application/json": {"example": {"detail": "Usuario no encontrado"}}
        },
    }
}

NOT_FOUND_VEST: dict[int, dict[str, Any]] = {
    404: {
        "description": "El usuario no tiene un chaleco vinculado.",
        "content": {
            "application/json": {
                "example": {"detail": "No tienes un chaleco vinculado"}
            }
        },
    }
}

NOT_FOUND_SESSION: dict[int, dict[str, Any]] = {
    404: {
        "description": "Sesión no encontrada.",
        "content": {
            "application/json": {"example": {"detail": "Sesión no encontrada"}}
        },
    }
}

NOT_FOUND_NO_READINGS: dict[int, dict[str, Any]] = {
    404: {
        "description": (
            "El usuario tiene chaleco vinculado pero aún no hay lecturas "
            "registradas para él."
        ),
        "content": {
            "application/json": {
                "example": {"detail": "No hay lecturas registradas aún"}
            }
        },
    }
}

VALIDATION_ERROR: dict[int, dict[str, Any]] = {
    400: {
        "description": "Datos inválidos según la regla de negocio.",
        "content": {
            "application/json": {
                "example": {"detail": "La estatura debe estar entre 100 y 250 cm"}
            }
        },
    }
}

PYDANTIC_VALIDATION: dict[int, dict[str, Any]] = {
    422: {
        "description": "El payload no cumple el schema (campos faltantes o tipos incorrectos).",
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "loc": ["body", "email"],
                            "msg": "value is not a valid email address",
                            "type": "value_error.email",
                        }
                    ]
                }
            }
        },
    }
}
