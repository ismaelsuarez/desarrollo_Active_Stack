"""Disparador interno con secreto de servidor, fuera del contrato público."""
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.deps import get_reloj, get_settings
from app.api.v1.schemas.barrido import ResumenBarridoResponse
from app.core.config import Settings
from app.domain.ports.reloj import Reloj
from app.infrastructure.barrido import componer_barrido

router = APIRouter(prefix="/internal", include_in_schema=False)


async def autenticar_barrido(request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    credencial: Annotated[str | None, Header(alias="X-Sweep-Secret")] = None,
) -> None:
    secreto = settings.sweep_shared_secret
    valor = secreto.get_secret_value() if secreto is not None else ""
    if not valor or credencial is None or not secrets.compare_digest(
            credencial.encode("utf-8"), valor.encode("utf-8")):
        raise HTTPException(403, "Disparador no autorizado")
    if request.query_params or await request.body():
        raise HTTPException(422, "El disparador no admite query ni cuerpo")


@router.post("/barrido", response_model=ResumenBarridoResponse,
             dependencies=[Depends(autenticar_barrido)])
async def ejecutar_barrido(request: Request,
    reloj: Annotated[Reloj, Depends(get_reloj)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        return await componer_barrido(request.app, reloj, settings).ejecutar(settings.consultorio_activo_id)
    except Exception:
        raise HTTPException(503, "Barrido no disponible") from None
