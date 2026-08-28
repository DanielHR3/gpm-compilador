"""Extrae pantallas y campos del Diccionario de Datos en markdown.

Estructura real de los expedientes del wiki:

    ### Pantalla N — ACTOR — Nombre de la pantalla

    | Nombre del Campo | Tipo de Dato | Componente Sugerido (GPM) | Obligatorio |
    | Condicion de Visibilidad | Limite/Especificaciones | Catalogo de Valores |
    | Ejemplo Real | Descripcion |

El nombre tecnico no tiene columna propia: viaja embebido en la Descripcion
como `@@nombre`. Cuando falta, se reporta como hueco en vez de inventarlo.
"""

from typing import Optional
import re
import unicodedata
from dataclasses import dataclass, field

from gpmc.nucleo.manifiesto import Campo, OpcionCatalogo
from gpmc.nucleo.huecos import Hueco

# Acepta ### y ####: los expedientes que siguen la regla fija 16 anidan las
# pantallas bajo un encabezado "### Paso N del stepper".
_ENCABEZADO = re.compile(
    r"^#{3,4}\s+Pantalla\s+(?P<num>\d+)\s*[—\-–]\s*(?P<actor>[^—\-–]+?)\s*[—\-–]\s*(?P<nombre>.+?)\s*$",
    re.M,
)
_PASO_STEPPER = re.compile(r"\(\s*Paso\s+(\d+)", re.I)
# El cuerpo de una pantalla termina en la siguiente pantalla o en el siguiente
# encabezado de igual o mayor jerarquia. Sin este corte, las tablas de las
# Secciones 2 a 5 del Diccionario se absorben dentro de la ultima pantalla.
_CORTE = re.compile(r"^#{1,3}\s+(?!#)", re.M)
_CAMPO_TECNICO = re.compile(r"@@(\w+)")
_LONGITUD = re.compile(r"(\d+)\s*caracteres")

COMPONENTES = [
    ("lista desplegable", "select"), ("desplegable", "select"), ("select", "select"),
    ("carga de archivo", "file"), ("archivo", "file"), ("file", "file"),
    ("area de texto", "textarea"), ("área de texto", "textarea"), ("textarea", "textarea"),
    ("radio", "radio"), ("opcion", "radio"), ("opción", "radio"),
    ("fecha y hora", "date_time"), ("fecha", "date"),
    ("parrafo", "paragraph"), ("párrafo", "paragraph"),
    ("etiqueta", "paragraph"), ("badge", "paragraph"),
    ("numerico", "text"), ("numérico", "text"),
    ("texto", "text"), ("input", "text"),
]

MARCAS_PENDIENTE = ("pendiente", "por confirmar", "sin confirmar", "por definir")


@dataclass
class PantallaExtraida:
    id: str
    numero: int
    nombre: str
    actor: str
    paso_ciudadano: Optional[int] = None
    campos: list[Campo] = field(default_factory=list)


@dataclass
class Resultado:
    pantallas: list[PantallaExtraida] = field(default_factory=list)
    huecos: list[Hueco] = field(default_factory=list)


def _sin_acentos(t: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
    )


def _babel(t: str) -> str:
    return _sin_acentos((t or "").strip().lower())


def _tipo_de(componente: str, tipo_dato: str) -> str:
    """El Diccionario estandar nombra el componente ("Lista desplegable
    (select)"); el hibrido nombra directamente el tipo de la plataforma
    ("select"). Se consultan ambas columnas contra la misma tabla, el
    componente primero para que la mas especifica gane."""
    for celda in (componente, tipo_dato):
        c = _babel(celda)
        for aguja, tipo in COMPONENTES:
            if _sin_acentos(aguja) in c:
                return tipo
    return "file" if "archivo" in _babel(tipo_dato) else "text"


def _celdas(linea: str) -> list[str]:
    partes = linea.split("|")
    if len(partes) >= 3:
        partes = partes[1:-1]
    return [p.strip() for p in partes]


def _es_separador(linea: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:\-|]+\|", linea.strip()))


def _catalogo_de(celda: str) -> tuple[list[OpcionCatalogo], bool]:
    """Devuelve las opciones y si el catalogo esta declarado como pendiente."""
    crudo = (celda or "").strip()
    if not crudo or crudo.upper() == "N/A":
        return [], False
    if any(m in _babel(crudo) for m in MARCAS_PENDIENTE):
        return [], True
    partes = [p.strip() for p in re.split(r"\s+·\s+|\s+•\s+|\s*;\s*", crudo) if p.strip()]
    if len(partes) < 2:
        return [], False
    return [
        OpcionCatalogo(etiqueta=p, valor=_babel(p).replace(" ", "_")) for p in partes
    ], False


def extraer(texto: str) -> Resultado:
    r = Resultado()
    encabezados = list(_ENCABEZADO.finditer(texto))

    for i, m in enumerate(encabezados):
        ini = m.end()
        fin = encabezados[i + 1].start() if i + 1 < len(encabezados) else len(texto)
        corte = _CORTE.search(texto, ini, fin)
        if corte:
            fin = corte.start()
        cuerpo = texto[ini:fin]

        nombre_crudo = m["nombre"].strip()
        m_paso = _PASO_STEPPER.search(nombre_crudo)
        pantalla = PantallaExtraida(
            id=f"p{m['num']}",
            numero=int(m["num"]),
            nombre=_PASO_STEPPER.sub("(", nombre_crudo).replace("()", "").strip(" —-()"),
            actor=_babel(m["actor"]),
            paso_ciudadano=int(m_paso.group(1)) if m_paso else None,
        )

        filas = [l for l in cuerpo.splitlines() if l.strip().startswith("|")]
        filas = [l for l in filas if not _es_separador(l)]
        if len(filas) < 2:
            r.huecos.append(Hueco(
                "falta_dato", "DIC-03", pantalla.id,
                "no trae tabla de campos legible",
            ))
            r.pantallas.append(pantalla)
            continue

        columnas = [_babel(c) for c in _celdas(filas[0])]

        def col(*nombres, defecto=None):
            for n in nombres:
                for j, c in enumerate(columnas):
                    if n in c:
                        return j
            return defecto

        i_nombre = col("nombre del campo", "campo", "variable", defecto=0)
        es_columna_variable = i_nombre is not None and "variable" in columnas[i_nombre]
        i_tipo = col("tipo de dato", defecto=1)
        i_comp = col("componente", defecto=2)
        i_obl = col("obligatorio", defecto=3)
        i_lim = col("limite", "especificaciones")
        i_cat = col("catalogo de valores", "catalogo")
        i_desc = col("descripcion")

        for fila in filas[1:]:
            celdas = _celdas(fila)
            if len(celdas) < 3 or not celdas[i_nombre]:
                continue

            etiqueta = re.sub(r"\*+", "", celdas[i_nombre]).strip()
            etiqueta = etiqueta.replace("`", "")
            desc = celdas[i_desc] if i_desc is not None and i_desc < len(celdas) else ""

            tecnicos = _CAMPO_TECNICO.findall(desc)
            if es_columna_variable and re.fullmatch(r"[A-Za-z_]\w*", etiqueta):
                nombre = etiqueta
                etiqueta = nombre.replace("_", " ").capitalize()
            elif tecnicos:
                nombre = tecnicos[0]
            else:
                nombre = re.sub(r"[^a-z0-9]+", "_", _babel(etiqueta)).strip("_")[:40]
                r.huecos.append(Hueco(
                    "por_confirmar", "DIC-01", pantalla.id,
                    f"el campo '{etiqueta}' no declara nombre técnico @@ en su "
                    f"descripción; se propuso '{nombre}'",
                    propuesta=nombre,
                ))

            limite = celdas[i_lim] if i_lim is not None and i_lim < len(celdas) else ""
            m_long = _LONGITUD.search(limite or "")

            cat_celda = celdas[i_cat] if i_cat is not None and i_cat < len(celdas) else ""
            catalogo, pendiente = _catalogo_de(cat_celda)
            if pendiente:
                r.huecos.append(Hueco(
                    "falta_dato", "DIC-02", pantalla.id,
                    f"el catálogo de '{etiqueta}' está declarado como pendiente "
                    f"en el Diccionario; no se emite",
                ))

            tipo = _tipo_de(
                celdas[i_comp] if i_comp is not None and i_comp < len(celdas) else "",
                celdas[i_tipo] if i_tipo is not None and i_tipo < len(celdas) else "",
            )
            if catalogo and tipo == "text":
                tipo = "select"

            obligatorio = _babel(
                celdas[i_obl] if i_obl is not None and i_obl < len(celdas) else ""
            ).startswith("si")

            pantalla.campos.append(Campo(
                nombre=nombre,
                etiqueta=etiqueta,
                tipo=tipo,
                obligatorio=obligatorio,
                solo_lectura="solo lectura" in _babel(desc),
                longitud_exacta=int(m_long.group(1)) if m_long else None,
                catalogo=catalogo,
            ))

        r.pantallas.append(pantalla)

    if not r.pantallas:
        r.huecos.append(Hueco(
            "falta_dato", "DIC-04", "",
            "no se encontró ninguna cabecera '### Pantalla N — ACTOR — Nombre'; "
            "se agruparon todos los campos en una sola pantalla por defecto",
        ))
        
        filas = [l for l in texto.splitlines() if l.strip().startswith("|")]
        filas = [l for l in filas if not _es_separador(l)]
        if len(filas) >= 2:
            pantalla = PantallaExtraida(id="p1", numero=1, nombre="Datos Generales", actor="usuario")
            columnas = [_babel(c) for c in _celdas(filas[0])]
            
            def col(*nombres, defecto=None):
                for n in nombres:
                    for j, c in enumerate(columnas):
                        if n in c:
                            return j
                return defecto
                
            i_nombre = col("nombre del campo", "campo", "variable", defecto=0)
            # Una columna "Variable" declara el nombre tecnico de forma explicita;
            # entonces un @@ en el Comportamiento es una dependencia (select en
            # cascada), no el nombre del campo.
            es_columna_variable = i_nombre is not None and "variable" in columnas[i_nombre]
            i_tipo = col("tipo de dato", "tipo", defecto=1)
            i_comp = col("componente", defecto=2)
            i_obl = col("obligatorio", defecto=3)
            i_lim = col("limite", "especificaciones")
            i_cat = col("catalogo de valores", "catalogo")
            i_desc = col("descripcion", "comportamiento")
            
            for fila in filas[1:]:
                celdas = _celdas(fila)
                if len(celdas) < 3 or not celdas[i_nombre]:
                    continue
                    
                etiqueta = re.sub(r"\*+", "", celdas[i_nombre]).strip()
                # Quitar backticks si es una variable cruda
                etiqueta = etiqueta.replace("`", "")
                
                desc = celdas[i_desc] if i_desc is not None and i_desc < len(celdas) else ""

                tecnicos = _CAMPO_TECNICO.findall(desc)
                if es_columna_variable and re.fullmatch(r"[A-Za-z_]\w*", etiqueta):
                    nombre = etiqueta
                    etiqueta = nombre.replace("_", " ").capitalize()
                elif tecnicos:
                    nombre = tecnicos[0]
                else:
                    nombre = re.sub(r"[^a-z0-9]+", "_", _babel(etiqueta)).strip("_")[:40]
                    r.huecos.append(Hueco(
                        "por_confirmar", "DIC-01", "p1",
                        f"se propuso el nombre técnico '{nombre}' para '{etiqueta}'",
                        propuesta=nombre,
                    ))
                    
                limite = celdas[i_lim] if i_lim is not None and i_lim < len(celdas) else ""
                m_long = _LONGITUD.search(limite or "")
                
                cat_celda = celdas[i_cat] if i_cat is not None and i_cat < len(celdas) else ""
                catalogo, pendiente = _catalogo_de(cat_celda)
                
                tipo = _tipo_de(
                    celdas[i_comp] if i_comp is not None and i_comp < len(celdas) else "",
                    celdas[i_tipo] if i_tipo is not None and i_tipo < len(celdas) else "",
                )
                if catalogo and tipo == "text":
                    tipo = "select"
                    
                obligatorio = _babel(
                    celdas[i_obl] if i_obl is not None and i_obl < len(celdas) else ""
                ).startswith("si")
                
                pantalla.campos.append(Campo(
                    nombre=nombre,
                    etiqueta=etiqueta,
                    tipo=tipo,
                    obligatorio=obligatorio,
                    solo_lectura="solo lectura" in _babel(desc),
                    longitud_exacta=int(m_long.group(1)) if m_long else None,
                    catalogo=catalogo,
                ))
            if pantalla.campos:
                r.pantallas.append(pantalla)

    return r
