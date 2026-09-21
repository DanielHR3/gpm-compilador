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
from collections import Counter
import unicodedata
from dataclasses import dataclass, field

from gpmc.nucleo.manifiesto import Campo, OpcionCatalogo
from gpmc.nucleo.huecos import Hueco
from gpmc.nucleo.limites import LIMITE_CAMPO_NOMBRE as LIMITE_NOMBRE_CAMPO

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

# La forma con la que el Diccionario DECLARA el nombre tecnico de una fila, y
# que la guia del equipo de Simplificacion enseña: «[Captura] Campo `@@curp`».
# Una fila que solo lo CITA —«[Solo lectura] Muestra `@@observaciones`
# capturadas por la Direccion»— no lleva esa palabra delante.
_DECLARA_NOMBRE = re.compile(r"[Cc]ampo\s*`?@@(\w+)")
_LONGITUD = re.compile(r"(\d+)\s*caracteres")
_ENDPOINT = re.compile(r"`?([\w/-]+)`?")

# La columna 'campo.nombre' de la plataforma corta los nombres tecnicos largos y
# tumba el import entero con "Data too long for column 'nombre'" (verificado
# 2026-09-02: expediente de Prorroga con `@@fecha_vencimiento_certificado_anterior`,
# 38 chars). El tope vive en nucleo/limites.py (LIMITE_CAMPO_NOMBRE); aquí se
# aplica tanto al nombre propuesto como al que el analista declara a mano.


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
        return _despegar(inequivoco)
    for patron in (r"\s*,\s*", r"\s+/\s+"):
        partes = [p.strip() for p in re.split(patron, crudo) if p.strip()]
        if 2 <= len(partes) <= 40 and all(len(p) <= 60 for p in partes):
            return _despegar(partes)
    return []


def _despegar(partes: list[str]) -> list[str]:
    """Una corrida de 2+ espacios o tabs por dentro de una opcion casi siempre
    son dos valores que perdieron su separador al pegarse de una tabla o Excel
    (verificado 2026-09-02, 'Estado Civil' de Testamento: 'Soltero      casado'
    salia como una sola opcion). Un espacio simple ('Union Libre') es una
    etiqueta legitima y se respeta."""
    salida = []
    for p in partes:
        salida += [t.strip() for t in re.split(r"\s{2,}", p) if t.strip()]
    return salida


def _catalogo_de(celda: str) -> tuple[list[OpcionCatalogo], bool]:
    """Devuelve las opciones y si el catalogo esta declarado como pendiente."""
    crudo = (celda or "").strip()
    # El Diccionario de Testamento envuelve la lista: '(catálogo: A, B, C)'. Sin
    # quitar el prefijo y el parentesis, la primera opcion salia como
    # '(catálogo: A' (verificado 2026-09-02).
    m = re.match(r"^\(\s*cat[aá]logo\s*:\s*(.+?)\s*\)?\s*$", crudo, re.I)
    if m:
        crudo = m.group(1).rstrip(")").strip()
    # La otra forma del mismo envoltorio, con la palabra DELANTE del parentesis:
    # 'Catálogo (A, B, C)'. Publicacion en el Periodico Oficial la usa, y sin
    # esto la primera opcion salia como 'Catálogo (A' y la ultima como 'C)' —
    # no un hueco, sino un .gpm con las opciones corruptas.
    #
    # El parentesis tiene que abrir justo tras la palabra y cerrar al final:
    # 'En línea (validación automática) · Banco...' es una lista con notas, no
    # un envoltorio, y desenvolverla se comeria la segunda opcion.
    m = re.match(
        r"^(?:cat[aá]logo|valores|lista|opciones)\s*[:\-]?\s*\((.+)\)\s*$",
        crudo, re.I,
    )
    # Los parentesis del contenido tienen que quedar balanceados: si no, lo que
    # se recorto no era un envoltorio.
    if m and m.group(1).count("(") == m.group(1).count(")"):
        crudo = m.group(1).strip()
    if not crudo or crudo.upper() == "N/A":
        return [], False
    # Si es un catálogo por archivo, se maneja como un endpoint especial
    m_archivo = re.match(r"^(?:archivo|file)\s*[:\-]\s*(.+?\.csv)$", crudo, re.I)
    if m_archivo:
        # Esto se parsea en _clave_endpoint, aquí devolvemos lista vacía
        return [], False

    partes = _partir_opciones(crudo)
    # Una lista que parte en opciones gana sobre la marca de pendiente. La
    # marca se buscaba como subcadena en toda la celda, y una etiqueta
    # legitima que la contiene tumbaba el catalogo entero: Constancia de No
    # Infraccion declara «En revisión, Pendiente de regularización, Concluido»
    # y salia como DIC-02 falso por la palabra «Pendiente» de la segunda
    # opcion (verificado 2026-09-18). Una celda que de verdad declara el
    # catalogo como pendiente —«Pendiente de confirmar con la dependencia»—
    # no parte en opciones, asi que sigue cayendo en la rama de abajo.
    if len(partes) < 2:
        if any(m in _babel(crudo) for m in MARCAS_PENDIENTE):
            return [], True
        return [], False
    return [
        OpcionCatalogo(etiqueta=p, valor=_babel(p).replace(" ", "_")) for p in partes
    ], False


_RE_VISIBLE = re.compile(
    r"(?:visible|obligatori[ao]|se\s+muestra|se\s+habilita|se\s+genera)"
    r".*?\b(?:solo\s+si|solo\s+cuando|cuando|si)\s+"
    r"(?P<ref>\"[^\"]+\"|`?@@\w+`?)"
    r"\s*(?P<op>≠|!=|=)\s*"
    r"(?P<val>.+)$",
    re.I,
)
_ETIQUETA_CLAVE = re.compile(r"[¿?¡!.:\"`]")


def _clave_etiqueta(texto: str) -> str:
    """Etiqueta -> forma canonica para casar la referencia de una condicion
    ('¿Es Persona Moral?') con el campo que la define."""
    return _ETIQUETA_CLAVE.sub("", _babel(texto)).strip()


def _parece_condicion(texto: str) -> bool:
    t = _babel(texto)
    return ("solo si" in t or "solo cuando" in t
            or ("cuando" in t and ("=" in t or "≠" in t or "∈" in t)))


def _parsear_condicion_visible(texto: str):
    """(ref_crudo, operador, valor_crudo) o None. None = no es una condicion
    simple 'campo = valor'; el llamador decide si es 'siempre visible' o un
    hueco DIC-08."""
    t = (texto or "").strip()
    tb = _babel(t)
    if "∈" in t or "{" in t or "salvo cuando" in tb or "no aplica cuando" in tb:
        return None
    m = _RE_VISIBLE.search(t)
    if not m:
        return None
    val = re.split(r"\s*[,(]", m["val"].strip(), maxsplit=1)[0].strip().strip('"').strip()
    if not val or '"' in val or "∈" in val:
        return None
    if re.search(r"\s(?:y|o|and|or)\s", val, re.I):
        return None
    op = "!=" if m["op"] in ("≠", "!=") else "=="
    return m["ref"].strip().strip('"').strip("`"), op, val


_RE_CONJUNTO = re.compile(
    r"(?P<salvo>salvo\s+cuando|no\s+aplica\s+cuando|cuando|solo\s+si|si)\s*"
    r"`?@@(?P<campo>\w+)`?\s*∈\s*\{(?P<valores>[^}]*)\}",
    re.I,
)


def _condicion_desde_conjunto(texto: str, indice: dict):
    """«salvo cuando @@c ∈ {A, B}» -> «≠A Y ≠B». None si no aplica.

    El Diccionario escribe la pertenencia a un conjunto con ∈, y hasta ahora el
    parser se rendia en cuanto veia ese simbolo: cada frase asi era un DIC-08
    que el analista tenia que rearmar a mano.

    La forma NEGADA es la unica que se puede traducir: «no estar en {A, B}» es
    «≠A Y ≠B», y la conjuncion es justo lo que el modelo sabe expresar desde
    SP2. La forma positiva —«∈ {A, B}»— es una disyuncion, y `Condicion` no
    tiene O: convertirla en «=A Y =B» daria una condicion que no se cumple
    nunca, asi que se deja como hueco y lo decide una persona.
    """
    from gpmc.nucleo.manifiesto import Clausula, Condicion

    m = _RE_CONJUNTO.search(texto or "")
    if not m:
        return None
    if not re.match(r"salvo|no\s+aplica", _babel(m["salvo"])):
        return None

    campo = m["campo"]
    if campo not in indice["campos"]:
        return None
    catalogo = indice["campos"][campo].catalogo

    valores = []
    for bruto in m["valores"].split(","):
        v = _babel(bruto)
        if not v:
            continue
        hallado = next((o.valor for o in catalogo if _babel(o.etiqueta) == v), None)
        if hallado is None:
            # Un solo valor que no casa deja la condicion incompleta, y una
            # condicion incompleta es peor que preguntar.
            return None
        valores.append(hallado)

    if not valores:
        return None
    primero, resto = valores[0], valores[1:]
    return Condicion(
        campo=campo, operador="!=", igual=primero,
        y=[Clausula(campo=campo, operador="!=", igual=v) for v in resto],
    )


# Siglas que se escriben en mayusculas en un documento de gobierno.
_SIGLAS = {"curp", "rfc", "ine", "pdf", "api", "id", "url", "iva", "uma"}

# Abreviaturas que el Diccionario usa dentro del nombre tecnico.
_ABREVIATURAS = {"cp": "Código Postal", "dom": "Domicilio", "tel": "Teléfono",
                 "num": "Número", "doc": "Documento", "fec": "Fecha",
                 "paterno": "Apellido paterno", "materno": "Apellido materno"}

# Sufijos de rol: van al final del nombre y piden su articulo. Se escriben
# completos porque el genero lo decide la palabra, no una regla.
_ROLES = {
    "sol": "del solicitante", "solicitante": "del solicitante",
    "rep": "del representante", "representante": "del representante",
    "ut": "de la Unidad de Transparencia",
    "dependencia": "de la dependencia",
    "empresa": "de la empresa",
}


def etiqueta_desde_nombre(nombre: str) -> str:
    """La etiqueta que vera el ciudadano, a partir del nombre tecnico.

    Se emite AL .gpm y se imprime en el formulario publicado, asi que
    'Nombres sol' o 'Cp sol' no valen: son la clave interna con un espacio.

    Solo se expande lo que esta en las tablas de arriba. Un nombre que no
    reconozco se deja legible —guiones bajos por espacios y mayuscula
    inicial— en vez de inventarle un significado.
    """
    partes = [p for p in (nombre or "").split("_") if p]
    if not partes:
        return ""

    cola = ""
    if len(partes) > 1 and partes[-1].lower() in _ROLES:
        cola = _ROLES[partes[-1].lower()]
        partes = partes[:-1]

    palabras = []
    for i, p in enumerate(partes):
        b = p.lower()
        if b in _SIGLAS:
            palabras.append(b.upper())
        elif b in _ABREVIATURAS:
            palabras.append(_ABREVIATURAS[b])
        else:
            palabras.append(p.capitalize() if i == 0 else p.lower())

    cuerpo = " ".join(palabras)
    return f"{cuerpo} {cola}".strip() if cola else cuerpo


def _catalogo_en_la_descripcion(desc: str) -> "list[OpcionCatalogo]":
    """Opciones escritas entre parentesis dentro de la descripcion, o [].

    Se exige mas de un elemento: «Validación regex (exact_length[5])» lleva un
    parentesis y no es un catalogo. Con un solo elemento no hay lista, y
    convertirlo en un select de una opcion seria peor que dejar el hueco.
    """
    for bruto in re.findall(r"\(([^()]*)\)", desc or ""):
        partes = [p.strip() for p in bruto.split(",")]
        partes = [p for p in partes if p]
        if len(partes) < 2:
            continue
        # Nada de listas tecnicas: rutas, llamadas, tipos.
        if any(re.search(r"[`\[\]{}=<>/\\]|@@", p) for p in partes):
            continue
        return [
            OpcionCatalogo(etiqueta=p, valor=_babel(p).replace(" ", "_"))
            for p in partes
        ]
    return []


def _resolver_condicion_visible(
    ref_crudo: str, operador: str, valor_crudo: str, indice: dict,
) -> "Optional[object]":
    """Resuelve la referencia a un @@nombre ya visto y el valor contra el
    catalogo de ese campo. Devuelve una Condicion, o None si no resuelve."""
    from gpmc.nucleo.manifiesto import Condicion

    if ref_crudo.startswith("@@"):
        ref_nombre = ref_crudo[2:]
        if ref_nombre not in indice["campos"]:
            return None
    else:
        ref_nombre = indice["por_etiqueta"].get(_clave_etiqueta(ref_crudo))
        if ref_nombre is None:
            return None

    v = _babel(valor_crudo)
    if v in ("si", "sí"):
        igual = "si"
    elif v == "no":
        igual = "no"
    else:
        ref_campo = indice["campos"][ref_nombre]
        igual = next(
            (o.valor for o in ref_campo.catalogo if _babel(o.etiqueta) == v), None
        )
        if igual is None:
            # El Diccionario declara la opcion con una nota —«En línea
            # (validación automática)»— y la condicion la cita por su parte
            # util: «= En línea». Exigir la cadena completa dejaba el campo sin
            # condicion y emitia un DIC-08 por una diferencia de redaccion.
            #
            # Solo se acepta si UNA opcion casa: si la cita fuera ambigua entre
            # dos, adivinar seria peor que preguntar.
            def _sin_nota(et: str) -> str:
                return _babel(re.sub(r"\s*\([^()]*\)\s*$", "", et or "")).strip()

            candidatas = [o for o in ref_campo.catalogo if _sin_nota(o.etiqueta) == v]
            if len(candidatas) != 1:
                return None
            igual = candidatas[0].valor
    return Condicion(campo=ref_nombre, igual=igual, operador=operador)


def _unico(nombre: str, usados: set) -> str:
    """El mismo nombre no se puede proponer dos veces.

    El sufijo entra DENTRO de `LIMITE_NOMBRE_CAMPO`: pasarse del tope es el
    'Data too long for column nombre' de PLAT-7.
    """
    if nombre not in usados:
        usados.add(nombre)
        return nombre
    for i in range(2, 100):
        sufijo = f"_{i}"
        cand = (nombre[:LIMITE_NOMBRE_CAMPO - len(sufijo)].strip("_") + sufijo)
        if cand not in usados:
            usados.add(cand)
            return cand
    usados.add(nombre)
    return nombre


def _extraer_campos(
    filas: list[str], pantalla: PantallaExtraida, r: Resultado,
    indice: "Optional[dict]" = None,
):
    if indice is None:
        indice = {"por_etiqueta": {}, "campos": {}}
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
    i_vis = col("condicion de visibilidad", "visibilidad")
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
        # Un `@@` de la descripcion es el nombre de ESTA fila solo si lo declara
        # («Campo @@x»). Si solo lo cita y ese nombre lo declara otra fila, es
        # una REFERENCIA: quedarselo creaba dos campos con el mismo nombre.
        #
        # Medido el 2026-09-21 sobre el lote de reingenieria: 27 campos fantasma
        # en 5 de 6 tramites, ocho en Reposicion de Certificado, donde tres
        # campos acabaron llamandose `estatus_tramite` y el que ganaba no traia
        # catalogo. La regla se acordo con Simplificacion ese mismo dia.
        ajenos = indice.get("declarados") or set()
        propios = _DECLARA_NOMBRE.findall(desc)
        tecnicos = propios or [t for t in _CAMPO_TECNICO.findall(desc) if t not in ajenos]

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
            # Dos filas que dicen «Campo @@x» declaran el mismo dato dos veces.
            # No se renombra a la callada —cual de las dos es cual solo lo sabe
            # quien escribio el Diccionario—: se reporta para que lo corrijan
            # donde vive el dato. El validador lo vuelve a cazar (EST-08) por si
            # el `.gpm` llega editado a mano.
        else:
            declarado = False
            # Se recorta a LIMITE_NOMBRE_CAMPO y se limpia el '_' que quede
            # colgando al cortar a mitad de palabra (ver _capar_nombre).
            nombre = re.sub(r"[^a-z0-9]+", "_", _babel(etiqueta)).strip("_")[:LIMITE_NOMBRE_CAMPO].strip("_")
            # Un nombre que proponemos NOSOTROS no puede chocar con otro. Al
            # capar a 30, «Vista de solo lectura (Ciudadano → Notario)» y
            # «…(Ciudadano → Área)» quedaban en la misma cadena: eran 74 de los
            # 92 campos fantasma que quedaban el 2026-09-21. El sufijo se
            # aplica DENTRO del limite, que es lo que hace chocar los nombres.
            nombre = _unico(nombre, indice.setdefault("nombres_usados", set()))
            r.huecos.append(Hueco(
                "por_confirmar", "DIC-01", pantalla.id,
                f"el campo '{etiqueta}' no declara nombre técnico @@ en su descripción ni en la columna Variable; se propuso '{nombre}'",
                propuesta=nombre,
            ))


        if declarado:
            nombre_original = nombre
            nombre, capado = _capar_nombre(nombre)
            if capado:
                r.huecos.append(Hueco(
                    "falta_dato", "DIC-06", pantalla.id,
                    f"el nombre técnico declarado para '{etiqueta}' excede los "
                    f"{LIMITE_NOMBRE_CAMPO} caracteres que admite la columna 'campo.nombre' "
                    f"de la plataforma (el import falla con 'Data too long'); se emitió "
                    f"como '{nombre}'. El compilador mantendrá un alias para que tus fórmulas con "
                    f"@@{nombre_original} sigan funcionando sin que las modifiques.",
                    propuesta=nombre,
                ))
                indice["campos"][nombre_original] = None # placeholder to be updated

        if es_columna_variable and (etiqueta == nombre or not etiqueta or etiqueta.lower() == (nombre_original.lower() if declarado else nombre.lower())):
            etiqueta = etiqueta_desde_nombre(nombre)
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
        # El Diccionario Hibrido no tiene columna de catalogo y escribe las
        # opciones entre parentesis dentro de la descripcion: «Clasificación de
        # la Unidad de Transparencia (Entregable, Reservada, Inexistente)». Se
        # emitia DIC-07 —«es select pero no se extrajo ninguna opción»— con las
        # opciones a la vista en la misma fila.
        if not catalogo and not pendiente and tipo in ("select", "radio"):
            catalogo = _catalogo_en_la_descripcion(desc)
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

        campo = Campo(
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
        )

        # Condicion de visibilidad. Se resuelve contra los campos ya vistos
        # (el que gobierna casi siempre viene antes). Si la condicion parece
        # una condicion pero no se puede interpretar con seguridad, se reporta
        # DIC-08 y el campo queda siempre visible — no se adivina.
        vis_cruda = celdas[i_vis] if i_vis is not None and i_vis < len(celdas) else ""
        parsed = _parsear_condicion_visible(vis_cruda)
        if parsed is not None:
            cond = _resolver_condicion_visible(*parsed, indice)
            if cond is not None:
                campo.condicion_visible = cond
            else:
                r.huecos.append(Hueco(
                    "falta_dato", "DIC-08", f"{pantalla.id}::{nombre}",
                    f"la condición de visibilidad de '{etiqueta}' ({nombre}) no se "
                    f"pudo interpretar: «{vis_cruda.strip()}»; configúrala a mano",
                ))
        elif _parece_condicion(vis_cruda):
            # Antes de rendirse: «salvo cuando @@c ∈ {A, B}» es «≠A Y ≠B», que
            # el modelo si sabe expresar. La forma positiva sigue siendo hueco
            # porque pide una disyuncion y `Condicion` no tiene O.
            cond = _condicion_desde_conjunto(vis_cruda, indice)
            if cond is not None:
                campo.condicion_visible = cond
            else:
                r.huecos.append(Hueco(
                    "falta_dato", "DIC-08", f"{pantalla.id}::{nombre}",
                    f"la condición de visibilidad de '{etiqueta}' ({nombre}) no se "
                    f"pudo interpretar: «{vis_cruda.strip()}»; configúrala a mano",
                ))

        # El nombre lo puso el Diccionario —columna Variable o un `@@` en la
        # descripcion— y ya lo usa otro campo. NO se renombra: cual de los dos
        # es cual solo lo sabe quien lo escribio. Se reporta aqui, con el campo
        # ya construido, para poder decir DONDE esta el gemelo y si parece el
        # mismo dato o dos distintos: visto en pantalla el 2026-09-21, sin eso
        # hay que buscarlo a mano entre 41 campos.
        if declarado:
            gemelos = indice.setdefault("gemelos", {})
            previo = gemelos.get(nombre)
            if previo is not None and nombre not in indice.setdefault("dic09_reportados", set()):
                indice["dic09_reportados"].add(nombre)
                p_ant, e_ant, t_ant = previo
                mismo = (t_ant == campo.tipo and _babel(e_ant) == _babel(etiqueta))
                if mismo:
                    que_es = (f"parece el mismo dato mostrado de nuevo: «{e_ant}» en "
                              f"{p_ant} y «{etiqueta}» en {pantalla.nombre or pantalla.id} "
                              f"son iguales. Déjalo en una sola fila y di en el TO-BE "
                              f"dónde se vuelve a mostrar")
                else:
                    que_es = (f"son dos datos distintos con el mismo nombre: «{e_ant}» "
                              f"({t_ant}) en {p_ant} y «{etiqueta}» ({campo.tipo}) en "
                              f"{pantalla.nombre or pantalla.id}. Renombra uno de los dos "
                              f"en el Diccionario")
                r.huecos.append(Hueco(
                    "falta_dato", "DIC-09", pantalla.id,
                    f"el nombre técnico '@@{nombre}' lo declaran dos campos; {que_es}",
                ))
            gemelos.setdefault(nombre, (pantalla.nombre or pantalla.id, etiqueta, campo.tipo))

        indice["campos"][nombre] = campo
        if declarado and capado:
            indice["campos"][nombre_original] = campo
        indice["por_etiqueta"].setdefault(_clave_etiqueta(etiqueta), nombre)
        pantalla.campos.append(campo)


def extraer(texto: str) -> Resultado:
    r = Resultado()
    # Indice de campos vistos, compartido entre pantallas: una condicion de
    # visibilidad casi siempre nombra un campo de una pantalla anterior.
    # Una pasada previa por el documento entero: que nombres tecnicos DECLARA
    # alguna fila. Hace falta antes de recorrer las pantallas porque una fila
    # puede citar un campo que se declara mas adelante.
    declarados = _DECLARA_NOMBRE.findall(texto)
    indice = {"por_etiqueta": {}, "campos": {},
              "declarados": set(declarados),
              "declarados_n": Counter(declarados)}
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

        _extraer_campos(filas, pantalla, r, indice)
        r.pantallas.append(pantalla)

    if not r.pantallas:
        # `por_confirmar`, no `falta_dato`: esto describe una decision que el
        # compilador YA tomo —agrupar todo en una pantalla—, igual que DIC-05
        # cuando propone una etiqueta. No hay respuesta que dar: el unico
        # control posible era "lo configuro a mano", que solo reconoce el
        # hueco. Bloquear la descarga del .gpm no arreglaba nada; solo exigia
        # una configuracion manual para poder seguir.
        r.huecos.append(Hueco(
            "por_confirmar", "DIC-04", "",
            "el Diccionario no separa el trámite en pantallas (falta la cabecera "
            "'### Pantalla N — ACTOR — Nombre'), así que todos los campos quedaron "
            "en una sola. Si el trámite se captura de una vez, está bien así",
        ))
        
        filas = [l for l in texto.splitlines() if l.strip().startswith("|")]
        filas = [l for l in filas if not _es_separador(l)]
        if len(filas) >= 2:
            pantalla = PantallaExtraida(id="p1", numero=1, nombre="Datos Generales", actor="usuario")
            _extraer_campos(filas, pantalla, r, indice)
            if pantalla.campos:
                r.pantallas.append(pantalla)

    return r
