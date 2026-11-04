import pytest
from sqlalchemy import text

from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from app.domain.entities.turno import NuevoTurno
from app.domain.ports.reloj import RelojSimulado
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.errors import HorarioOcupado
from sqlalchemy.exc import IntegrityError
from app.infrastructure.db.models import TurnoModel
from tests.integration.fabricas import crear_profesional, crear_prestacion, crear_turno, hora

pytestmark = pytest.mark.integration


async def reserva(engine, *, inicio=None):
    profesional = await crear_profesional(engine)
    prestacion = await crear_prestacion(engine)
    return await crear_turno(engine, profesional_id=profesional, prestacion_id=prestacion, inicio=inicio or hora(10))


async def test_obtener_conserva_datos_operativos_y_acota_consultorio(engine, sesiones):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        turno = await unidad.turnos.obtener(1, identificador)
        assert turno.id == identificador
        assert turno.ciclo_confirmacion == 1
        assert turno.creado_en == hora(8)
        assert await unidad.turnos.obtener(2, identificador) is None
        assert await unidad.turnos.obtener(1, identificador + 999) is None


async def test_actualizar_conserva_identidad_y_devuelve_cambios(engine, sesiones):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        original = await unidad.turnos.obtener(1, identificador)
        actualizado = await unidad.turnos.actualizar(original, {
            "inicio": hora(11), "fin": hora(11, 30), "ciclo_confirmacion": 2,
            "reprogramado_de_inicio": original.inicio, "actualizado_en": hora(9),
        })
        assert actualizado.id == original.id
        assert actualizado.inicio == hora(11)
        assert actualizado.ciclo_confirmacion == 2
        assert actualizado.reprogramado_de_inicio == hora(10)


@pytest.mark.parametrize("campo,nuevo", [
    ("estado", "confirmado"), ("ciclo_confirmacion", 2),
    ("inicio", hora(10, 15)), ("fin", hora(10, 45)),
    ("marcado_sin_confirmar_en", hora(9)),
])
async def test_actualizacion_con_lectura_obsoleta_es_conflicto_sin_historia_parcial(engine, sesiones, campo, nuevo):
    from app.domain.errors_turnos import ConflictoDeTurno
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        original = await unidad.turnos.obtener(1, identificador)
    async with sesiones() as sesion:
        await sesion.execute(text(f"UPDATE turno SET {campo}=:valor WHERE id=:id"), {"valor": nuevo, "id": identificador})
        await sesion.commit()
    with pytest.raises(ConflictoDeTurno):
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            await unidad.turnos.actualizar(original, {"inicio": hora(11), "fin": hora(11, 30)})
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 0
        assert await sesion.scalar(text("SELECT inicio FROM turno WHERE id=:id"), {"id": identificador}) == (nuevo if campo == "inicio" else hora(10))


async def test_guardar_usa_tiempos_explicitos_y_conserva_trazabilidad(engine, sesiones):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones, reloj=RelojSimulado(hora(7))) as unidad:
        anterior = await unidad.turnos.obtener(1, identificador)
        nuevo = await unidad.turnos.guardar(NuevoTurno(
            consultorio_id=1, paciente_id=anterior.paciente_id,
            profesional_id=anterior.profesional_id, box_id=anterior.box_id,
            prestacion_id=anterior.prestacion_id, inicio=hora(11), fin=hora(11, 30),
            estado=EstadoTurno.CONFIRMADO, origen="recepcion",
            creado_en=hora(8), actualizado_en=hora(8), confirmado_en=hora(8),
        ))
        assert nuevo.creado_en == hora(8)
        assert nuevo.actualizado_en == hora(8)
        assert nuevo.confirmado_en == hora(8)
        assert nuevo.estado == EstadoTurno.CONFIRMADO
        assert nuevo.origen == "recepcion"


async def test_agenda_configuracion_y_ficha_son_minimas_y_por_consultorio(engine, sesiones):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        turno = await unidad.turnos.obtener(1, identificador)
        parametros = await unidad.agenda.obtener_configuracion(1)
        assert parametros.zona_horaria == "America/Argentina/Buenos_Aires"
        assert parametros.horas_confirmacion == 48
        assert parametros.minutos_granularidad == 15
        assert await unidad.agenda.obtener_configuracion(99) is None
        paciente = await unidad.agenda.obtener_paciente(1, turno.paciente_id)
        assert paciente.nombre == "Paciente"
        assert paciente.apellido == "Sintetico"
        assert not hasattr(paciente, "dni")
        assert not hasattr(paciente, "telefono")
        assert await unidad.agenda.obtener_paciente(2, turno.paciente_id) is None


async def test_agenda_resuelve_vinculo_bloques_y_bloqueos_globales_y_propios(engine, sesiones):
    from datetime import time
    identificador = await reserva(engine)
    otro_profesional = await crear_profesional(engine, box_id=2)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        turno = await unidad.turnos.obtener(1, identificador)
    async with sesiones() as sesion:
        await sesion.execute(text("""INSERT INTO usuario(id,consultorio_id,nombre_usuario,email,password_hash,rol,activo,creado_en,actualizado_en)
            VALUES (10,1,'profesor','prof@example.test','hash','profesional',true,:ahora,:ahora)"""), {"ahora": hora(8)})
        await sesion.execute(text("UPDATE profesional SET usuario_id=10 WHERE id=:id"), {"id": turno.profesional_id})
        await sesion.execute(text("""INSERT INTO horario_semanal(consultorio_id,profesional_id,dia_semana,hora_inicio,hora_fin)
            VALUES (1,:prof,1,'09:00','12:00'),(1,:prof,2,'14:00','16:00'),(1,:otro,1,'13:00','17:00')"""), {"prof": turno.profesional_id, "otro": otro_profesional})
        await sesion.execute(text("""INSERT INTO bloqueo_agenda(consultorio_id,profesional_id,tipo,inicio,fin,creado_por_id,creado_en)
            VALUES (1,NULL,'feriado',:inicio,:fin,10,:ahora),(1,:prof,'ausencia',:inicio,:fin,10,:ahora),(1,:otro,'ausencia',:inicio,:fin,10,:ahora)"""), {"inicio": hora(13), "fin": hora(14), "ahora": hora(8), "prof": turno.profesional_id, "otro": otro_profesional})
        await sesion.commit()
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        assert await unidad.agenda.profesional_vinculado(1, 10) == turno.profesional_id
        assert await unidad.agenda.profesional_vinculado(2, 10) is None
        assert await unidad.agenda.bloques(1, turno.profesional_id, 1) == [(time(9), time(12))]
        assert await unidad.agenda.bloques(1, turno.profesional_id, 3) == []
        assert await unidad.agenda.bloques(2, turno.profesional_id, 1) == []
        assert len(await unidad.agenda.bloqueos(1, turno.profesional_id)) == 2
        assert await unidad.agenda.bloqueos(2, turno.profesional_id) == []
        assert await unidad.agenda.pacientes_de_profesional(1, turno.profesional_id) == frozenset({turno.paciente_id})
        assert await unidad.agenda.pacientes_de_profesional(1, otro_profesional) == frozenset()
        assert await unidad.agenda.pacientes_de_profesional(2, turno.profesional_id) == frozenset()


async def test_listado_filtra_profesional_ficha_y_rango_por_inicio_y_ordena(engine, sesiones):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        primero = await unidad.turnos.obtener(1, identificador)
        segundo = await unidad.turnos.guardar(NuevoTurno(
            consultorio_id=1, paciente_id=primero.paciente_id, profesional_id=primero.profesional_id,
            box_id=primero.box_id, prestacion_id=primero.prestacion_id, inicio=hora(9), fin=hora(9, 30),
        ))
        filas = await unidad.turnos.listar(1, profesional_id=primero.profesional_id, paciente_id=primero.paciente_id)
        assert [turno.id for turno in filas] == [segundo.id, primero.id]
        assert [t.id for t in await unidad.turnos.listar(1, desde=hora(9), hasta=hora(10))] == [segundo.id]
        assert await unidad.turnos.listar(2) == []
        assert await unidad.turnos.listar(1, profesional_id=999) == []
        assert await unidad.turnos.listar(1, paciente_id=999) == []


@pytest.mark.parametrize("estado,ocupa", [("pendiente", True), ("confirmado", True), ("atendido", True), ("ausente", True), ("cancelado", False), ("liberado", False)])
async def test_solapamiento_incluye_sobreturno_activo_y_excluye_fila_y_bordes(engine, sesiones, estado, ocupa):
    identificador = await reserva(engine)
    async with sesiones() as sesion:
        await sesion.execute(text("UPDATE turno SET es_sobreturno=true,estado=CAST(:estado AS estado_turno) WHERE id=:id"), {"estado": estado, "id": identificador})
        await sesion.commit()
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        turno = await unidad.turnos.obtener(1, identificador)
        assert await unidad.turnos.hay_solapamiento(1, turno.profesional_id, hora(10, 15), hora(10, 45)) is ocupa
        assert not await unidad.turnos.hay_solapamiento(1, turno.profesional_id, hora(10, 30), hora(11))
        assert not await unidad.turnos.hay_solapamiento(1, turno.profesional_id, hora(9, 30), hora(10))
        assert not await unidad.turnos.hay_solapamiento(1, turno.profesional_id, hora(10), hora(10, 30), excluir_id=identificador)
        assert not await unidad.turnos.hay_solapamiento(2, turno.profesional_id, hora(10), hora(10, 30))
        assert not await unidad.turnos.hay_solapamiento(1, 999, hora(10), hora(10, 30))


@pytest.mark.parametrize("operacion", ["actualizar", "commit", "otra_integridad"])
async def test_integridad_se_traduce_selectivamente_y_revierte_operacion(engine, sesiones, operacion):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        original = await unidad.turnos.obtener(1, identificador)
    if operacion != "otra_integridad":
        await crear_turno(engine, profesional_id=original.profesional_id, prestacion_id=original.prestacion_id, inicio=hora(11))
    with pytest.raises(IntegrityError if operacion == "otra_integridad" else HorarioOcupado):
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            if operacion == "commit":
                unidad._sesion.add(TurnoModel(
                    consultorio_id=1,paciente_id=original.paciente_id,
                    profesional_id=original.profesional_id,prestacion_id=original.prestacion_id,
                    box_id=original.box_id,inicio=hora(11),fin=hora(11,30),creado_en=hora(8),
                ))
            else:
                cambios = {"paciente_id": 999999} if operacion == "otra_integridad" else {"inicio": hora(11), "fin": hora(11,30)}
                await unidad.turnos.actualizar(original, cambios)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        conservado = await unidad.turnos.obtener(1, identificador)
        assert conservado.inicio == hora(10)
        assert conservado.paciente_id == original.paciente_id
        assert len(await unidad.turnos.listar(1)) == (1 if operacion == "otra_integridad" else 2)
        assert await unidad.historial.listar(1, identificador) == []


@pytest.mark.parametrize("tabla,columna,repo,atributo", [
    ("profesional", "activo", "profesionales", "profesional_id"),
    ("prestacion", "activa", "prestaciones", "prestacion_id"),
])
async def test_referencias_inactivas_no_admiten_nuevas_reservas(engine, sesiones, tabla, columna, repo, atributo):
    identificador = await reserva(engine)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        turno = await unidad.turnos.obtener(1, identificador)
        recurso_id = getattr(turno, atributo)
        assert await getattr(unidad, repo).obtener(1, recurso_id) is not None
    async with sesiones() as sesion:
        await sesion.execute(text(f"UPDATE {tabla} SET {columna}=false WHERE id=:id"), {"id": recurso_id})
        await sesion.commit()
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        assert await getattr(unidad, repo).obtener(1, recurso_id) is None
        assert await unidad.turnos.obtener(1, identificador) is not None
