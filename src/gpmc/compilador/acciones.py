"""Los cuatro arquetipos de Accion, emitidos desde plantilla.

Aqui es donde los defectos dejan de ser posibles. El folio del mismo tramite
esta mal en las dos implementaciones existentes: una implementacion uso ->count() sin
bloqueo (FOLIO-01) y otra uso rand(), que ni siquiera es consecutivo. Ninguna
de las dos escapa las variables al armar documentos (DOC-01).

El analista da parametros, nunca codigo, asi que ninguno de esos dos modos de
falla es expresable.
"""

import json
import re

from gpmc.nucleo.manifiesto import Accion

_VARIABLE_EN_PLANTILLA = re.compile(r"\{\{(\w+)\}\}")


def php_folio(prefijo: str, variable: str) -> str:
    """Folio consecutivo con bloqueo transaccional. Cierra FOLIO-01.

    Forma copiada byte a byte de los dos exports autenticos que funcionan
    (constancia-de-no-infraccion-vehicular-ambiental.gpm,
    pago-de-bases-licitaciones.gpm): el contador se llavea por el NOMBRE de la
    variable en la tabla 'dato_seguimiento', columna 'valor', con lockForUpdate.
    NO lleva proceso_id: la plataforma lo reasigna al importar y no reescribe las
    referencias dentro del PHP, asi que cualquier proceso_id hardcodeado deja el
    folio roto (PLAT-4, acta 2026-08-30). El incremento de 'valor' lo administra
    la plataforma, por eso la expresion solo lee con el lock y no reescribe.

    El export autentico trae un comentario '// Fixed Race Condition' en la misma
    linea; como toda la expresion va en una sola linea, ese '//' comentaria el
    resto (el str_pad y el return) si la plataforma la evalua cruda. No lo
    reproducimos: copiamos el mecanismo, no un comentario que puede romperlo.
    """
    return (
        "$year = date('Y'); "
        "$total = \\DB::table('dato_seguimiento')"
        f"->where('nombre', '{variable}')"
        "->lockForUpdate()->value('valor'); "
        "$consecutivo = str_pad($total + 1, 5, '0', STR_PAD_LEFT); "
        f"return '{prefijo}-' . $year . '-' . $consecutivo;"
    )


def php_costo(variable: str, tarifas: dict) -> str:
    """Calculo de costo a partir de una tabla de tarifas."""
    tabla = json.dumps(tarifas, ensure_ascii=False)
    return f"""$tarifas = json_decode('{tabla}', true);
$clave = $data['tipo_persona'] ?? '';
${variable} = $tarifas[$clave] ?? 0;

return ${variable};"""


def php_documento(plantilla: str, variables: list[str]) -> str:
    """Arma un documento escapando toda variable de usuario. Cierra DOC-01."""
    declaradas = set(variables)
    usadas = set(_VARIABLE_EN_PLANTILLA.findall(plantilla))
    faltantes = sorted(usadas - declaradas)
    if faltantes:
        raise ValueError(
            f"la plantilla usa variables no declaradas: {', '.join(faltantes)}"
        )

    lineas = [
        f"${v} = htmlspecialchars($data['{v}'] ?? '', ENT_QUOTES, 'UTF-8');"
        for v in variables
    ]
    cuerpo = _VARIABLE_EN_PLANTILLA.sub(lambda m: f"' . ${m.group(1)} . '", plantilla)
    return "\n".join(lineas) + f"\n\nreturn '{cuerpo}';"


def _documento_gpm(id_, nombre, contenido, proceso_id, datos=None) -> dict:
    """La entidad Documento: 29 claves.
    Permite configuración básica de firma para simplificación.
    """
    datos = datos or {}
    return {
        "id": id_, "tipo": "blanco", "nombre": nombre, "contenido": contenido,
        "servicio": None, "servicio_url": None, "logo": None, "timbre": None,
        "firmador_nombre": datos.get("firmador_nombre"), 
        "firmador_cargo": datos.get("firmador_cargo"), 
        "firmador_servicio": None,
        "firmador_imagen": None, "validez": None, "hsm_configuracion_id": None,
        "proceso_id": str(proceso_id), 
        "subtitulo": datos.get("subtitulo"), 
        "titulo": datos.get("titulo"),
        "validez_habiles": None, "paper_size": "LETTER", "orientation_page": "portrait",
        "header": None, "footer": "1 de 1", "margin_top": 100, "margin_bottom": 100,
        "margin_left": 20, "margin_right": 20, "output": "pdf",
        "verify_code": None, "metadata": None,
    }


def _accion_gpm(id_, nombre, tipo, extra, proceso_id) -> dict:
    return {
        "id": id_, "nombre": nombre, "tipo": tipo,
        "extra": json.dumps(extra, ensure_ascii=False),
        "proceso_id": str(proceso_id), "request": None, "metadata": None,
    }


def construir_acciones(acciones: list[Accion], proceso_id: str, ids):
    """Traduce las acciones del manifiesto a Acciones y Documentos del .gpm."""
    salida_acciones, salida_documentos = [], []

    mapa_ids = {}

    for a in acciones:
        datos = a.model_dump()
        accion_id = next(ids)
        mapa_ids[a.nombre] = str(accion_id)
        
        if a.tipo == "folio":
            variable = datos.get("variable", "folio")
            # El contador se llavea por el nombre de la variable, no por proceso_id
            # (PLAT-4). 'inicial' no es expresable en la forma autentica: el conteo
            # arranca de dato_seguimiento, que administra la plataforma.
            php = php_folio(prefijo=datos.get("prefijo", "GPM"), variable=variable)
            extra = {"variable": variable, "expresion": php}
            salida_acciones.append(
                _accion_gpm(accion_id, a.nombre, "variable", extra, proceso_id)
            )

        elif a.tipo == "costo":
            variable = datos.get("variable", "costo")
            php = php_costo(variable=variable, tarifas=datos.get("tarifas", {}))
            extra = {"variable": variable, "expresion": php}
            salida_acciones.append(
                _accion_gpm(accion_id, a.nombre, "variable", extra, proceso_id)
            )

        elif a.tipo == "documento":
            plantilla = datos.get("plantilla", "")
            variables = list(datos.get("variables", []))
            php = php_documento(plantilla=plantilla, variables=variables)
            variable = datos.get("variable", "documento_contenido")
            extra = {"variable": variable, "expresion": php}
            salida_acciones.append(
                _accion_gpm(accion_id, a.nombre, "variable", extra, proceso_id)
            )
            salida_documentos.append(
                _documento_gpm(next(ids), a.nombre, f"@@{variable}", proceso_id, datos)
            )

        elif a.tipo == "notificacion":
            para = datos.get("para") or ""
            if not para:
                raise ValueError(
                    f"la notificacion '{a.nombre}' no declara destinatario ('para')"
                )
            extra = {
                "para": para,
                "cc": datos.get("cc", ""),
                "cco": datos.get("cco", ""),
                "tema": datos.get("asunto", ""),
                "contenido": datos.get("contenido", ""),
                "attach_files": datos.get("adjuntos", ""),
            }
            salida_acciones.append(
                _accion_gpm(accion_id, a.nombre, "enviar_correo", extra, proceso_id)
            )

    return salida_acciones, salida_documentos, mapa_ids
