"""La verificacion de lo que el modelo propone para la comparativa.

Aqui no hay modelo. El agente no entrega cifras: entrega frases, y la cifra es
cuantas sobreviven estas reglas. Una frase sobrevive si esta escrita en el
documento que corresponde al lado (AS-IS para el antes, TO-BE para el despues)
y habla de lo que dice medir.

Tres reglas salieron de la prueba en vivo del 2026-10-01 sobre un TO-BE de
25 000 caracteres, donde el modelo copio mal 4 de 13 frases:

- Las etiquetas HTML no son texto: el modelo lee a traves de los `<br/>` de un
  nodo del diagrama.
- De una cita mal copiada en las orillas se acepta el tramo literal mas largo,
  y lo que se guarda es ESE tramo tal como esta en el documento, nunca lo que
  escribio el modelo.
- El «antes» solo se sostiene en el AS-IS, aunque el TO-BE describa el problema.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from gpmc.comparativa.propuestas import (
    ACCIONES, TIPOS_DE_MEJORA, Evidencia, Mejora, Propuesta, id_de_mejora)
from gpmc.planeacion.registro import clave

_PALABRA = re.compile(r"[^\W_]+")
# Acotada: un `<` suelto en la prosa («plazo < 5 dias») no se come media linea.
_ETIQUETA = re.compile(r"<[^<>\n]{1,40}>")
_MARCADOR_DE_LINEA = re.compile(r"^\s*(?:[-*|]|\d+[.)])\s*")
# Un enlace de la boveda, `[[carpeta/Nombre|alias]]`: lo que se lee es el
# alias o, sin alias, el nombre sin su ruta.
_ENLACE = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")

# Una cita vale si su tramo literal tiene al menos cuatro palabras y cubre la
# mayor parte de lo que cito el modelo: cuatro palabras sueltas en comun
# («de la solicitud y») aparecen en cualquier documento.
MINIMO_TRAMO = 4
COBERTURA = 0.6
MAX_MOTIVO = 300
MAX_LINEA = 200
MAX_MEJORAS = 6
MAX_TITULO, MAX_PROPUESTA, MAX_BENEFICIO = 120, 400, 300

# De que tiene que hablar la frase para contar en cada metrica. Son raices de
# palabra: «acud» cubre acude, acudir, acudio. Que la frase exista no basta
# (misma leccion que `verificar_documentos._comparten`).
_HABLA_DE = {
    "visitas": ("present", "acud", "ventanilla", "oficina", "banco", "sucursal", "traslad",
                "fisic", "entreg", "recog", "llev", "modulo", "visita"),
    "capturas": ("captur", "llen", "escrib", "requisit", "anot", "tecle", "transcrib",
                 "autocomplet"),
    # Solo se usa para un «ninguno»: un sistema con nombre se sostiene en que
    # el nombre esta escrito, no en el vocabulario de la frase.
    "sistemas": ("sistema", "plataforma", "base", "excel", "herramienta", "software",
                 "aplicac"),
}
# Una captura REPETIDA: ademas de hablar de capturar, la frase tiene que decir
# que se hace otra vez. «La placa que se registro» habla de un dato, no de
# escribirlo dos veces (prueba en vivo, 2026-10-01).
_DICE_REPETIR = ("vuelve", "vuelven", "volver", "de nuevo", "otra vez", "veces", "nuevamente",
                 "duplic", "repit", "repet", "doble", "mism")
# Un plazo que el propio documento da por no fijado no es un plazo.
_DICE_PENDIENTE = ("pendiente", "por confirmar", "por definir", "sin definir", "no fija",
                   "no se fija")
# Lo que dice una frase que afirma que YA NO HAY, por metrica. Raices y giros.
# «Digital» dice que ya no hay visitas, pero no que no haya capturas repetidas
# ni sistemas (prueba en vivo, 2026-10-01).
_NADA = ("cero", "ningun", "elimin", "ya no", "sin ")
_DICE_NINGUNO = {
    "visitas": _NADA + ("digital", "linea", "distancia", "100"),
    "capturas": _NADA + ("automat", "autocomplet", "una sola vez"),
    "sistemas": _NADA,
}
# En que metricas tiene sentido un cero: no hay tramite sin actores ni sin plazo.
_ADMITE_NINGUNO = ("sistemas", "visitas", "capturas")
# Limites de diseño del metodo de Simplificacion (2026-10-01). Una mejora que
# los rompe no se propone: no es una opcion que el equipo pueda tomar.
# - El ciudadano no tiene firma electronica avanzada.
# - Siempre dos formas de pagar: en linea, o en el banco con comprobante.
_ROMPE_LIMITES = (
    re.compile(r"\be\s?\.?\s?firma\b|firma electr[oó]nica avanzada", re.I),
    re.compile(r"(elimin|quit|suprim)\w*\s+(el\s+)?pago\s+(en|por)\s+(el\s+)?banco"
               r"|solo\s+(el\s+)?pago\s+en\s+l[ií]nea", re.I),
)
# El sistema no se conecta con los sistemas internos de la dependencia: lo que
# lo necesite es «a futuro» aunque el modelo no lo marque.
_SISTEMA_INTERNO = re.compile(
    r"padr[oó]n|base de datos|sistema interno|sistemas internos|tesorer[ií]a|"
    r"historial de|registro (estatal|de la)|integra(r|ci[oó]n) con|"
    # Formas medidas en la prueba en vivo de mejoras-v2 (Reposicion, 2026-10-01).
    r"registros? (digital|interno)|cuenta con el registro|"
    r"bus[cq]\w*\b.{0,60}\bautom[aá]tic|consult\w* (directamente|autom[aá]tic)", re.I)

# La metrica es «sistemas EXTERNOS»: la plataforma donde corre el tramite no lo
# es. Sin esto el despues de un tramite digitalizado siempre sumaba uno.
_PLATAFORMA_PROPIA = "gpm"
# Donde la evidencia es el nombre (esta escrito o no) y no la frase.
_POR_NOMBRE = ("actores", "sistemas")
_METRICAS = ("requisitos", "pasos", "actores", "sistemas", "tiempo", "visitas", "capturas")


@dataclass
class Indice:
    """Un documento partido en palabras, cada una con su lugar en el texto:
    asi el tramo que casa se puede devolver tal como esta escrito."""
    texto: str
    palabras: list = field(default_factory=list)
    inicios: list = field(default_factory=list)
    fines: list = field(default_factory=list)
    donde: dict = field(default_factory=dict)


def _normal(palabra: str) -> str:
    return clave(palabra).replace(" ", "")


def _palabras(texto) -> list:
    if not isinstance(texto, str):
        return []
    sin = _sin_ruta(_ETIQUETA.sub(" ", texto))
    return [n for n in (_normal(m.group()) for m in _PALABRA.finditer(sin)) if n]


def _sin_ruta(texto: str) -> str:
    """Los enlaces de la boveda, reducidos a lo que se lee y sin mover nada de
    sitio: la ruta y los corchetes se cambian por espacios del mismo largo."""
    def visible(m):
        ruta, alias = m.group(1), m.group(2)
        if alias is not None:
            return " " * (len(ruta) + 3) + alias + "  "
        corte = ruta.rfind("/") + 1
        return " " * (corte + 2) + ruta[corte:] + "  "
    return _ENLACE.sub(visible, texto)


def indexar(texto: str) -> Indice:
    # La etiqueta se cambia por espacios del mismo largo: las posiciones siguen
    # siendo las del documento original.
    sin = _sin_ruta(_ETIQUETA.sub(lambda m: " " * len(m.group()), texto or ""))
    idx = Indice(texto=sin)
    for m in _PALABRA.finditer(sin):
        n = _normal(m.group())
        if not n:
            continue
        idx.donde.setdefault(n, []).append(len(idx.palabras))
        idx.palabras.append(n)
        idx.inicios.append(m.start())
        idx.fines.append(m.end())
    return idx


def _limpio(texto: str) -> str:
    t = re.sub(r"\s+", " ", re.sub(r"[*`]", "", texto)).strip()
    # Los corchetes de un enlace se cambiaron por espacios: no dejan hueco
    # antes del signo que los seguia.
    return re.sub(r" ([,.;:)])", r"\1", t)


def _texto(idx: Indice, a: int, b: int) -> str:
    """Las palabras a..b (inclusive) tal como estan en el documento."""
    fin = idx.fines[b]
    tramo = idx.texto[idx.inicios[a]:fin]
    # El tramo acaba en una palabra y deja fuera el signo que la cierra:
    # «Reposicion (1» se lee como un error de copia. Se toma el parentesis.
    if tramo.count("(") > tramo.count(")") and idx.texto[fin:fin + 1] == ")":
        tramo += ")"
    return _limpio(tramo)


def _tramo(cita, idx: Indice) -> Optional[tuple]:
    """(primera, ultima) palabra del documento del tramo mas largo que comparte
    con la cita, o None si no alcanza para sostenerla."""
    c = _palabras(cita)
    mejor, donde = 0, -1
    for i, palabra in enumerate(c):
        for j in idx.donde.get(palabra, ()):
            # Solo se extiende desde donde empieza una coincidencia.
            if i and j and c[i - 1] == idx.palabras[j - 1]:
                continue
            n = 0
            while i + n < len(c) and j + n < len(idx.palabras) \
                    and c[i + n] == idx.palabras[j + n]:
                n += 1
            if n > mejor:
                mejor, donde = n, j
    if mejor < MINIMO_TRAMO or mejor < COBERTURA * len(c):
        return None
    return donde, donde + mejor - 1


def tramo_literal(cita, idx: Indice) -> str:
    t = _tramo(cita, idx)
    return _texto(idx, *t) if t else ""


def _aparece(nombre, idx: Indice) -> Optional[tuple]:
    """Donde esta escrito `nombre`, entero y seguido. Un nombre de una o dos
    letras «aparece» en cualquier documento y no cuenta."""
    n = _palabras(nombre)
    if not n or not any(len(p) >= 3 or p.isdigit() for p in n):
        return None
    for j in idx.donde.get(n[0], ()):
        if idx.palabras[j:j + len(n)] == n:
            return j, j + len(n) - 1
    return None


def _linea_de(idx: Indice, a: int) -> str:
    ini = idx.texto.rfind("\n", 0, idx.inicios[a]) + 1
    fin = idx.texto.find("\n", idx.inicios[a])
    linea = idx.texto[ini:fin if fin >= 0 else len(idx.texto)]
    return _limpio(_MARCADOR_DE_LINEA.sub("", linea)).strip("| ")[:MAX_LINEA]


def _habla_de(metrica: str, frase: str) -> bool:
    raices = _HABLA_DE.get(metrica)
    if not raices:
        return True
    return any(p.startswith(raices) for p in clave(frase).split())


def _dice(giros: tuple, frase: str) -> bool:
    """Si la frase trae alguno de los giros, al principio de una palabra."""
    k = f" {clave(frase)} "
    return any(f" {giro}" in k for giro in giros)


def _dice_ninguno(metrica: str, frase: str) -> bool:
    return _dice(_DICE_NINGUNO.get(metrica, _NADA), frase)


def _elementos(item: dict) -> list:
    return [(e["nombre"].strip(), e.get("cita"))
            for e in item.get("elementos") or []
            if isinstance(e, dict) and isinstance(e.get("nombre"), str) and e["nombre"].strip()]


def _ninguno(metrica: str, elementos: list, idx: Indice) -> Optional[Evidencia]:
    if metrica not in _ADMITE_NINGUNO:
        return None
    for nombre, cita in elementos:
        frase = tramo_literal(cita, idx)
        if frase and _habla_de(metrica, frase) and _dice_ninguno(metrica, frase):
            return Evidencia(nombre, frase)
    return None


def _tiempo(elementos: list, idx: Indice, alertas: list) -> tuple:
    """Un solo plazo, con cifra, escrito tal cual en el documento."""
    for k, (nombre, cita) in enumerate(elementos):
        if not any(c.isdigit() for c in nombre):
            alertas.append("tiempo_sin_cifra")
            continue
        donde = _aparece(nombre, idx)
        if donde is None:
            alertas.append("nombre_inventado")
            continue
        plazo = _texto(idx, *donde)
        frase = tramo_literal(cita, idx)
        if not frase or clave(plazo) not in clave(frase):
            frase = _linea_de(idx, donde[0])
        if _dice(_DICE_PENDIENTE, frase) or _dice(_DICE_PENDIENTE, _linea_de(idx, donde[0])):
            alertas.append("tiempo_pendiente")
            continue
        alertas += ["duplicado"] * (len(elementos) - k - 1)
        return plazo, [Evidencia(plazo, frase)]
    return "", []


def _por_nombre(metrica: str, elementos: list, idx: Indice, alertas: list) -> list:
    salida, vistos = [], []
    for nombre, cita in elementos:
        k = f" {clave(nombre)} "
        if metrica == "sistemas" and f" {_PLATAFORMA_PROPIA} " in k:
            alertas.append("plataforma_propia")
            continue
        # «Expediente Digital» y «Expediente Digital Ciudadano» son el mismo
        # sistema escrito corto y largo: uno contiene al otro.
        if any(k in v or v in k for v in vistos):
            alertas.append("duplicado")
            continue
        donde = _aparece(nombre, idx)
        if donde is None:
            alertas.append("nombre_inventado")
            continue
        vistos.append(k)
        # La evidencia es que el nombre esta escrito. Si la frase del modelo no
        # se sostiene, se enseña la linea del documento donde aparece.
        salida.append(Evidencia(nombre, tramo_literal(cita, idx) or _linea_de(idx, donde[0])))
    return salida


def _por_frase(metrica: str, elementos: list, idx: Indice, alertas: list) -> list:
    salida, vistas = [], set()
    for nombre, cita in elementos:
        frase = tramo_literal(cita, idx)
        if not frase:
            alertas.append("cita_inventada")
        elif not _habla_de(metrica, frase) \
                or (metrica == "capturas" and not _dice(_DICE_REPETIR, frase)):
            alertas.append("cita_ajena")
        elif clave(frase) in vistas:
            alertas.append("duplicado")
        else:
            vistas.add(clave(frase))
            salida.append(Evidencia(nombre, frase))
    return salida


def verificar_evidencia(items: list, as_is: str, to_be: str, faltan: list) -> tuple:
    """(propuestas, alertas). Solo entran los lados de `faltan`, y un lado que
    se queda sin evidencia no es una propuesta: sigue «sin dato»."""
    indices = {"antes": indexar(as_is), "despues": indexar(to_be)}
    pedidos, hechos = set(faltan or []), set()
    salida, alertas = [], []
    for item in items or []:
        if not isinstance(item, dict) or not isinstance(item.get("metrica"), str) \
                or item.get("lado") not in indices:
            alertas.append("respuesta_invalida")
            continue
        metrica, lado = item["metrica"], item["lado"]
        if metrica not in _METRICAS or (metrica, lado) not in pedidos \
                or (metrica, lado) in hechos:
            alertas.append("lado_no_pedido")
            continue
        idx, elementos = indices[lado], _elementos(item)
        motivo = str(item.get("motivo") or "").strip()[:MAX_MOTIVO]
        propuesta = Propuesta(metrica, lado, motivo=motivo)
        if item.get("ninguno") is True:
            evidencia = _ninguno(metrica, elementos, idx)
            if evidencia is None:
                alertas.append("ninguno_sin_frase")
                continue
            propuesta.ninguno, propuesta.evidencias = True, [evidencia]
        elif metrica == "tiempo":
            propuesta.texto, propuesta.evidencias = _tiempo(elementos, idx, alertas)
        elif metrica in _POR_NOMBRE:
            propuesta.evidencias = _por_nombre(metrica, elementos, idx, alertas)
        else:
            propuesta.evidencias = _por_frase(metrica, elementos, idx, alertas)
        if propuesta.evidencias:
            hechos.add((metrica, lado))
            salida.append(propuesta)
    return salida, alertas


def _cadena(item: dict, k: str, tope: int) -> str:
    v = item.get(k)
    return v.strip()[:tope] if isinstance(v, str) else ""


def verificar_mejoras(items: list, as_is: str, to_be: str, refs: list, servicios) -> tuple:
    """(mejoras, alertas). Un punto de mejora entra si se apoya en un campo
    que existe en el manifiesto o en una frase literal del bloque que dice su
    `fuente`. Un servicio que no esta en el catalogo publico no se promete: el
    punto queda rotulado «requiere convenio»."""
    indices = {"as_is": indexar(as_is), "to_be": indexar(to_be)}
    por_nombre = {r.nombre: r for r in refs or []}
    publicos = set(servicios or ())
    salida, alertas, vistos = [], [], set()
    for item in items or []:
        if not isinstance(item, dict):
            alertas.append("respuesta_invalida")
            continue
        titulo = _cadena(item, "titulo", MAX_TITULO)
        propuesta = _cadena(item, "propuesta", MAX_PROPUESTA)
        if not titulo or not propuesta:
            alertas.append("respuesta_invalida")
            continue
        tipo = item.get("tipo") if item.get("tipo") in TIPOS_DE_MEJORA else "friccion"
        if any(r.search(f"{titulo} {propuesta}") for r in _ROMPE_LIMITES):
            alertas.append("fuera_de_limites")
            continue

        campo = item.get("campo") if isinstance(item.get("campo"), str) else ""
        if campo and campo not in por_nombre:
            alertas.append("campo_inventado")
            campo = ""
        fuente = item.get("fuente") if item.get("fuente") in indices else ""
        cita = ""
        if item.get("cita"):
            # Una fuente que el modelo no dijo bien se busca en los dos bloques.
            for f in ([fuente] if fuente else ["to_be", "as_is"]):
                cita = tramo_literal(item["cita"], indices[f])
                if cita:
                    fuente = f
                    break
            if not cita:
                alertas.append("cita_inventada")
        if not cita:
            fuente = ""
        if not campo and not cita:
            alertas.append("mejora_sin_evidencia")
            continue

        ident = id_de_mejora(tipo, campo, cita, titulo)
        if ident in vistos:
            alertas.append("duplicado")
            continue
        vistos.add(ident)

        servicio = item.get("servicio") if isinstance(item.get("servicio"), str) else ""
        requiere = ""
        if servicio and servicio in publicos:
            requiere = "servicio_publico"
        elif servicio:
            alertas.append("servicio_fuera_del_catalogo")
            servicio, requiere = "", "convenio"
        elif item.get("requiere_convenio") is True or _SISTEMA_INTERNO.search(propuesta):
            requiere = "convenio"

        salida.append(Mejora(
            id=ident, titulo=titulo, tipo=tipo, propuesta=propuesta,
            beneficio=_cadena(item, "beneficio", MAX_BENEFICIO),
            cita=cita, fuente=fuente, campo=campo,
            etiqueta_campo=por_nombre[campo].etiqueta if campo else "",
            servicio=servicio, requiere=requiere,
            accion=item.get("accion") if item.get("accion") in ACCIONES else ""))
    return salida[:MAX_MEJORAS], alertas
