"""Convierte un Diccionario entregado en PDF (con texto) al Markdown del extractor.

A diferencia del `.docx` —donde la tabla es explicita en el XML— en un PDF la
tabla es una ilusion: texto colocado en posiciones. Reconstruirla es inferencia,
y una inferencia mal hecha mete la descripcion de un campo en la columna del
tipo sin que nadie se entere.

Por eso todo se ancla en la cabecera del propio documento: las columnas se
cortan donde el PDF dibujo los titulos, no donde a este codigo le parezca. Si no
hay cabecera reconocible se falla en voz alta, porque emitir una tabla partida a
ojo seria peor que no leer el archivo.

Un PDF escaneado no tiene texto y no se intenta: ver `es_escaneado`.
"""
import re
import unicodedata

# Titulos que delatan la cabecera de un Diccionario. Basta con tres.
_TITULOS = ("nombre del campo", "nombre", "tipo de dato", "tipo", "límite",
            "limite", "descripción", "descripcion", "ejemplo", "ayuda",
            "catálogo", "catalogo", "obligatorio", "componente")

_MINIMO_TITULOS = 3
# Dos espacios separan columnas; uno separa palabras.
_SEPARADOR = re.compile(r" {2,}")


def _normalizar(texto: str) -> str:
    """Deshace las ligaduras tipograficas del PDF (ﬁ, ﬂ, ﬀ...).

    Sin esto «especiﬁcaciones» viaja al .gpm con un caracter que no casa con
    nada al comparar.
    """
    return unicodedata.normalize("NFKC", texto or "")


def columnas_por_rios(lineas: "list[str]", minimo: int = 2) -> "list[int]":
    """Donde empieza cada columna, por los «rios» de espacios del bloque.

    No se puede anclar en la cabecera: los PDF centran los titulos sobre la
    columna mientras los datos van a la izquierda, asi que «Límite de» empieza
    en la 34 y su dato «30» en la 30. Cortar por la cabecera parte las celdas.

    Un rio es una franja de posiciones que esta en blanco en TODAS las lineas
    del bloque: ahi no hay texto de ninguna fila, luego ahi separa el PDF sus
    columnas. Se exige `minimo` posiciones seguidas para no confundir un rio
    con el espacio entre dos palabras.
    """
    # Solo las lineas que parecen de tabla definen las columnas. Un titulo
    # («DICCIONARIO DE DATOS...») o una fila de seccion («Si eres Notario»)
    # atraviesan los rios y los borran: con ellas dentro, dos columnas se
    # funden en una y el campo sale con el tipo pegado al nombre.
    utiles = [l for l in lineas if len(_SEPARADOR.findall(l)) >= 2]
    if not utiles:
        return []
    ancho = max(len(l) for l in utiles)
    libre = [
        all(pos >= len(l) or l[pos] == " " for l in utiles)
        for pos in range(ancho)
    ]

    cortes, corriendo = [0], 0
    for pos, vacio in enumerate(libre):
        if vacio:
            corriendo += 1
            continue
        if corriendo >= minimo and pos not in cortes:
            cortes.append(pos)
        corriendo = 0
    return cortes


def _es_cabecera(linea: str) -> bool:
    bajo = _normalizar(linea).lower()
    return sum(1 for t in _TITULOS if t in bajo) >= _MINIMO_TITULOS


def _partir(linea: str, cortes: "list[int]") -> "list[str]":
    celdas = []
    for i, ini in enumerate(cortes):
        fin = cortes[i + 1] if i + 1 < len(cortes) else len(linea)
        celdas.append(linea[ini:fin].strip())
    return celdas


def es_escaneado(contenido: bytes) -> bool:
    """Un PDF sin fuentes ni operadores de texto es una foto de papel."""
    return b"/Font" not in contenido


def a_markdown_desde_texto(texto: str) -> str:
    """El texto en modo trazado de un PDF, como tabla Markdown."""
    lineas = [_normalizar(l).rstrip() for l in (texto or "").splitlines()]

    inicio = next((i for i, l in enumerate(lineas) if _es_cabecera(l)), None)
    if inicio is None:
        raise ValueError(
            "no se encontró la cabecera de la tabla en el PDF; "
            "¿está escaneado o no es un Diccionario de Datos?"
        )

    # Los rios se miden sobre el bloque de datos, no sobre la cabecera.
    cortes = columnas_por_rios(lineas[inicio:])
    if len(cortes) < 2:
        raise ValueError("el PDF no separa columnas legibles")

    # El PDF separa registros con una linea en blanco, y una celda larga se
    # parte en varias lineas DENTRO del registro. Agrupar por lineas en blanco
    # es mas fiable que mirar si la primera columna viene vacia: «Fecha de» /
    # «registro» es una sola fila y las dos lineas tienen primera columna.
    bloques: "list[list[str]]" = []
    actual: "list[str]" = []
    for linea in lineas[inicio:]:
        if linea.strip():
            actual.append(linea)
        elif actual:
            bloques.append(actual)
            actual = []
    if actual:
        bloques.append(actual)

    if len(bloques) < 2:
        # Sin lineas en blanco: se cae a la senal debil, primera columna vacia.
        bloques = []
        for linea in lineas[inicio:]:
            if not linea.strip():
                continue
            celdas = _partir(linea, cortes)
            if bloques and not celdas[0]:
                bloques[-1].append(linea)
            else:
                bloques.append([linea])

    filas: "list[list[str]]" = []
    for bloque in bloques:
        fila = [""] * len(cortes)
        for linea in bloque:
            for i, c in enumerate(_partir(linea, cortes)):
                if not c:
                    continue
                # Se une con espacio: una celda partida a mitad de palabra
                # («Alfanu» + «mérico») sale con un espacio de mas, que se ve y
                # se corrige, en vez de pegarse en silencio dos palabras que no
                # iban juntas.
                if not fila[i]:
                    fila[i] = c
                elif len(c) <= 2 and c.isalpha() and c.islower():
                    # Una o dos letras sueltas son el rabo de una palabra que el
                    # PDF partio («especificacione» + «s»). Nadie escribe una
                    # celda de una letra.
                    fila[i] += c
                else:
                    fila[i] = f"{fila[i]} {c}"
        if any(fila):
            filas.append(fila)

    if len(filas) < 2:
        raise ValueError("el PDF trae la cabecera pero ninguna fila de datos")

    ancho = len(cortes)
    salida = ["| " + " | ".join(c.replace("|", "\\|") for c in filas[0]) + " |",
              "| " + " | ".join("---" for _ in range(ancho)) + " |"]
    for f in filas[1:]:
        salida.append("| " + " | ".join(c.replace("|", "\\|") for c in f) + " |")
    return "\n".join(salida) + "\n"


def _paginas(contenido: bytes):
    """Las paginas del PDF. `ValueError` si esta escaneado o no se puede abrir."""
    if es_escaneado(contenido):
        raise ValueError(
            "el PDF está escaneado (es una imagen, no texto). "
            "Adjúntalo como documento de apoyo y sube el texto en Word o Markdown"
        )
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover - depende del extra [web]
        raise ValueError(
            "falta la dependencia para leer PDF; instala con: pip install -e '.[web]'"
        ) from e
    from io import BytesIO
    try:
        return PdfReader(BytesIO(contenido)).pages
    except Exception as e:
        raise ValueError("no se pudo abrir el PDF: ¿está corrupto?") from e


def a_texto(contenido: bytes) -> str:
    """El texto corrido de un `.pdf`, pagina tras pagina, sin buscar tablas.

    Para una plantilla de oficio no hay columnas que reconstruir: basta el
    texto tal cual, con sus {{variables}}.
    """
    paginas = [(p.extract_text() or "").strip() for p in _paginas(contenido)]
    return "\n\n".join(p for p in paginas if p)


def a_markdown(contenido: bytes) -> str:
    """Un `.pdf` con texto, como Markdown. `ValueError` si no se puede leer.

    Un PDF escaneado —una foto de papel— no se intenta: no hay texto que sacar
    y el OCR haria que el compilador pudiera estar seguro y equivocado sobre un
    dato que nadie tecleo.
    """
    if es_escaneado(contenido):
        raise ValueError(
            "el PDF está escaneado (es una imagen, no texto). "
            "Adjúntalo como documento de apoyo y sube el Diccionario en Word o Markdown"
        )
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover - depende del extra [web]
        raise ValueError(
            "falta la dependencia para leer PDF; instala con: pip install -e '.[web]'"
        ) from e

    from io import BytesIO

    try:
        paginas = PdfReader(BytesIO(contenido)).pages
    except Exception as e:
        raise ValueError("no se pudo abrir el PDF: ¿está corrupto?") from e

    # Pagina por pagina: cada una coloca su tabla donde quiere, y medir los
    # rios sobre todas juntas no encuentra ninguna columna comun.
    trozos, fallos = [], []
    for n, pagina in enumerate(paginas, 1):
        texto = pagina.extract_text(extraction_mode="layout") or ""
        if not texto.strip():
            continue
        try:
            md = a_markdown_desde_texto(texto)
        except ValueError as e:
            fallos.append(f"página {n}: {e}")
            continue
        # Solo la primera tabla conserva su cabecera; las demas continuan.
        trozos.append(md if not trozos else "\n".join(md.splitlines()[2:]))

    if not trozos:
        raise ValueError(
            "no se encontró ninguna tabla legible en el PDF"
            + (f" ({fallos[0]})" if fallos else "")
        )
    return "\n".join(trozos) + "\n"
