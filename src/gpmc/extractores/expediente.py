"""Orquesta los tres extractores sobre la carpeta de un expediente.

Cada extractor es independiente: si uno falla, lo suyo se convierte en hueco y
los demas siguen. La herramienta siempre produce algo revisable.
"""

from typing import Optional
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from gpmc.extractores import documentos as ext_docs
from gpmc.extractores import diccionario as ext_dicc
from gpmc.extractores import mermaid as ext_mmd
from gpmc.extractores import metadatos as ext_meta
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.integraciones import resolver as _resolver_catalogo
from gpmc.nucleo.integraciones import requiere_token as _requiere_token
from gpmc.nucleo.integraciones import nombre_propuesta as _nombre_propuesta
from gpmc.nucleo.limites import LIMITE_FORMULARIO_NOMBRE as _CAP_NOMBRE
from gpmc.nucleo.manifiesto import (
    Accion, Actor, Condicion, Conexion, Flujo, Manifiesto, Pantalla, PasoPantalla, Tarea,
)

_BLOQUE_MERMAID = re.compile(r"```mermaid(.*?)```", re.S)


def _mapear_nodos_a_pantallas(nodos_tarea, pantallas):
    """Casa cada nodo 'tarea' del Mermaid con una pantalla del Diccionario por
    nombre normalizado. Acepta el prefijo de carril: 'Area: Cotiza' casa con la
    pantalla 'Cotiza'. Devuelve {id_nodo: pantalla} o None si no casan 1:1."""
    if len(nodos_tarea) != len(pantallas):
        return None

    def _sin_nota(texto):
        """El titulo sin su nota final entre parentesis.

        El Diccionario titula pantallas con una aclaracion para humanos
        —«(consulta manual FUERA de GPM)»— que el diagrama no repite. Exigir
        la cadena identica hacia fallar el mapeo entero por una nota, y con el
        se perdian todas las compuertas (Reposicion de Certificado, 2026-09-22).
        """
        return ext_dicc._babel(re.sub(r"\s*\([^()]*\)\s*$", "", texto or "")).strip()

    por_nombre = {ext_dicc._babel(p.nombre): p for p in pantallas}
    # Indice sin nota, solo con los que quedan SIN ambiguedad: si dos pantallas
    # se distinguen precisamente por su parentesis, quitarlo las confundiria.
    sin_nota = {}
    for p in pantallas:
        sin_nota.setdefault(_sin_nota(p.nombre), []).append(p)
    por_nombre_sin_nota = {k: v[0] for k, v in sin_nota.items() if len(v) == 1}

    mapa = {}
    for n in nodos_tarea:
        candidatos = [n.texto]
        if ":" in n.texto:
            candidatos.append(n.texto.split(":", 1)[1])
        p = next((por_nombre.get(ext_dicc._babel(c)) for c in candidatos
                  if por_nombre.get(ext_dicc._babel(c))), None)
        if p is None:
            p = next((por_nombre_sin_nota.get(_sin_nota(c)) for c in candidatos
                      if por_nombre_sin_nota.get(_sin_nota(c))), None)
        if p is None:
            return None
        mapa[n.id] = p
    if len({id(p) for p in mapa.values()}) != len(pantallas):
        return None  # dos nodos apuntan a la misma pantalla
    return mapa


def _pasos_de(p) -> list:
    """Los pasos de la tarea de una pantalla: primero, en visualizacion, las
    pantallas anteriores que su fila «Vista de solo lectura» pide ensenar; al
    final la propia. Es la forma de los exports autenticos para una revision
    (captura en visualizacion + dictamen en edicion) y lo que pidio la fabrica
    el 2026-11-12: que quien valida vea lo que esta validando."""
    return [PasoPantalla(id=pid, modo="visualizacion") for pid in p.muestra_antes] + [
        PasoPantalla(id=p.id)]


def _fusionar_tareas(tareas, conexiones):
    """Une en una sola tarea, con varios pasos, las que van seguidas y son del
    mismo responsable. Devuelve (tareas, conexiones, [(nombre_a, nombre_b)]).

    La fabrica (2026-11-12): «exceso de tareas que fragmentan el flujo… Las
    tareas deben emplearse cuando exista una separación funcional, un cambio de
    responsable». Una tarea por pantalla hacia que el mismo funcionario cerrara
    una tarea para abrir la siguiente.

    Solo cuando no hay nada que decidir entre las dos: A sale unicamente hacia
    B, sin condicion, y a B solo se llega desde A. Asi el resultado es la forma
    (edicion, edicion) que ya traen los exports autenticos. Fundir una rama
    exigiria una regla en el paso, y ningun export trae una: eso no se emite
    sin acta de la plataforma.
    """
    tareas = list(tareas)
    conexiones = list(conexiones)
    fusiones = []
    while True:
        por_id = {t.id: t for t in tareas}
        pareja = None
        for cx in conexiones:
            a, b = por_id.get(cx.de), por_id.get(cx.a)
            if (a is None or b is None or a is b or cx.cuando is not None
                    or not a.actor or a.actor != b.actor
                    or not a.pantallas or not b.pantallas or b.inicial
                    or sum(1 for c in conexiones if c.de == a.id) != 1
                    or sum(1 for c in conexiones if c.a == b.id) != 1
                    # B no puede volver a A: seria un ciclo dentro de la tarea.
                    or any(c.de == b.id and c.a == a.id for c in conexiones)):
                continue
            pareja = (cx, a, b)
            break
        if pareja is None:
            return tareas, conexiones, fusiones
        cx, a, b = pareja
        ya = {p.id for p in a.pantallas}
        # Lo que B ensenaba en visualizacion y A ya muestra no se repite.
        a.pantallas = a.pantallas + [
            p for p in b.pantallas if not (p.modo == "visualizacion" and p.id in ya)]
        a.terminal = b.terminal
        a.acciones_antes = a.acciones_antes + [x for x in b.acciones_antes if x not in a.acciones_antes]
        a.acciones_despues = a.acciones_despues + [x for x in b.acciones_despues if x not in a.acciones_despues]
        fusiones.append((a.nombre, b.nombre))
        a.nombre = _nombre_unido(a.nombre, b.nombre)
        tareas = [t for t in tareas if t is not b]
        conexiones = [c for c in conexiones if c is not cx]
        for c in conexiones:
            if c.de == b.id:
                c.de = a.id


_NOTA_FINAL = re.compile(r"\s*\([^()]*\)\s*$")


def _nombre_unido(a: str, b: str) -> str:
    """El nombre de la tarea que junta dos: los dos, para que no parezca que
    solo hace lo primero. Si no cabe en la columna, sin las notas entre
    parentesis; y si aun asi no cabe, el de la primera."""
    for x, y in ((a, b), (_NOTA_FINAL.sub("", a), _NOTA_FINAL.sub("", b))):
        junto = f"{x} / {y}"
        if len(junto) <= _CAP_NOMBRE:
            return junto
    return a


def _hueco_de_fusion(fusiones):
    detalle = "; ".join(f"«{b}» pasa a ser un paso de «{a}»" for a, b in fusiones)
    return Hueco(
        "por_confirmar", "FLU-04", "flujo",
        f"{len(fusiones)} tarea(s) seguidas del mismo responsable se unieron en una sola con "
        f"varios pasos: {detalle}. Confirma que no hay un cambio de responsable entre ellas",
    )


def colgar_folios(acciones, flujo, pantallas) -> None:
    """Cuelga cada accion de folio «antes» de la tarea que muestra su campo.

    Es donde la llevan los tres exports autenticos con folio (la variable de
    la accion se llama igual que el campo de solo lectura, y el evento va
    «antes» de la tarea de esa pantalla). No duplica: se llama tambien al
    rearmar el flujo, que construye tareas nuevas sin acciones."""
    donde = {c.nombre: p.id for p in pantallas for c in p.campos}
    for a in acciones:
        if a.tipo != "folio":
            continue
        if any(a.nombre in t.acciones_antes + t.acciones_despues for t in flujo.tareas):
            continue
        tarea = flujo.tarea_de_pantalla(donde.get(getattr(a, "variable", ""), ""))
        if tarea is not None:
            tarea.acciones_antes.append(a.nombre)


def _acciones_del_sistema(generados, pantallas):
    """De los campos que el Diccionario dice que llena el sistema: la accion de
    folio, si hay UN campo de folio, y el aviso de lo demas.

    La fabrica (2026-11-12): «no se aprovechan las variables de tipo Acción».
    El folio si se puede emitir sin adivinar: su forma es fija (contador con
    bloqueo). Un monto no: en los exports cada costo es PHP escrito para ese
    tramite (valor de la UMA, arreglo de la pasarela). Eso se nombra y lo
    configura una persona.
    """
    tipos = {c.nombre: c.tipo for p in pantallas for c in p.campos}
    presentes = {n: e for n, e in generados.items() if n in tipos}
    folios = [n for n in presentes if "folio" in n and tipos[n] == "text"]
    acciones, huecos = [], []
    if len(folios) == 1:
        variable = folios[0]
        acciones.append(Accion(tipo="folio", nombre="crear-folio", variable=variable, prefijo="GPM"))
        huecos.append(Hueco(
            "por_confirmar", "ACC-01", "acciones",
            f"«{presentes[variable]}» (@@{variable}) se llena con una acción de folio "
            f"consecutivo, con la forma GPM-AAAA-00001. El prefijo «GPM» es provisional: "
            f"cámbialo por el de la dependencia",
        ))
    resto = [e for n, e in presentes.items() if n not in folios[:1 if len(folios) == 1 else 0]]
    if resto:
        huecos.append(Hueco(
            "por_confirmar", "ACC-02", "acciones",
            f"{len(resto)} campo(s) los llena el sistema y el compilador no emite su cálculo: "
            + ", ".join(f"«{e}»" for e in resto)
            + ". Cada uno necesita una Acción PHP en la plataforma; sin ella el campo sale vacío",
        ))
    return acciones, huecos


def _marcar_visualizacion(tareas, pantallas) -> None:
    """Una pantalla donde todos los campos son de solo lectura se recorre en modo Visualización
    (observación de la fábrica, 2026-11-11): nadie captura nada ahí, solo consulta."""
    solo_lectura = {p.id for p in pantallas if p.campos and all(c.solo_lectura for c in p.campos)}
    for t in tareas:
        for paso in t.pantallas:
            if paso.id in solo_lectura:
                paso.modo = "visualizacion"


def _colapsar_mmd03(huecos):
    """Reduce los MMD-03 de un diagrama a un solo hueco que no bloquea.

    El `:::clase` del Mermaid NO alimenta el manifiesto: `Nodo.actor` se lee
    solo dentro de `mermaid.extraer`, para decidir si emite MMD-03, mientras
    que el actor de cada Tarea sale siempre de `p.actor` del Diccionario --
    tanto en el respaldo lineal como en `_flujo_ramificado`. Un MMD-03
    `falta_dato` por nodo convertia en bloqueante un dato que el compilador ya
    tiene por otra via, y encima a menudo irresoluble: `/resolver` traduce el
    id del nodo a una Tarea real via `_mapear_nodos_a_pantallas`, que es
    todo-o-nada. En "Publicacion en el Periodico Oficial" (diagrama que colorea
    con `style X fill:#...` en vez de `classDef`, 32 nodos tarea contra 13
    pantallas) eso daba 42 huecos bloqueantes, 36 de ellos con 422 al
    guardarlos: el expediente no se podia compilar por ningun camino.

    Se devuelven los demas huecos intactos y, si habia MMD-03, uno solo de
    nivel `por_confirmar` sobre el flujo: el diagrama se revisa de un vistazo,
    no se detiene la entrega por el.
    """
    otros = [h for h in huecos if h.codigo != "MMD-03"]
    sin_carril = [h.ubicacion for h in huecos if h.codigo == "MMD-03"]
    if not sin_carril:
        return otros
    return otros + [Hueco(
        "por_confirmar", "MMD-03", "flujo",
        f"{len(sin_carril)} nodo(s) del diagrama TO-BE no declaran carril "
        f"(`classDef` + `:::clase`): {', '.join(sin_carril)}. El actor de cada "
        f"tarea se tomó del Diccionario de Datos; confirma que el diagrama y "
        f"el Diccionario dicen lo mismo.",
    )]


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


def _flujo_ramificado(rm, pantallas, overrides=None):
    """Construye tareas y conexiones NO lineales desde el Mermaid, y solo si es
    seguro (spec 2026-09-03, Parte 2). Devuelve (tareas, conexiones, parejas) o
    None — y entonces el flujo sigue saliendo lineal, como antes.

    `overrides` es un dict opcional {id_compuerta: nombre_campo}: si una compuerta
    no nombra ningun `@@campo`, ese campo se usa igualmente para decidir la rama.
    Es una copia local; `rm` no se toca. Con `overrides=None`/`{}` el
    comportamiento es identico al de siempre.

    Condiciones, todas obligatorias:
      1. Cada nodo 'tarea' casa 1:1 por nombre con una pantalla del Diccionario.
      2. Cada compuerta nombra exactamente un @@campo, y ese campo existe.
      3. Cada arista que sale de una compuerta trae etiqueta, y esa etiqueta
         resuelve a un valor del catalogo del campo (o Si/No).
      4. Toda compuerta esta alimentada por una tarea, y sus ramas van a tareas
         (no a inicio/fin ni a otra compuerta).
    Si algo falla, se devuelve None: no se adivina.
    """
    overrides = overrides or {}

    nodos_tarea = [n for n in rm.nodos if n.clase_nodo == "tarea"]
    mapa = _mapear_nodos_a_pantallas(nodos_tarea, pantallas)
    if mapa is None:
        return None

    ids_if = {n.id for n in rm.nodos if n.clase_nodo == "inicio_fin"}
    compuertas = {n.id: n for n in rm.nodos if n.clase_nodo == "compuerta"}
    campos = {c.nombre: c for p in pantallas for c in p.campos}

    for g in compuertas.values():
        campos_gate = [overrides[g.id]] if g.id in overrides else list(g.campos)
        if len(set(campos_gate)) != 1 or campos_gate[0] not in campos:
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
            campo_efectivo = overrides.get(
                a.de,
                compuertas[a.de].campos[0] if compuertas[a.de].campos else None,
            )
            campo = campos[campo_efectivo]
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
    # Sin nodo Inicio y con la corrección de vuelta a la captura, la primera tarea recibe una
    # flecha y ninguna quedaría como inicial (fábrica, 2026-11-11: el flujo salía lineal). En un
    # diagrama así, la inicial es la primera tarea que el equipo dibujó.
    iniciales = {n.id for n in nodos_tarea if n.id in entra_if or n.id not in entra}
    if not iniciales and not entra_if and nodos_tarea:
        iniciales = {nodos_tarea[0].id}
    tareas = []
    for n in nodos_tarea:
        p = mapa[n.id]
        tareas.append(Tarea(
            id=n.id, nombre=(p.nombre or n.texto)[:_CAP_NOMBRE], actor=p.actor,
            inicial=(n.id in iniciales),
            terminal=(n.id in sale_if or n.id not in sale),
            pantallas=_pasos_de(p),
        ))
    # La plataforma arranca en UNA tarea: con dos que salen del Inicio (o sin
    # flecha de entrada) el Manifiesto lanzaba ValueError y el asistente daba 500.
    # Se cae al flujo lineal, que reporta FLU-01 si el diagrama tenía compuertas.
    if sum(1 for t in tareas if t.inicial) != 1 or not any(t.terminal for t in tareas):
        return None

    parejas = [(n.id, mapa[n.id].nombre) for n in nodos_tarea]
    return tareas, conexiones, parejas


def ramas_de_compuerta(rm, pantallas, gate_id):
    """Expone la estructura de ramas de una compuerta para el fallback de la UI.

    Devuelve {"predecesora": <id de la tarea previa>,
              "ramas": [{"a", "a_nombre", "etiqueta"}]}
    o None si `gate_id` no es una compuerta, o si no la alimenta ninguna tarea
    (sin predecesora no hay donde colgar las ramas). Funcion pura: no muta `rm`
    ni hace E/S.
    """
    compuerta = next(
        (n for n in rm.nodos
         if n.id == gate_id and n.clase_nodo == "compuerta"),
        None,
    )
    if compuerta is None:
        return None

    nodos = {n.id: n for n in rm.nodos}
    ids_tarea = {n.id for n in rm.nodos if n.clase_nodo == "tarea"}
    nodos_tarea = [n for n in rm.nodos if n.clase_nodo == "tarea"]
    mapa = _mapear_nodos_a_pantallas(nodos_tarea, pantallas) or {}

    def _nombre(nid):
        if nid in mapa:
            return mapa[nid].nombre
        n = nodos.get(nid)
        return n.texto if n is not None else nid

    predecesora = next(
        (a.de for a in rm.aristas if a.a == gate_id and a.de in ids_tarea),
        None,
    )
    if predecesora is None:
        return None

    ramas = [
        {"a": a.a, "a_nombre": _nombre(a.a), "etiqueta": a.etiqueta or ""}
        for a in rm.aristas if a.de == gate_id
    ]
    return {"predecesora": predecesora, "ramas": ramas}


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


def _decisiones_de_publicacion(actores: "list[Actor]", flujo: Flujo) -> "list[Hueco]":
    """Lo que hoy se corrige en la plataforma despues de importar, dicho antes.

    Ninguna de las dos cosas esta en los insumos, asi que no se derivan: se
    avisan `por_confirmar` y las decide una persona en el asistente (`meta07`
    y `act01` de `POST /resolver`). Sin decidir, el .gpm sale como siempre.
    Se emiten aqui y no en `metadatos` porque solo aqui se conocen a la vez
    los actores y la tarea inicial. Spec 2026-10-01.
    """
    huecos = []
    por_id = {a.id: a for a in actores}

    # P-17: `publico` nace en False y ningun extractor lo cambia. El tramite
    # importa limpio, el funcionario lo ve y el ciudadano no.
    inicial = next((t for t in flujo.tareas if t.inicial), None)
    actor_inicial = por_id.get(inicial.actor) if inicial and inicial.actor else None
    lo_inicia_el_ciudadano = actor_inicial is not None and actor_inicial.tipo == "autoservicio"
    huecos.append(Hueco(
        "por_confirmar", "META-07", "metadatos",
        "el tramite saldra oculto del portal del ciudadano: nada en el "
        "expediente dice si es publico",
        propuesta="Sí, porque lo inicia el ciudadano" if lo_inicia_el_ciudadano else None,
    ))

    # PLAT-11: el grupo se llena con el nombre del responsable tal como lo
    # escribe el Diccionario. La plataforma busca un grupo suyo
    # (`verificacion_vehicular`) y, al no hallarlo, la restriccion no ata.
    for a in actores:
        if a.tipo != "grupo":
            continue
        grupo = a.grupos_usuarios[0] if a.grupos_usuarios else a.nombre
        huecos.append(Hueco(
            "por_confirmar", "ACT-01", a.id,
            f"las tareas de «{a.nombre}» se restringen al grupo «{grupo}», que "
            f"es el nombre del responsable y no un grupo de la plataforma",
        ))
    return huecos


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

    meta = ext_meta.extraer(as_is, to_be, nombre_carpeta=carpeta.name, diccionario=dicc)
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
            muestra_antes=list(p.muestra_antes),
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
                    f"'{c.endpoint}' es {_nombre_propuesta(c.endpoint)}: exige token y el "
                    f"compilador no lo emite en el navegador (riesgo SEG-04). Configúralo como "
                    f"una Acción PHP a mano, o usa la vía pública si existe (para CURP: SIPUBEH).",
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
            # Los nombres del Diccionario permiten que una compuerta escrita
            # en español —sin la sintaxis @@— resuelva sola su campo.
            declarados = [c.nombre for p_ in pantallas for c in p_.campos]
            rm = ext_mmd.extraer(bloques[0], campos_declarados=declarados)
            r.huecos += _colapsar_mmd03(rm.huecos)

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
                  inicial=(i == 0), pantallas=_pasos_de(p))
            for i, p in enumerate(pantallas)
        ]
        tareas.append(Tarea(id="t_fin", nombre="Trámite concluido", terminal=True))
        conexiones = [
            Conexion(de=tareas[i].id, a=tareas[i + 1].id) for i in range(len(tareas) - 1)
        ]

    # Los documentos que el tramite genera (oficios, acuses): plantillas .md
    # con {{variables}} en documentos/. Cada variable debe ser un campo real.
    acciones_doc, huecos_doc = ext_docs.extraer_documentos(
        carpeta, {c.nombre for p_ in pantallas for c in p_.campos},
    )
    r.huecos += huecos_doc
    # Sin Evento en una tarea el PDF nunca se produce: se cuelga de la
    # primera tarea que ya tiene todos sus datos, y se reporta para confirmar.
    # Con FLU-01 el flujo lineal es un esqueleto provisional: el diagrama trae
    # compuertas que una persona va a resolver a mano, tarea por tarea
    # (`mmd04rama`). Fundir ahi esconderia las tareas donde cuelgan las ramas.
    if not any(h.codigo == "FLU-01" for h in r.huecos):
        tareas, conexiones, fusiones = _fusionar_tareas(tareas, conexiones)
        if fusiones:
            r.huecos.append(_hueco_de_fusion(fusiones))
    _marcar_visualizacion(tareas, pantallas)
    flujo = Flujo(tareas=tareas, conexiones=conexiones)
    r.huecos += ext_docs.atar_a_tareas(acciones_doc, flujo, pantallas)
    acciones_sis, huecos_sis = _acciones_del_sistema(rd.generados, pantallas)
    r.huecos += huecos_sis
    colgar_folios(acciones_sis, flujo, pantallas)

    r.huecos += _decisiones_de_publicacion(list(actores_vistos.values()), flujo)

    r.manifiesto = Manifiesto(
        tramite=tramite,
        actores=list(actores_vistos.values()),
        pantallas=pantallas,
        flujo=flujo,
        acciones=acciones_sis + acciones_doc,
    )
    return r
