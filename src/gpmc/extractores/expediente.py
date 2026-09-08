"""Orquesta los tres extractores sobre la carpeta de un expediente.

Cada extractor es independiente: si uno falla, lo suyo se convierte en hueco y
los demas siguen. La herramienta siempre produce algo revisable.
"""

from typing import Optional
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from gpmc.extractores import diccionario as ext_dicc
from gpmc.extractores import mermaid as ext_mmd
from gpmc.extractores import metadatos as ext_meta
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.integraciones import resolver as _resolver_catalogo
from gpmc.nucleo.integraciones import requiere_token as _requiere_token
from gpmc.nucleo.limites import LIMITE_FORMULARIO_NOMBRE as _CAP_NOMBRE
from gpmc.nucleo.manifiesto import (
    Actor, Condicion, Conexion, Flujo, Manifiesto, Pantalla, Tarea,
)

_BLOQUE_MERMAID = re.compile(r"```mermaid(.*?)```", re.S)


def _mapear_nodos_a_pantallas(nodos_tarea, pantallas):
    """Casa cada nodo 'tarea' del Mermaid con una pantalla del Diccionario por
    nombre normalizado. Acepta el prefijo de carril: 'Area: Cotiza' casa con la
    pantalla 'Cotiza'. Devuelve {id_nodo: pantalla} o None si no casan 1:1."""
    if len(nodos_tarea) != len(pantallas):
        return None
    por_nombre = {ext_dicc._babel(p.nombre): p for p in pantallas}
    mapa = {}
    for n in nodos_tarea:
        p = por_nombre.get(ext_dicc._babel(n.texto))
        if p is None and ":" in n.texto:
            p = por_nombre.get(ext_dicc._babel(n.texto.split(":", 1)[1]))
        if p is None:
            return None
        mapa[n.id] = p
    if len({id(p) for p in mapa.values()}) != len(pantallas):
        return None  # dos nodos apuntan a la misma pantalla
    return mapa


def _valor_de_arista(etiqueta, campo):
    """La etiqueta de una arista que sale de una compuerta tiene que ser un valor
    del catalogo del campo que decide (por valor tecnico o por etiqueta visible),
    o 'Si'/'No'. Devuelve el valor tecnico, o None si no resuelve."""
    if not etiqueta:
        return None
    e = ext_dicc._babel(etiqueta)
    for o in getattr(campo, "catalogo", []) or []:
        if e in (ext_dicc._babel(o.valor), ext_dicc._babel(o.etiqueta)):
            return o.valor
    if e in ("si", "no"):
        return e
    return None


def _flujo_ramificado(rm, pantallas):
    """Construye tareas y conexiones NO lineales desde el Mermaid, y solo si es
    seguro (spec 2026-09-03, Parte 2). Devuelve (tareas, conexiones, parejas) o
    None — y entonces el flujo sigue saliendo lineal, como antes.

    Condiciones, todas obligatorias:
      1. Cada nodo 'tarea' casa 1:1 por nombre con una pantalla del Diccionario.
      2. Cada compuerta nombra exactamente un @@campo, y ese campo existe.
      3. Cada arista que sale de una compuerta trae etiqueta, y esa etiqueta
         resuelve a un valor del catalogo del campo (o Si/No).
      4. Toda compuerta esta alimentada por una tarea, y sus ramas van a tareas
         (no a inicio/fin ni a otra compuerta).
    Si algo falla, se devuelve None: no se adivina.
    """
    nodos_tarea = [n for n in rm.nodos if n.clase_nodo == "tarea"]
    mapa = _mapear_nodos_a_pantallas(nodos_tarea, pantallas)
    if mapa is None:
        return None

    ids_if = {n.id for n in rm.nodos if n.clase_nodo == "inicio_fin"}
    compuertas = {n.id: n for n in rm.nodos if n.clase_nodo == "compuerta"}
    campos = {c.nombre: c for p in pantallas for c in p.campos}

    for g in compuertas.values():
        if len(set(g.campos)) != 1 or g.campos[0] not in campos:
            return None

    utiles = [a for a in rm.aristas if a.de not in ids_if and a.a not in ids_if]

    # Predecesor (una tarea) de cada compuerta.
    pred_de = {}
    for a in utiles:
        if a.a in compuertas:
            if a.de not in mapa:
                return None
            pred_de[a.a] = a.de
    if set(pred_de) != set(compuertas):
        return None

    conexiones = []
    for a in utiles:
        if a.de in compuertas:
            if a.a not in mapa:
                return None  # rama de compuerta a inicio/fin u otra compuerta
            campo = campos[compuertas[a.de].campos[0]]
            valor = _valor_de_arista(a.etiqueta, campo)
            if valor is None:
                return None
            conexiones.append(Conexion(
                de=pred_de[a.de], a=a.a,
                cuando=Condicion(campo=campo.nombre, igual=valor),
            ))
        elif a.de in mapa and a.a in mapa:
            conexiones.append(Conexion(de=a.de, a=a.a))
        elif a.de in mapa and a.a in compuertas:
            pass  # tarea -> compuerta: la conexion real ya se emitio arriba
        else:
            return None

    entra_if = {a.a for a in rm.aristas if a.de in ids_if}
    sale_if = {a.de for a in rm.aristas if a.a in ids_if}
    entra = {a.a for a in utiles}
    sale = {a.de for a in utiles}
    tareas = []
    for n in nodos_tarea:
        p = mapa[n.id]
        tareas.append(Tarea(
            id=n.id, nombre=(p.nombre or n.texto)[:_CAP_NOMBRE], actor=p.actor,
            inicial=(n.id in entra_if or n.id not in entra),
            terminal=(n.id in sale_if or n.id not in sale),
            pantallas=[p.id],
        ))
    if not any(t.inicial for t in tareas) or not any(t.terminal for t in tareas):
        return None

    parejas = [(n.id, mapa[n.id].nombre) for n in nodos_tarea]
    return tareas, conexiones, parejas


@dataclass
class Resultado:
    manifiesto: Optional[Manifiesto] = None
    huecos: list[Hueco] = field(default_factory=list)


class SinPermiso(Exception):
    """macOS niega el acceso a ~/Documents y ~/Desktop salvo autorizacion
    expresa. El archivo existe, exists() dice True, y la lectura revienta con
    un error que a un analista no le dice nada."""


def _normalizar(nombre: str) -> str:
    """Nombre de archivo -> forma canónica para comparar. Quita acentos, el
    prefijo de orden ('1.-', '3) '), y sufijos de versión/copia (' 1', ' v2',
    ' (2)', ' final', ' copia'). Sin esto, 'Propuesta TO-BE 1.md' no casaba
    con 'Propuesta TO-BE' porque la comparación incluía la extensión."""
    t = unicodedata.normalize("NFKD", nombre or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"\.md$", "", t)
    # El prefijo de orden se recorta ANTES de colapsar separadores: necesita ver
    # la puntuación cruda ('1.-', '3)') que el colapso convertiría en espacio.
    t = re.sub(r"^\s*\d+\s*[.)\-]+\s*", "", t)
    t = re.sub(r"[\s._\-]+", " ", t).strip()
    for _ in range(3):                                     # sufijos, posiblemente apilados
        nuevo = re.sub(r"\s*(v?\d+|final|copia|\(\d+\))$", "", t).strip()
        if nuevo == t:
            break
        t = nuevo
    return t


def _buscar_insumo(carpeta: Path, claves: list[str]) -> "tuple[Optional[Path], list[Hueco]]":
    """Devuelve (ruta_o_None, huecos). Solo considera archivos .md. Si varios
    casan, no adivina: devuelve None y un hueco INS-02."""
    claves_norm = [_normalizar(k) for k in claves]
    candidatos = []
    for archivo in sorted(carpeta.iterdir()):
        if not archivo.is_file() or archivo.suffix.lower() != ".md":
            continue
        stem = _normalizar(archivo.name)
        if any(k in stem for k in claves_norm):
            candidatos.append(archivo)
    if not candidatos:
        return None, []
    if len(candidatos) > 1:
        nombres = ", ".join(a.name for a in candidatos)
        return None, [Hueco(
            "falta_dato", "INS-02", "",
            f"{len(candidatos)} candidatos para '{claves[0]}': {nombres} — confirma cuál",
        )]
    return candidatos[0], []


def _leer(ruta: Path) -> str:
    """Lee el archivo ya resuelto. SinPermiso traduce el bloqueo de TCC de
    macOS a algo accionable para un analista."""
    try:
        return ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Un .md guardado en Latin-1 / Windows-1252 (Word, editores viejos).
        # Se recupera con reemplazo en vez de reventar con un traceback: el
        # extractor sigue y lo que no se lea bien saldrá como hueco.
        return ruta.read_text(encoding="utf-8", errors="replace")
    except PermissionError as exc:
        raise SinPermiso(
            f"macOS no permite leer '{ruta}'.\n\n"
            "El archivo existe, pero el sistema bloquea el acceso a las carpetas "
            "Documentos, Escritorio y Descargas.\n\n"
            "Solucion: Ajustes del Sistema > Privacidad y seguridad > Acceso total al "
            "disco, y autorizar la aplicacion desde la que se ejecuta (Terminal, o el "
            "navegador si se usa el asistente web).\n\n"
            "Alternativa: mover el expediente a una carpeta fuera de esas tres."
        ) from exc


def extraer_expediente(carpeta: Path) -> Resultado:
    carpeta = Path(carpeta)
    r = Resultado()

    ruta_as_is, h_as_is = _buscar_insumo(carpeta, ["Análisis AS-IS", "AS IS"])
    ruta_to_be, h_to_be = _buscar_insumo(carpeta, ["Propuesta TO-BE", "TO BE"])
    ruta_dicc, h_dicc = _buscar_insumo(carpeta, ["Diccionario de Datos", "Diccionario"])
    r.huecos += h_as_is + h_to_be + h_dicc

    as_is = _leer(ruta_as_is) if ruta_as_is else ""
    to_be = _leer(ruta_to_be) if ruta_to_be else ""
    dicc = _leer(ruta_dicc) if ruta_dicc else ""

    if not dicc:
        r.huecos.append(Hueco(
            "bloqueante", "INS-03", "",
            "no se encontró el Diccionario de Datos: sin él no hay pantallas",
        ))
        return r
    if not to_be:
        r.huecos.append(Hueco(
            "bloqueante", "INS-01", "",
            "no se encontró la Propuesta TO-BE: el flujo sale lineal, sin ramificar",
        ))

    meta = ext_meta.extraer(as_is, to_be, nombre_carpeta=carpeta.name)
    r.huecos += meta.huecos
    
    # Validacion de concordancia de insumos (flexible)
    def _sacar_titulo(texto: str, patron: str) -> str:
        m = re.search(patron, texto or "", re.M | re.I)
        return _normalizar(m.group(1).strip()) if m else ""
        
    tit_as = _sacar_titulo(as_is, r"^#\s+An[aá]lisis AS-?IS\s*[—\-–]\s*(.+?)\s*$")
    tit_tb = _sacar_titulo(to_be, r"^#\s+Propuesta TO-?BE\s*[—\-–]\s*(.+?)\s*$")
    tit_dic = _sacar_titulo(dicc, r"^#\s+Diccionario de Datos\s*[—\-–]\s*(.+?)\s*$")
    
    def _palabras(t: str) -> set:
        # Extrae palabras de 4 o más letras para ignorar preposiciones ("de", "en", "el")
        return set(re.findall(r'\b\w{4,}\b', t)) if t else set()

    p_as = _palabras(tit_as)
    p_tb = _palabras(tit_tb)
    p_dic = _palabras(tit_dic)
    
    # Comparamos solo los archivos que sí traen título H1 válido
    conjuntos = [p for p in (p_as, p_tb, p_dic) if p]
    
    if len(conjuntos) > 1:
        # Buscamos si existe al menos UNA palabra significativa en común entre todos.
        # En "Alta de Avisos de Testamento" y "Digitalización de Alta de Avisos en GPM",
        # la intersección tendría "alta", "avisos", "testamento".
        interseccion = conjuntos[0].intersection(*conjuntos[1:])
        if not interseccion:
            nombres_encontrados = " | ".join(t for t in (tit_as, tit_tb, tit_dic) if t)
            r.huecos.append(Hueco(
                "falta_dato", "INS-04", "archivos",
                f"Los títulos de los archivos no parecen coincidir en absoluto "
                f"({nombres_encontrados}). Revisa que no hayas mezclado insumos de diferentes trámites."
            ))

    tramite = meta.tramite
    if tramite is None:
        # metadatos ya intento el nombre de la carpeta; si llego aqui es que no
        # servia (vacio o con forma de id de sesion del asistente web).
        from gpmc.nucleo.manifiesto import Tramite
        tramite = Tramite(nombre="[por confirmar]", dependencia="[por confirmar]")

    rd = ext_dicc.extraer(dicc)
    r.huecos += rd.huecos
    if not rd.pantallas:
        r.huecos.append(Hueco(
            "bloqueante", "DIC-00", "",
            "no se extrajo ninguna pantalla del Diccionario",
        ))
        return r

    actores_vistos: dict[str, Actor] = {}
    pantallas: list[Pantalla] = []
    for p in rd.pantallas:
        aid = re.sub(r"[^a-z0-9]+", "_", p.actor).strip("_")[:30] or "actor"
        if aid not in actores_vistos:
            es_ciudadano = ext_mmd.normalizar_actor(aid) == "ciudadano"
            actores_vistos[aid] = Actor(
                id=aid,
                nombre=p.actor.title(),
                tipo="autoservicio" if es_ciudadano else "grupo",
                grupos_usuarios=[] if es_ciudadano else [p.actor.title()],
            )
        pantallas.append(Pantalla(
            id=p.id, nombre=p.nombre, actor=aid,
            paso_ciudadano=p.paso_ciudadano, campos=p.campos,
        ))

    # Huecos de integracion: se comprueban aqui y no en el compilador porque
    # aqui estan a la vez el campo, su pantalla y sus vecinos.
    for p in pantallas:
        nombres = {c.nombre for c in p.campos}
        for c in p.campos:
            if not c.endpoint:
                continue
            if _requiere_token(c.endpoint):
                r.huecos.append(Hueco(
                    "falta_dato", "API-05", c.nombre,
                    f"el endpoint '{c.endpoint}' exige token; el compilador no lo emite "
                    f"en cliente (riesgo SEG-04). Configúralo como una Acción PHP a mano, "
                    f"o usa la vía pública si existe (para CURP: SIPUBEH).",
                ))
                continue
            cat = _resolver_catalogo(c.endpoint)
            if cat is None:
                r.huecos.append(Hueco(
                    "falta_dato", "API-01", c.nombre,
                    f"el endpoint '{c.endpoint}' no está en el registro de catálogos "
                    f"conocidos; el campo se emite como lista vacía",
                ))
                continue
            if cat.requiere_padre and not c.dependencia_campo:
                r.huecos.append(Hueco(
                    "falta_dato", "API-03", c.nombre,
                    f"el catálogo '{cat.clave}' se puebla a partir de otro campo, "
                    f"pero no se declaró de cuál depende",
                ))
            elif c.dependencia_campo and c.dependencia_campo not in nombres:
                r.huecos.append(Hueco(
                    "falta_dato", "API-02", c.nombre,
                    f"depende del campo '{c.dependencia_campo}', que no existe en "
                    f"la pantalla '{p.nombre}'",
                ))

    tareas = []
    conexiones = []
    flujo_ramificado_exitoso = False

    if to_be:
        bloques = _BLOQUE_MERMAID.findall(to_be)
        if bloques:
            rm = ext_mmd.extraer(bloques[0])
            r.huecos += rm.huecos

            tareas_mmd = [n for n in rm.nodos if n.clase_nodo == "tarea"]
            compuertas = [n for n in rm.nodos if n.clase_nodo == "compuerta"]

            ramificado = _flujo_ramificado(rm, pantallas)
            if ramificado is not None:
                tareas, conexiones, parejas = ramificado
                flujo_ramificado_exitoso = True
                n_cond = sum(1 for c in conexiones if c.cuando is not None)
                detalle = "; ".join(f"«{ext_dicc._babel(nom)}» → {nid}" for nid, nom in parejas)
                r.huecos.append(Hueco(
                    "por_confirmar", "FLU-03", "flujo",
                    f"el flujo se ramificó automáticamente del diagrama TO-BE "
                    f"({len(compuertas)} compuerta(s), {n_cond} conexión(es) con condición). "
                    f"Confirma que las tareas casan con las pantallas: {detalle}",
                ))
            else:
                if compuertas:
                    r.huecos.append(Hueco(
                        "falta_dato", "FLU-01", "flujo",
                        f"el diagrama TO-BE tiene {len(compuertas)} compuerta(s) que este "
                        f"manifiesto NO reproduce: falta el `@@campo` en la compuerta, o "
                        f"una etiqueta de arista no casa con un valor del catálogo, o las "
                        f"tareas no casan con las pantallas. El flujo sale lineal; "
                        f"ramificar a mano.",
                    ))
                if len(tareas_mmd) != len(pantallas):
                    r.huecos.append(Hueco(
                        "falta_dato", "FLU-02", "flujo",
                        f"el diagrama tiene {len(tareas_mmd)} tareas y el Diccionario "
                        f"{len(pantallas)} pantallas; confirmar la correspondencia",
                    ))
        else:
            r.huecos.append(Hueco(
                "falta_dato", "MMD-01", "flujo",
                "la Propuesta TO-BE no trae bloque ```mermaid```",
            ))

    if not flujo_ramificado_exitoso:
        tareas = [
            Tarea(id=f"t_{p.id}", nombre=p.nombre[:_CAP_NOMBRE], actor=p.actor,
                  inicial=(i == 0), pantallas=[p.id])
            for i, p in enumerate(pantallas)
        ]
        tareas.append(Tarea(id="t_fin", nombre="Trámite concluido", terminal=True))
        conexiones = [
            Conexion(de=tareas[i].id, a=tareas[i + 1].id) for i in range(len(tareas) - 1)
        ]

    r.manifiesto = Manifiesto(
        tramite=tramite,
        actores=list(actores_vistos.values()),
        pantallas=pantallas,
        flujo=Flujo(tareas=tareas, conexiones=conexiones),
        acciones=[],
    )
    return r
