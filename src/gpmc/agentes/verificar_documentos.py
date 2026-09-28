"""La verificacion de lo que el modelo propone sobre los documentos del tramite.

Aqui no hay modelo. Cada propuesta tiene que sostenerse en algo que ya esta
escrito: una frase literal del AS-IS o del TO-BE, o un campo que existe en el
manifiesto. Lo que no se sostiene no se corrige en silencio: la tarjeta queda
«sin destino» con el veredicto a la vista, y decide una persona.
"""
from gpmc.comparativa.documentos import (
    DESTINOS, MAX_MOTIVO, SIN_DESTINO, Documento, id_de)
from gpmc.extractores.as_is import requisitos_del_as_is
from gpmc.planeacion.registro import clave

# Una cita de dos letras «aparece» en cualquier documento.
_MINIMO_CITA = 3


def _esta(cita, texto_normalizado: str) -> bool:
    k = clave(cita if isinstance(cita, str) else "")
    return len(k) >= _MINIMO_CITA and k in texto_normalizado


def _evidencia(destino: str, clase: str, con_frase: bool) -> str:
    """El veredicto que deja la regla de evidencia; vacio si se cumple."""
    if destino == "conserva":
        return "" if clase == "archivo_ciudadano" else "evidencia_insuficiente"
    if destino == "consulta":
        return "" if (clase == "consulta" or con_frase) else "evidencia_insuficiente"
    if destino == "sistema":
        return "" if (clase in ("accion_documento", "archivo_otro") or con_frase) \
            else "evidencia_insuficiente"
    return "" if con_frase else "sin_fundamento"


def verificar(items: list, as_is: str, to_be: str, refs: list) -> tuple:
    antes, despues = clave(as_is), clave(to_be)
    por_nombre = {r.nombre: r for r in refs}
    salida, alertas, vistos, campos_usados = [], [], set(), set()

    for item in items or []:
        if not isinstance(item, dict) or not isinstance(item.get("nombre"), str) \
                or not item["nombre"].strip():
            alertas.append("respuesta_invalida")
            continue
        nombre, cita = item["nombre"].strip(), item.get("cita_as_is")
        if not _esta(cita, antes):
            # No existe en el AS-IS: no es un documento que pidiera el tramite.
            alertas.append("documento_inventado")
            continue
        doc = Documento(
            id=id_de(nombre, cita), nombre=nombre, cita_as_is=cita.strip(), origen="agente",
            motivo=str(item.get("motivo") or "").strip()[:MAX_MOTIVO],
            confianza=item.get("confianza") if item.get("confianza") in ("alta", "media", "baja")
            else "baja")
        doc.motivo_de = "ia" if doc.motivo else ""
        if clave(nombre) in vistos:
            alertas.append("duplicado")
            continue
        vistos.add(clave(nombre))

        destino = item.get("destino")
        frase, campo = item.get("cita_to_be"), item.get("campo")
        veredicto = ""
        if destino not in DESTINOS:
            veredicto = "destino_invalido"
        elif frase and not _esta(frase, despues):
            veredicto = "cita_inventada"
        elif campo and campo not in por_nombre:
            veredicto = "campo_inventado"
        else:
            clase = por_nombre[campo].clase if campo else ""
            veredicto = _evidencia(destino, clase, bool(frase))
            if not veredicto and campo and destino in ("conserva", "sistema") \
                    and campo in campos_usados:
                veredicto = "campo_repetido"

        if veredicto:
            alertas.append(veredicto)
            doc.veredicto = veredicto
            doc.destino = SIN_DESTINO
        else:
            doc.destino = destino
            doc.campo = campo or ""
            doc.cita_to_be = frase.strip() if frase else ""
            if campo and destino in ("conserva", "sistema"):
                campos_usados.add(campo)
        salida.append(doc)

    # Cobertura: el modelo puede partir una linea en varios documentos, pero no
    # puede hacer desaparecer ninguna.
    citas = [clave(d.cita_as_is) for d in salida]
    for req in requisitos_del_as_is(as_is):
        k = clave(req)
        if not k or any(c in k or k in c for c in citas):
            continue
        alertas.append("requisito_omitido")
        salida.append(Documento(id=id_de(req, req), nombre=req, cita_as_is=req,
                                veredicto="omitido_por_el_modelo"))
    return salida, alertas
