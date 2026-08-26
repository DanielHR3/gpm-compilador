"""Primitivos del formato .gpm.

Los valores por omision se tomaron de dos exports autenticos de la plataforma.
El orden de las claves reproduce el del export porque la prueba de ida y vuelta
compara byte a byte.
"""

import json
from dataclasses import dataclass


@dataclass
class RUTS:
    """Ficha del Registro Unico de Tramites y Servicios que viaja dentro del .gpm."""

    category: str = "ciudadano"
    type_of_person: str = "ambas"
    tiempo_entrega: str = ""
    costo: str = ""
    description: str = ""
    publico: bool = False
    process_limit: str = "999"
    categoria_id: str = "1"


def campo(
    id, nombre, tipo, etiqueta, formulario_id, posicion,
    validacion="", datos=None, extra=None, readonly=False,
    valor_default="", ayuda=None, documento_id=None,
    dependiente_tipo=None, dependiente_campo="", dependiente_valor=None,
):
    """Un campo del Form Builder. 25 claves, en el orden del export."""
    if extra is None:
        extra = {"tamano": "col-xs-12 col-md-6"}
    return {
        "id": str(id),
        "nombre": nombre,
        "readonly": "1" if readonly else "0",
        "valor_default": valor_default,
        "posicion": str(posicion),
        "tipo": tipo,
        "formulario_id": str(formulario_id),
        "etiqueta": etiqueta,
        "validacion": validacion,
        "ayuda": ayuda,
        "dependiente_tipo": dependiente_tipo,
        "dependiente_campo": dependiente_campo,
        "dependiente_valor": dependiente_valor,
        "datos": json.dumps(datos, ensure_ascii=False) if datos is not None else None,
        "documento_id": documento_id,
        "extra": json.dumps(extra, ensure_ascii=False),
        "dependiente_relacion": None,
        "catalogo_id": None,
        "valid": None,
        "valid_readonly": None,
        "condicion_valor_default": None,
        "valor_default_no_cumple": None,
        "condicion_solo_lectura": None,
        "config_applicant": None,
        "metadata": None,
    }


def formulario(id, nombre, proceso_id, campos, subtitulo="", is_reusable=False):
    """Una pantalla. 7 claves."""
    return {
        "id": str(id),
        "nombre": nombre,
        "proceso_id": str(proceso_id),
        "subtitle": subtitulo,
        "is_reusable": "1" if is_reusable else "0",
        "metadata": None,
        "Campos": list(campos),
    }


def paso(id, orden, formulario_id, tarea_id, modo="edicion", regla=""):
    """Un paso dentro de una tarea: que pantalla se muestra y en que modo. 7 claves."""
    return {
        "id": str(id),
        "orden": str(orden),
        "modo": modo,
        "regla": regla,
        "formulario_id": str(formulario_id),
        "tarea_id": str(tarea_id),
        "metadata": None,
    }


def tarea(
    id, identificador, nombre, proceso_id,
    inicial=False, terminal=False, actor_grupos=(), pasos=(), eventos=(),
    posx=0, posy=0, asignacion="autoservicio", asignacion_usuario="",
):
    """Una tarea del diagrama BPMN. 40 claves."""
    grupos = list(actor_grupos)
    return {
        "id": str(id),
        "identificador": identificador,
        "inicial": "1" if inicial else "0",
        "nombre": nombre,
        "posx": str(posx),
        "posy": str(posy),
        "asignacion": asignacion,
        "asignacion_usuario": asignacion_usuario,
        "asignacion_notificar": "0",
        "proceso_id": str(proceso_id),
        "almacenar_usuario": "0",
        "almacenar_usuario_variable": "",
        "acceso_modo": "grupos_usuarios" if grupos else "publico",
        "activacion": "si",
        "activacion_inicio": None,
        "activacion_fin": None,
        "vencimiento": "0",
        "vencimiento_valor": "10",
        "vencimiento_unidad": "D",
        "vencimiento_habiles": "0",
        "vencimiento_notificar": "0",
        "vencimiento_notificar_email": "",
        "vencimiento_notificar_dias": "0",
        "grupos_usuarios": None,
        "vencimiento_semana": "0",
        "disponible": "0",
        "disponible_habiles": "0",
        "disponible_semana": "0",
        "disponible_valor": "0",
        "terminal": "1" if terminal else "0",
        "expiration_action": None,
        "hora_inicio": None,
        "hora_fin": None,
        "horario_atencion": "0",
        "init_capture": "0",
        "extra": None,
        "metadata": None,
        "Pasos": list(pasos),
        "Eventos": list(eventos),
        "GruposUsuarios": [{"nombre": g} for g in grupos],
    }


def conexion(id, origen, destino, regla=None):
    """Una transicion. Sin regla es secuencial; con regla es evaluacion."""
    return {
        "id": id,
        "tarea_id_origen": origen,
        "tarea_id_destino": destino,
        "tipo": "evaluacion" if regla else "secuencial",
        "regla": regla,
    }


def proceso(
    id, nombre, homoclave, ruts, tareas, formularios,
    acciones, conexiones, documentos, folio_inicial="1",
):
    """El objeto raiz del .gpm. 36 claves, en el orden del export."""
    extra_interno = json.dumps({
        "is_plantilla": False,
        "is_nombre_personalizado": False,
        "nombre_personalizado": "",
        "folio_consecutivo_inicial": folio_inicial,
    }, ensure_ascii=False)
    return {
        "id": str(id),
        "nombre": nombre,
        "homoclave": homoclave,
        "width": "100",
        "height": "800",
        "cuenta_id": "18",
        "is_macro": "0",
        "is_reusable": "0",
        "public": "1" if ruts.publico else "0",
        "category": ruts.category,
        "type_of_person": ruts.type_of_person,
        "process_limit": ruts.process_limit,
        "categoria_id": ruts.categoria_id,
        "icon": None,
        "invited": "0",
        "client_id": "1",
        "add_in_menu": "0",
        "etapa_vida_id": "1",
        "tipo_apoyo_id": "1",
        "derecho_social_id": "1",
        "tiempo_entrega": ruts.tiempo_entrega,
        "costo": ruts.costo,
        "description": ruts.description,
        "json": None,
        "is_active": "1",
        "metadata": None,
        "semaforo": None,
        "folio": "",
        "extra": json.dumps(extra_interno, ensure_ascii=False),
        "Tareas": list(tareas),
        "Formularios": list(formularios),
        "Acciones": list(acciones),
        "Documentos": list(documentos),
        "Conexiones": list(conexiones),
        "Sections": [],
        "ElectronicFiles": [],
    }
