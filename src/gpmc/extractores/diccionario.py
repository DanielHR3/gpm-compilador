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
_PASO_STEPPER = re.compile(r"\(\s*Paso\s+(\d+)", re.I)          # captura el numero
_PASO_STEPPER_FULL = re.compile(r"\s*\(\s*Paso\s+\d+[^)]*\)", re.I)  # el parentesis entero
# Anotacion de mockup que el analista deja al final del nombre de pantalla, del
# tipo '*(Tarea GPM #7920 en una prueba/mockup ...)*'. No es parte del nombre y,
# sin quitarla, desborda la columna 'nombre' de la plataforma y tumba el import
# entero con 'Data too long' (verificado 2026-08-31, ver actas/).
_ANOTACION_MOCKUP = re.compile(r"\s*\*\(.*\)\*\s*$")
# El cuerpo de una pantalla termina en la siguiente pantalla o en el siguiente
# encabezado de igual o mayor jerarquia. Sin este corte, las tablas de las
# Secciones 2 a 5 del Diccionario se absorben dentro de la ultima pantalla.
_CORTE = re.compile(r"^#{1,3}\s+(?!#)", re.M)
_CAMPO_TECNICO = re.compile(r"@@(\w+)")
_LONGITUD = re.compile(r"(\d+)\s*caracteres")
_ENDPOINT = re.compile(r"`?([\w/-]+)`?")

# La columna 'campo.nombre' de la plataforma corta los nombres tecnicos largos y
# tumba el import entero con "Data too long for column 'nombre'" (verificado
# 2026-09-02: expediente de Prorroga con `@@fecha_vencimiento_certificado_anterior`,
# 38 chars). Los exports autenticos no pasan de 31. 30 es el tope que ya usaba la
# ruta de nombre propuesto; ahora se aplica tambien al nombre que el analista
# declara a mano (columna Variable o `@@` en la Descripcion).
LIMITE_NOMBRE_CAMPO = 30


def _capar_nombre(nombre: str) -> "tuple[str, bool]":
    """Devuelve (nombre, fue_capado). Recorta a LIMITE_NOMBRE_CAMPO y limpia el
    '_' que quede colgando al cortar a mitad de palabra."""
    if len(nombre) <= LIMITE_NOMBRE_CAMPO:
        return nombre, False
    return nombre[:LIMITE_NOMBRE_CAMPO].strip("_"), True

COMPONENTES = [
    # 'selector de fecha' y 'calendario' van antes que 'select': "Selector de
    # fecha (calendario)" contiene la subcadena "select" ("sele-ctor") y se
    # clasificaba como lista desplegable, saliendo como un select vacio en la
    # vista (verificado 2026-09-02, Prorroga: "Fecha de Vencimiento del
    # Certificado Anterior").
    ("selector de fecha", "date"), ("calendario", "date"),
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


def _limpiar_celda(celda: str) -> str:
    """Quita acentos graves, asteriscos y espacios. El Diccionario escribe los
    identificadores entre acentos graves por costumbre de markdown."""
    return re.sub(r"[`*]", "", celda or "").strip()


def _clave_endpoint(celda: str) -> Optional[str]:
    """'`mgem` (INEGI)' -> 'mgem'. El proveedor entre parentesis es informativo:
    el registro de nucleo/integraciones ya sabe de quien es cada endpoint."""
    limpio = _limpiar_celda(celda)
    if not limpio or limpio.upper() == "N/A":
        return None
    m = _ENDPOINT.match(limpio)
    return m.group(1) if m else None


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


def _partir_opciones(crudo: str) -> list[str]:
    """Divide la lista de opciones. Los Diccionarios no son consistentes en el
    separador: el estandar usa ' · ', pero varios expedientes reales (Reposicion,
    Holograma) usan comas ('Doble cero, Cero, Uno, Dos') y los radios booleanos
    escriben 'Sí / No'.

    ' · ', ' • ', ';' y '<br>' son inequivocos: si aparecen, es una lista, sin
    limite de conteo ni de tamano (los municipios de Hidalgo son 84; un organismo
    puede tener un nombre de 130 caracteres). La coma y la barra son ambiguas:
    ahi si se descarta la prosa —fragmentos larguisimos o demasiados no son
    opciones— y 'Persona física, Persona moral / institución' parte por la coma
    en 2, sin seguir partiendo por la barra."""
    inequivoco = [
        p.strip() for p in
        re.split(r"\s+·\s+|\s+•\s+|\s*;\s*|\s*<br\s*/?>\s*", crudo)
        if p.strip()
    ]
    if len(inequivoco) >= 2:
        return inequivoco
    for patron in (r"\s*,\s*", r"\s+/\s+"):
        partes = [p.strip() for p in re.split(patron, crudo) if p.strip()]
        if 2 <= len(partes) <= 40 and all(len(p) <= 60 for p in partes):
            return partes
    return []


def _catalogo_de(celda: str) -> tuple[list[OpcionCatalogo], bool]:
    """Devuelve las opciones y si el catalogo esta declarado como pendiente."""
    crudo = (celda or "").strip()
    # El Diccionario de Testamento envuelve la lista: '(catálogo: A, B, C)'. Sin
    # quitar el prefijo y el parentesis, la primera opcion salia como
    # '(catálogo: A' (verificado 2026-09-02).
    m = re.match(r"^\(\s*cat[aá]logo\s*:\s*(.+?)\s*\)?\s*$", crudo, re.I)
    if m:
        crudo = m.group(1).rstrip(")").strip()
    if not crudo or crudo.upper() == "N/A":
        return [], False
    if any(m in _babel(crudo) for m in MARCAS_PENDIENTE):
        return [], True
    partes = _partir_opciones(crudo)
    if len(partes) < 2:
        return [], False
    return [
        OpcionCatalogo(etiqueta=p, valor=_babel(p).replace(" ", "_")) for p in partes
    ], False


def _extraer_campos(filas: list[str], pantalla: PantallaExtraida, r: Resultado):
    if len(filas) < 2:
        return

    columnas = [_babel(c) for c in _celdas(filas[0])]

    def col(*nombres, defecto=None):
        for n in nombres:
            for j, c in enumerate(columnas):
                if n in c:
                    return j
        return defecto

    i_nombre = col("nombre del campo", "campo", defecto=0)
    i_var = col("variable")
    es_columna_variable = i_var is not None

    i_tipo = col("tipo de dato", "tipo", defecto=1)
    i_comp = col("componente sugerido", "componente")
    i_obl = col("obligatorio", defecto=3)
    i_lim = col("limite", "especificaciones")
    i_cat = col("catalogo de valores", "catalogo")
    i_desc = col("descripcion", "comportamiento")
    
    # Fase A: Columnas nuevas
    i_dep = col("dependencia")
    i_end = col("endpoint", "api")

    for fila in filas[1:]:
        celdas = _celdas(fila)
        if len(celdas) < 3 or not celdas[i_nombre]:
            continue

        etiqueta = re.sub(r"\*+", "", celdas[i_nombre]).strip()
        etiqueta = etiqueta.replace("`", "")

        desc = celdas[i_desc] if i_desc is not None and i_desc < len(celdas) else ""
        tecnicos = _CAMPO_TECNICO.findall(desc)

        nombre = None
        if es_columna_variable and i_var < len(celdas):
            var_cruda = celdas[i_var].strip().replace("`", "")
            if var_cruda and re.fullmatch(r"[A-Za-z_]\w*", var_cruda):
                nombre = var_cruda

        if nombre:
            declarado = True
        elif tecnicos:
            nombre = tecnicos[0]
            declarado = True
        else:
            declarado = False
            # Se recorta a LIMITE_NOMBRE_CAMPO y se limpia el '_' que quede
            # colgando al cortar a mitad de palabra (ver _capar_nombre).
            nombre = re.sub(r"[^a-z0-9]+", "_", _babel(etiqueta)).strip("_")[:LIMITE_NOMBRE_CAMPO].strip("_")
            r.huecos.append(Hueco(
                "por_confirmar", "DIC-01", pantalla.id,
                f"el campo '{etiqueta}' no declara nombre técnico @@ en su descripción ni en la columna Variable; se propuso '{nombre}'",
                propuesta=nombre,
            ))

        if declarado:
            nombre, capado = _capar_nombre(nombre)
            if capado:
                r.huecos.append(Hueco(
                    "falta_dato", "DIC-06", pantalla.id,
                    f"el nombre técnico declarado para '{etiqueta}' excede los "
                    f"{LIMITE_NOMBRE_CAMPO} caracteres que admite la columna 'campo.nombre' "
                    f"de la plataforma (el import falla con 'Data too long'); se emitió "
                    f"como '{nombre}'. Ajusta este nombre y sus referencias @@ en la "
                    f"Propuesta TO-BE y en las fórmulas del Diccionario.",
                    propuesta=nombre,
                ))

        if es_columna_variable and (etiqueta == nombre or not etiqueta or etiqueta.lower() == nombre.lower()):
            etiqueta = nombre.replace("_", " ").capitalize()
            r.huecos.append(Hueco(
                "por_confirmar", "DIC-05", pantalla.id,
                f"'{nombre}' no trae etiqueta visible en el Diccionario; se propuso '{etiqueta}'",
                propuesta=etiqueta,
            ))

        limite = celdas[i_lim] if i_lim is not None and i_lim < len(celdas) else ""
        m_long = _LONGITUD.search(limite or "")

        tipo_dato = _babel(celdas[i_tipo] if i_tipo is not None and i_tipo < len(celdas) else "")
        componente = _babel(celdas[i_comp] if i_comp is not None and i_comp < len(celdas) else "")
        tipo = _tipo_de(
            celdas[i_comp] if i_comp is not None and i_comp < len(celdas) else "",
            celdas[i_tipo] if i_tipo is not None and i_tipo < len(celdas) else "",
        )

        cat_celda = celdas[i_cat] if i_cat is not None and i_cat < len(celdas) else ""
        catalogo, pendiente = _catalogo_de(cat_celda)
        # Fallback: varios expedientes escriben las opciones en la columna
        # Limite/Especificaciones ('Sí / No' para los radios booleanos) y dejan
        # 'Catálogo de Valores' en 'N/A'. Solo para select/radio y solo si no hay
        # ya opciones ni marca de pendiente.
        if not catalogo and not pendiente and tipo in ("select", "radio"):
            catalogo, pendiente = _catalogo_de(limite)
        # Un campo Boolean (o 'Switch / radio Sí-No') sin lista parseable: su
        # dominio ES {Sí, No}. Derivarlo no es inventar. Sin esto salia sin
        # opciones y la vista reventaba con foreach() (verificado 2026-09-02,
        # 'Disposiciones de Contenido Irrevocable' de Testamento).
        if not catalogo and not pendiente and (
            "boolean" in tipo_dato or "si-no" in componente or "sí-no" in componente
            or "si/no" in _babel(limite) or "sí/no" in _babel(limite)
        ):
            catalogo = [
                OpcionCatalogo(etiqueta="Sí", valor="si"),
                OpcionCatalogo(etiqueta="No", valor="no"),
            ]
            if tipo not in ("select", "radio"):
                tipo = "radio"
        if pendiente:
            r.huecos.append(Hueco(
                "falta_dato", "DIC-02", pantalla.id,
                f"el catálogo de '{etiqueta}' está declarado como pendiente en el Diccionario; no se emite",
            ))

        if catalogo and tipo == "text":
            tipo = "select"

        obligatorio = _babel(
            celdas[i_obl] if i_obl is not None and i_obl < len(celdas) else ""
        ).startswith("si")

        # Fase A: dependencia y endpoint, normalizados.
        dep_tipo = None
        dep_campo = None
        endpoint = None

        if i_dep is not None and i_dep < len(celdas):
            val_dep = _limpiar_celda(celdas[i_dep]).lstrip("@")
            if val_dep and val_dep.upper() != "N/A":
                if val_dep.lower() == "api_ajax":
                    # No es un campo padre: marca que a este campo lo llena una
                    # peticion. Esta fase no emite el componente (ver spec §6).
                    dep_tipo = "api_ajax"
                    r.huecos.append(Hueco(
                        "por_confirmar", "API-04", pantalla.id,
                        f"'{nombre}' se autocompleta por API; esta versión no emite "
                        f"el componente y el campo queda de captura manual",
                    ))
                else:
                    dep_tipo = "campo"
                    dep_campo = val_dep

        if i_end is not None and i_end < len(celdas):
            endpoint = _clave_endpoint(celdas[i_end])

        origen = endpoint

        # DIC-07: un select/radio que quedo sin opciones, sin marca de pendiente
        # y sin endpoint. Un select vacio revienta la vista de la plataforma con
        # foreach() (radio/display.php, CampoSelect.php), asi que el compilador lo
        # emite como campo de texto. Se reporta para que una persona escriba el
        # catalogo en el Diccionario y el campo vuelva a ser una lista.
        if tipo in ("select", "radio") and not catalogo and not pendiente \
                and not endpoint and dep_tipo != "api_ajax":
            r.huecos.append(Hueco(
                "falta_dato", "DIC-07", pantalla.id,
                f"el campo '{etiqueta}' es {tipo} pero no se extrajo ninguna opción "
                f"(ni en 'Catálogo de Valores' ni en 'Límite/Especificaciones'); "
                f"el compilador lo emite como campo de texto hasta que se defina el catálogo",
            ))

        pantalla.campos.append(Campo(
            nombre=nombre,
            etiqueta=etiqueta,
            tipo=tipo,
            obligatorio=obligatorio,
            solo_lectura="solo lectura" in _babel(desc),
            longitud_exacta=int(m_long.group(1)) if m_long else None,
            catalogo=catalogo,
            dependencia_tipo=dep_tipo,
            dependencia_campo=dep_campo,
            endpoint=endpoint,
            origen=origen,
        ))


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

        nombre_crudo = _ANOTACION_MOCKUP.sub("", m["nombre"].strip())
        m_paso = _PASO_STEPPER.search(nombre_crudo)
        pantalla = PantallaExtraida(
            id=f"p{m['num']}",
            numero=int(m['num']),
            nombre=_PASO_STEPPER_FULL.sub("", nombre_crudo).strip(" —-"),
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

        _extraer_campos(filas, pantalla, r)
        r.pantallas.append(pantalla)

    if not r.pantallas:
        r.huecos.append(Hueco(
            "falta_dato", "DIC-04", "",
            "no se encontró ninguna cabecera '### Pantalla N — ACTOR — Nombre'; se agruparon todos los campos en una sola pantalla por defecto",
        ))
        
        filas = [l for l in texto.splitlines() if l.strip().startswith("|")]
        filas = [l for l in filas if not _es_separador(l)]
        if len(filas) >= 2:
            pantalla = PantallaExtraida(id="p1", numero=1, nombre="Datos Generales", actor="usuario")
            _extraer_campos(filas, pantalla, r)
            if pantalla.campos:
                r.pantallas.append(pantalla)

    return r
