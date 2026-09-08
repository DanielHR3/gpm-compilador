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
from gpmc.nucleo.manifiesto import (
    Actor, Conexion, Flujo, Manifiesto, Pantalla, Tarea,
)

_BLOQUE_MERMAID = re.compile(r"```mermaid(.*?)```", re.S)


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
            
            # Intento de mapeo exacto (sin adivinar)
            nombres_pantallas = {ext_dicc._babel(p.nombre): p for p in pantallas}
            tareas_mmd = [n for n in rm.nodos if n.clase_nodo == "tarea"]
            
            mapeo_exacto = True
            nodos_a_pantallas = {}
            for n in tareas_mmd:
                babel_n = ext_dicc._babel(n.texto)
                if babel_n in nombres_pantallas:
                    nodos_a_pantallas[n.id] = nombres_pantallas[babel_n]
                else:
                    mapeo_exacto = False
                    break
                    
            if mapeo_exacto and len(tareas_mmd) == len(pantallas):
                # Generar tareas
                nodos_inicio = {a.a for a in rm.aristas if a.de in [n.id for n in rm.nodos if n.clase_nodo == "inicio_fin"]}
                nodos_fin = {a.de for a in rm.aristas if a.a in [n.id for n in rm.nodos if n.clase_nodo == "inicio_fin"]}
                
                # Nodos inicio/fin que no son compuertas ni tareas
                ids_inicio_fin = {n.id for n in rm.nodos if n.clase_nodo == "inicio_fin"}
                
                # Crear Tareas
                for n in rm.nodos:
                    if n.clase_nodo == "tarea":
                        p = nodos_a_pantallas[n.id]
                        tareas.append(Tarea(
                            id=n.id, nombre=n.texto[:60], actor=p.actor,
                            inicial=(n.id in nodos_inicio or not any(a.a == n.id for a in rm.aristas if a.de not in ids_inicio_fin)),
                            terminal=(n.id in nodos_fin or not any(a.de == n.id for a in rm.aristas if a.a not in ids_inicio_fin)),
                            pantallas=[p.id]
                        ))
                
                # Manejar compuertas resolviendo condiciones desde el Diccionario
                from gpmc.nucleo.manifiesto import Condicion
                from gpmc.extractores.diccionario import _parsear_condicion_visible, _resolver_condicion_visible
                
                # Índice simulado para resolver condiciones de compuertas
                indice_campos = {"por_etiqueta": {}, "campos": {}}
                for p in pantallas:
                    for c in p.campos:
                        indice_campos["campos"][c.nombre] = c
                        indice_campos["por_etiqueta"].setdefault(ext_dicc._clave_etiqueta(c.etiqueta), c.nombre)

                compuertas_resueltas = True
                for a in rm.aristas:
                    if a.de in ids_inicio_fin or a.a in ids_inicio_fin:
                        continue
                        
                    nodo_origen = next((n for n in rm.nodos if n.id == a.de), None)
                    if nodo_origen and nodo_origen.clase_nodo == "compuerta":
                        # La arista sale de una compuerta
                        # Necesitamos resolver la etiqueta de la arista o los campos de la compuerta
                        # Como Mermaid solo tiene etiquetas de arista libres (ej. "Sí", "No"), y el compilador 
                        # necesita `cuando: campo == valor`, esto requiere inferencia riesgosa.
                        # Para no violar el invariante "no adivinar", exigimos validación humana.
                        compuertas_resueltas = False
                        break
                    elif nodo_origen and nodo_origen.clase_nodo == "tarea":
                        conexiones.append(Conexion(de=a.de, a=a.a))
                        
                if compuertas_resueltas:
                    flujo_ramificado_exitoso = True

            compuertas = [n for n in rm.nodos if n.clase_nodo == "compuerta"]
            if compuertas and not flujo_ramificado_exitoso:
                r.huecos.append(Hueco(
                    "falta_dato", "FLU-01", "flujo",
                    f"el diagrama TO-BE tiene {len(compuertas)} compuertas que este "
                    f"manifiesto NO reproduce de forma automática (requiere resolver condiciones a mano). "
                    f"El flujo propuesto es lineal. Revisar y ramificar a mano antes de compilar.",
                ))
            if len(tareas_mmd) != len(pantallas) and not flujo_ramificado_exitoso:
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
            Tarea(id=f"t_{p.id}", nombre=p.nombre[:60], actor=p.actor,
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
