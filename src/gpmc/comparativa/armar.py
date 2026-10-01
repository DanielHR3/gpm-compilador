"""Cruza el AS-IS con el TO-BE y el manifiesto: la comparativa de antes y despues.

La pidio Simplificacion el 2026-09-28 para comprobar que un tramite si tuvo
reingenieria. Es una funcion pura y determinista: aqui no se llama a ningun
modelo. Cada valor dice de donde salio (contado, leido, declarado, propuesto o
sin dato), porque una cifra sin origen no sirve de evidencia.

Desde el 2026-10-01 puede recibir, ya verificado, lo que propone el agente
para los lados que el compilador no sabe contar (`propuestas`) y los puntos de
mejora (`mejoras`). Entran como datos: este modulo no importa de `agentes`.
"""
import dataclasses
import re
from dataclasses import dataclass, field
from typing import Optional

from gpmc.comparativa import documentos as docs_tramite
from gpmc.comparativa.propuestas import LADOS, mejoras_a_dicts
from gpmc.extractores.as_is import EstadoActual, casa
from gpmc.extractores.rediseno import Rediseno
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.manifiesto import Manifiesto
from gpmc.planeacion.registro import clave

METRICAS = (
    ("requisitos", "Requisitos documentales"),
    ("pasos", "Pasos del proceso"),
    ("actores", "Actores que intervienen"),
    ("sistemas", "Sistemas externos"),
    ("tiempo", "Tiempo de respuesta"),
    ("visitas", "Visitas presenciales"),
    ("capturas", "Capturas manuales del mismo dato"),
)
_NOMBRES = dict(METRICAS)
# Como nombra el equipo cada metrica en su «Presentacion Antes y Despues».
_RAICES = (("requisit", "requisitos"), ("paso", "pasos"), ("actor", "actores"),
           ("sistema", "sistemas"), ("tiempo", "tiempo"), ("visita", "visitas"),
           ("captura", "capturas"))
_CANTIDAD = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(.*?)\s*$")
# Mismas dos reglas del tablero (`web/tablero.py`): el prefijo no es parte del
# requisito y la fila de solo lectura no es un documento que entregue nadie.
_PREFIJO_DOC = "documento:"
_NO_ES_REQUISITO = "vista de solo lectura"
# La ficha de pago (el F7, la orden de pago, la linea de captura) es un insumo
# que emite la dependencia para que el ciudadano pague, aunque el ciudadano la
# suba: no es requisito. El comprobante de pago si lo es (respuesta de
# Simplificacion, 2026-10-01). Formas medidas en los Diccionarios del almacen.
_FICHA_DE_PAGO = re.compile(
    r"\b(formato|ficha|orden) de pago\b|\bformato f-?7\b|\bf-?7\b|l[ií]nea de captura|"
    r"referencia (bancaria|de pago)|pre-?recibo", re.I)


@dataclass
class Valor:
    texto: str = ""
    numero: Optional[float] = None
    unidad: str = ""
    origen: str = "sin_dato"


@dataclass
class Metrica:
    clave: str
    nombre: str
    antes: Valor
    despues: Valor
    diferencia: Optional[float] = None
    porcentaje: Optional[float] = None
    # La evidencia de un lado que propuso el agente: {motivo, ninguno, evidencia}.
    # Va aparte del `Valor` para que una cifra contada y una propuesta tengan la
    # misma forma y solo cambie su origen.
    propuesta_antes: Optional[dict] = None
    propuesta_despues: Optional[dict] = None


@dataclass
class Requisito:
    nombre: str
    destino: str
    fundamento: str = ""


@dataclass
class Comparativa:
    disponible: bool = True
    motivo: str = ""
    tramite: str = ""
    metricas: list = field(default_factory=list)
    requisitos: list = field(default_factory=list)
    pasos_antes: list = field(default_factory=list)
    tareas_despues: list = field(default_factory=list)
    fricciones: list = field(default_factory=list)
    cambios: list = field(default_factory=list)
    eliminaciones: list = field(default_factory=list)
    impacto: list = field(default_factory=list)
    autollenados: int = 0
    porcentaje_global: Optional[float] = None
    base_global: int = 0
    total_metricas: int = len(METRICAS)
    veredicto: str = "sin_medida"
    frase: str = ""
    huecos: list = field(default_factory=list)
    # El resumen de «Documentos del tramite», si alguien ya empezo a revisarlos.
    documentos: Optional[dict] = None
    # La tabla «Analisis de eliminacion» del TO-BE, fila por fila y contada.
    elementos: list = field(default_factory=list)
    resumen_elementos: Optional[dict] = None
    # Lo mismo que dicen las cifras, en frases: que bajo, que subio, que falta.
    resumen: list = field(default_factory=list)
    # «Que mas se puede simplificar»: lo propone el agente, verificado.
    mejoras: list = field(default_factory=list)


def clave_de_metrica(nombre: str) -> Optional[str]:
    k = clave(nombre)
    for raiz, c in _RAICES:
        if raiz in k:
            return c
    return None


def _singular(palabra: str) -> str:
    """«dias» y «dia», «habiles» y «habil», «meses» y «mes» son la misma
    unidad. No es convertir unidades: es no tropezar con el plural."""
    if len(palabra) > 4 and palabra.endswith("es") and palabra[-3] not in "aeiou":
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def _unidad(texto: str) -> str:
    return " ".join(_singular(p) for p in clave(texto).split())


def _valor(texto: str, origen: str) -> Valor:
    t = (texto or "").strip()
    if not t:
        return Valor()
    m = _CANTIDAD.match(t)
    if not m:
        return Valor(texto=t, origen=origen)
    return Valor(texto=t, numero=float(m.group(1).replace(",", ".")),
                 unidad=_unidad(m.group(2)), origen=origen)


def _contado(n: int) -> Valor:
    return Valor(texto=str(n), numero=float(n), origen="contado")


def _contado_si_hay(lista: list) -> Valor:
    # Una lista vacia es «no se leyo», no «hay cero»: el AS-IS pudo traerla en
    # una forma que el extractor no entiende.
    return _contado(len(lista)) if lista else Valor()


def _archivos(m: Manifiesto) -> list:
    """Los archivos que entrega el solicitante. Lo que sube otro actor es un
    producto del tramite, no un requisito (respuesta de Simplificacion,
    2026-10-01). Misma regla que `documentos.referencias`."""
    salida, vistos = [], set()
    del_solicitante = docs_tramite.pantallas_del_solicitante(m)
    for p in m.pantallas:
        if p.id not in del_solicitante:
            continue
        for c in p.campos:
            if c.tipo != "file":
                continue
            t = (c.etiqueta or c.nombre).strip()
            if t.lower().startswith(_PREFIJO_DOC):
                t = t[len(_PREFIJO_DOC):].strip()
            if not t or t.lower().startswith(_NO_ES_REQUISITO) or clave(t) in vistos \
                    or _FICHA_DE_PAGO.search(t):
                continue
            vistos.add(clave(t))
            salida.append(t)
    return salida


def _mezclar(rediseno: Rediseno, pantalla: Optional[dict]) -> dict:
    """Lo declarado, por clave y por lado. Gana la pantalla sobre el TO-BE:
    es lo ultimo que decidio una persona."""
    d = {}
    for nombre, antes, despues in rediseno.declaradas:
        k = clave_de_metrica(nombre)
        if k:
            d[k] = {"antes": antes.strip(), "despues": despues.strip()}
    for k, v in (pantalla or {}).items():
        if k not in _NOMBRES or not isinstance(v, dict):
            continue
        previo = d.get(k, {"antes": "", "despues": ""})
        d[k] = {lado: str(v.get(lado) or "").strip() or previo[lado]
                for lado in ("antes", "despues")}
    return d


def _de_propuesta(p) -> tuple:
    """(Valor, evidencia) de una propuesta. Sin evidencia no hay cifra: el
    agente no puede poner un numero que no se pueda abrir."""
    if not p.evidencias:
        return Valor(), None
    if p.texto:
        valor = _valor(p.texto, "propuesto")
    else:
        n = 0 if p.ninguno else len(p.evidencias)
        valor = Valor(str(n), float(n), "", "propuesto")
    return valor, {"motivo": p.motivo, "ninguno": p.ninguno,
                   "evidencia": [{"nombre": e.nombre, "cita": e.cita} for e in p.evidencias]}


def _metrica(k: str, antes: Valor, despues: Valor, declarado: dict,
             propuestas: Optional[dict] = None) -> Metrica:
    if declarado.get("antes"):
        antes = _valor(declarado["antes"], "declarado")
    if declarado.get("despues"):
        despues = _valor(declarado["despues"], "declarado")
    # Lo propuesto solo ocupa un lado que seguia vacio: no pisa lo contado, lo
    # leido ni lo que declaro una persona.
    evidencia = {"antes": None, "despues": None}
    lados = {"antes": antes, "despues": despues}
    for lado in LADOS:
        p = (propuestas or {}).get((k, lado))
        if p is not None and lados[lado].origen == "sin_dato":
            valor, ev = _de_propuesta(p)
            if ev is not None:
                lados[lado], evidencia[lado] = valor, ev
    antes, despues = lados["antes"], lados["despues"]
    dif = pct = None
    if (antes.numero is not None and despues.numero is not None
            and antes.unidad == despues.unidad):
        dif = antes.numero - despues.numero
        if antes.numero > 0:
            pct = round(dif / antes.numero * 100, 1)
    return Metrica(k, _NOMBRES[k], antes, despues, dif, pct,
                   evidencia["antes"], evidencia["despues"])


def _requisitos(estado: EstadoActual, archivos: list, eliminaciones: list) -> list:
    if not estado.requisitos:
        return []
    salida, usados = [], set()
    for req in estado.requisitos:
        casados = [a for a in archivos if casa(req, a)]
        if casados:
            usados.update(casados)
            salida.append(Requisito(req, "conservado", casados[0]))
            continue
        k = clave(req)
        fundamento = next((p.texto for p in eliminaciones if k and k in clave(p.texto)), "")
        # Sin una linea del equipo que lo nombre, el compilador no sabe si se
        # elimino o se olvido: «sin destino», nunca «eliminado» por omision.
        salida.append(Requisito(req, "eliminado" if fundamento else "sin_destino", fundamento))
    salida += [Requisito(a, "nuevo") for a in archivos if a not in usados]
    return salida


def _cifra(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def texto_cambio(pct: float) -> str:
    return f"{'−' if pct >= 0 else '+'}{_cifra(abs(pct))} %"


_CABEZA = {
    "reduce": "La reingeniería reduce",
    "mixto": "La reingeniería reduce unas métricas y aumenta otras",
    "no_reduce": "La reingeniería no reduce ninguna métrica medida",
}


def _veredicto(metricas: list) -> tuple:
    comparables = [m for m in metricas if m.porcentaje is not None]
    total = len(METRICAS)
    if len(comparables) < 2:
        return ("sin_medida", None, len(comparables),
                f"No se puede medir: solo {len(comparables)} de {total} métricas tienen "
                f"número en los dos lados. Declara las que faltan.")
    pct = round(sum(m.porcentaje for m in comparables) / len(comparables), 1)
    bajan = any(m.porcentaje > 0 for m in comparables)
    suben = any(m.porcentaje < 0 for m in comparables)
    veredicto = "mixto" if bajan and suben else "reduce" if bajan else "no_reduce"
    partes = "; ".join(
        f"{m.nombre.lower()} de {m.antes.texto} a {m.despues.texto} ({texto_cambio(m.porcentaje)})"
        for m in comparables)
    # Negativa quiere decir que, en promedio, las metricas medidas crecieron:
    # se dice con palabras para que nadie lea «−26 %» como una reduccion.
    cifra = f"{_cifra(pct)} %" if pct >= 0 else f"−{_cifra(abs(pct))} % (aumento neto)"
    frase = (f"{_CABEZA[veredicto]}: {partes}. Simplificación global: "
             f"{cifra} sobre {len(comparables)} de {total} métricas.")
    return veredicto, pct, len(comparables), frase


def _huecos(estado: EstadoActual, metricas: list, requisitos: list, veredicto: str) -> list:
    huecos = []
    if not estado.pasos:
        huecos.append(Hueco("por_confirmar", "CMP-01", "as_is",
                            "El AS-IS no trae una lista de pasos que se pueda leer: "
                            "los pasos de antes no se cuentan."))
    faltan = [m.nombre for m in metricas if m.despues.origen == "sin_dato"]
    if faltan:
        huecos.append(Hueco("por_confirmar", "CMP-02", "to_be",
                            "Falta el dato del después para: " + ", ".join(faltan) + "."))
    propuestas = [f"{m.nombre} ({_lados_propuestos(m)})" for m in metricas if _lados_propuestos(m)]
    if propuestas:
        huecos.append(Hueco("por_confirmar", "CMP-06", "to_be",
                            "Cifras propuestas por el agente a partir de frases del "
                            "expediente, sin revisar por una persona: "
                            + ", ".join(propuestas) + ". Abre cada una en «Antes y "
                            "después» y corrígela si la evidencia no la sostiene."))
    if veredicto == "no_reduce":
        huecos.append(Hueco("por_confirmar", "CMP-03", "to_be",
                            "Con las cifras leídas, la reingeniería no reduce ninguna de "
                            "las métricas medidas. Revisa las cuentas en la vista «Antes "
                            "y después» y corrígelas si el lector contó mal."))
    sueltos = [r.nombre for r in requisitos if r.destino == "sin_destino"]
    if sueltos:
        huecos.append(Hueco("por_confirmar", "CMP-04", "to_be",
                            "Requisitos del AS-IS que el TO-BE no conserva ni dice que "
                            "elimina: " + ", ".join(f"«{s}»" for s in sueltos) + "."))
    return huecos


def _lados_propuestos(m: Metrica) -> str:
    lados = [rotulo for rotulo, v in (("antes", m.antes), ("después", m.despues))
             if v.origen == "propuesto"]
    return " y ".join(lados)


def lados_sin_dato(c: Comparativa) -> list:
    """Los (metrica, lado) que el compilador no pudo llenar: lo que se le pide
    al agente. Se calcula sobre una comparativa armada SIN propuestas."""
    return [(m.clave, lado) for m in c.metricas
            for lado, v in (("antes", m.antes), ("despues", m.despues))
            if v.origen == "sin_dato"]


_CLASES_ELEMENTO = ("elimina", "conserva", "cambia", "sin_decision", "otro")
# (singular, plural) de cada clase, en el orden en que se cuenta la historia.
_VERBO_ELEMENTO = (
    ("elimina", "se elimina", "se eliminan"),
    ("cambia", "cambia", "cambian"),
    ("conserva", "se conserva", "se conservan"),
    ("sin_decision", "sigue sin decisión", "siguen sin decisión"),
    ("otro", "tiene otra respuesta", "tienen otra respuesta"),
)


def _resumen_elementos(elementos: list) -> Optional[dict]:
    if not elementos:
        return None
    cuenta = {k: sum(1 for e in elementos if e.clase == k) for k in _CLASES_ELEMENTO}
    return {"total": len(elementos), **cuenta}


def _enumerar(partes: list) -> str:
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def _resumen(metricas: list, cuenta: Optional[dict]) -> list:
    """Las cifras, dichas en frases para quien no va a leer siete tarjetas."""
    salida = []
    if cuenta:
        partes = [f"{cuenta[k]} {uno if cuenta[k] == 1 else varios}"
                  for k, uno, varios in _VERBO_ELEMENTO if cuenta[k]]
        n = cuenta["total"]
        cabeza = ("Del único elemento" if n == 1 else f"De los {n} elementos")
        salida.append({"clase": "elementos",
                       "texto": f"{cabeza} del trámite actual que revisó el equipo, "
                                f"{_enumerar(partes)}."})
    baja, sube, igual, sin_comparar, sin_dato = [], [], [], [], []
    for m in metricas:
        nombre = m.nombre.lower()
        vacios = [rotulo for rotulo, v in (("antes", m.antes), ("después", m.despues))
                  if v.origen == "sin_dato"]
        if len(vacios) == 2:
            sin_dato.append(nombre)
        elif vacios:
            sin_dato.append(f"{nombre} ({vacios[0]})")
        elif m.diferencia is None:
            sin_comparar.append(f"{nombre} ({m.antes.texto} → {m.despues.texto})")
        elif m.diferencia > 0:
            baja.append(f"{nombre}, de {m.antes.texto} a {m.despues.texto}")
        elif m.diferencia < 0:
            sube.append(f"{nombre}, de {m.antes.texto} a {m.despues.texto}")
        else:
            igual.append(f"{nombre} ({m.antes.texto})")
    for clase, rotulo, puntos in (
            ("baja", "Baja", baja), ("igual", "Queda igual", igual), ("sube", "Sube", sube),
            ("sin_comparar", "No se compara, porque las unidades no coinciden", sin_comparar),
            ("sin_dato", "Sin dato en el expediente", sin_dato)):
        if puntos:
            salida.append({"clase": clase, "texto": f"{rotulo}: {'; '.join(puntos)}."})
    return salida


def no_disponible(motivo: str) -> Comparativa:
    return Comparativa(disponible=False, motivo=motivo)


def comparar(estado: EstadoActual, rediseno: Rediseno, m: Manifiesto,
             declaradas: Optional[dict] = None,
             documentos: Optional[list] = None,
             propuestas: Optional[list] = None,
             mejoras: Optional[list] = None) -> Comparativa:
    d = _mezclar(rediseno, declaradas)
    por_lado = {(p.metrica, p.lado): p for p in propuestas or []}
    archivos = _archivos(m)
    actores = {t.actor for t in m.flujo.tareas if t.actor} or {p.actor for p in m.pantallas}
    base = {
        "requisitos": (_contado_si_hay(estado.requisitos), _contado(len(archivos))),
        "pasos": (_contado_si_hay(estado.pasos), _contado(len(m.flujo.tareas))),
        "actores": (Valor(), _contado(len(actores))),
        "sistemas": (_contado_si_hay(estado.sistemas), Valor()),
        "tiempo": (_valor(estado.tiempo, "leido"), Valor()),
        "visitas": (Valor(), Valor()),
        "capturas": (Valor(), Valor()),
    }
    revisados = docs_tramite.resumen(documentos, m) if documentos else None
    completo = bool(revisados and revisados["completo"])
    if completo:
        # Con todas las tarjetas decididas, la cuenta de requisitos deja de ser
        # un emparejado por subcadena y pasa a ser lo que reviso una persona.
        quedan = revisados["solicitados"]
        base["requisitos"] = (
            Valor(str(revisados["total"]), float(revisados["total"]), "", "revisado"),
            Valor(str(quedan), float(quedan), "", "revisado"))
    nombres_actor = {a.id: a.nombre for a in m.actores}
    metricas = [_metrica(k, base[k][0], base[k][1], d.get(k, {}), por_lado)
                for k, _ in METRICAS]
    requisitos = [] if completo else _requisitos(estado, archivos, rediseno.eliminaciones)
    veredicto, pct, n, frase = _veredicto(metricas)
    con_propuesta = sum(1 for x in metricas
                        if x.porcentaje is not None and _lados_propuestos(x))
    if con_propuesta:
        # La cifra global nunca viaja sin decir cuanto de ella interpreto un modelo.
        frase += (f" {con_propuesta} de esas {n} {'usa' if con_propuesta == 1 else 'usan'} "
                  f"cifras propuestas por el agente.")
    cuenta = _resumen_elementos(rediseno.elementos)
    return Comparativa(
        tramite=m.tramite.nombre,
        metricas=metricas,
        requisitos=requisitos,
        pasos_antes=list(estado.pasos),
        tareas_despues=[{"nombre": t.nombre, "actor": nombres_actor.get(t.actor, t.actor or "")}
                        for t in m.flujo.tareas],
        fricciones=list(estado.fricciones),
        cambios=[p.titulo for p in rediseno.cambios],
        eliminaciones=[p.titulo for p in rediseno.eliminaciones],
        impacto=[p.titulo for p in rediseno.impacto],
        autollenados=sum(len(c.autollena) for p in m.pantallas for c in p.campos),
        porcentaje_global=pct,
        base_global=n,
        veredicto=veredicto,
        frase=frase,
        huecos=(_huecos(estado, metricas, requisitos, veredicto)
                + docs_tramite.avisos(documentos or [])),
        documentos=revisados,
        elementos=[dataclasses.asdict(e) for e in rediseno.elementos],
        resumen_elementos=cuenta,
        resumen=_resumen(metricas, cuenta),
        mejoras=mejoras_a_dicts(mejoras or []),
    )


def a_dict(c: Comparativa) -> dict:
    return dataclasses.asdict(c)
