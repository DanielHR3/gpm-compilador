"""Interfaz de linea de comandos del compilador GPM."""

from typing import Optional
import argparse
import tempfile
import shutil
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from gpmc.compilador.a_gpm import compilar
from gpmc.estimador import estimar
from gpmc.extractores.expediente import SinPermiso, extraer_expediente
from gpmc.agentes.bitacora import RUTA_BITACORA
from gpmc.agentes.dic08 import proponer_lote
from gpmc.agentes.proveedor import ErrorDeRed, RespuestaInvalida
from gpmc.nucleo.formato import escribir
from gpmc.nucleo.huecos import NIVELES, bloquean
from gpmc.nucleo.manifiesto import guardar
from gpmc.planeacion.proyeccion import proyectar
from gpmc.planeacion.registro import Registro, capacidad, estado, sembrar_desde_wiki
from gpmc.simulador.analisis import analizar
from gpmc.simulador.html import generar as generar_simulador
from gpmc.compilador.aprobacion import generar_aprobacion
from gpmc.nucleo.manifiesto import cargar
from gpmc.validador.reglas import Hallazgo, revisar, revisar_archivo


def _imprimir(hallazgos: list[Hallazgo]) -> int:
    if not hallazgos:
        print("Revision completada: sin hallazgos.")
        return 0

    bloqueantes = [h for h in hallazgos if h.gravedad == "bloqueante"]
    avisos = [h for h in hallazgos if h.gravedad == "aviso"]

    for h in bloqueantes:
        print(f"  [BLOQUEANTE] {h.codigo}  {h.ubicacion}\n               {h.mensaje}")
    for h in avisos:
        print(f"  [aviso]      {h.codigo}  {h.ubicacion}\n               {h.mensaje}")

    print(f"\n{len(bloqueantes)} bloqueante(s), {len(avisos)} aviso(s).")
    return 1 if bloqueantes else 0


_ROTULO = {
    "bloqueante": ("■", "BLOQUEANTE", "resolver antes de compilar"),
    "falta_dato": ("▲", "FALTAN DATOS", "un humano debe escribirlos"),
    "por_confirmar": ("·", "POR CONFIRMAR", "el extractor propuso un valor, revísalos de un vistazo"),
}


def _imprimir_huecos(huecos, completo: bool) -> None:
    for nivel in NIVELES:
        grupo = [h for h in huecos if h.nivel == nivel]
        if not grupo:
            continue
        glifo, titulo, nota = _ROTULO[nivel]
        print(f"\n{glifo} {len(grupo)} {titulo} — {nota}")
        limite = len(grupo) if (completo or nivel != "por_confirmar") else 3
        for h in grupo[:limite]:
            loc = f"{h.ubicacion} " if h.ubicacion else ""
            flecha = f" → {h.propuesta}" if h.propuesta else ""
            print(f"  [{h.codigo}] {loc}{h.mensaje}{flecha}")
        if len(grupo) > limite:
            print(f"  … y {len(grupo) - limite} más   (usa --huecos para verlos todos)")


def cargar_entorno(ruta: Optional[Path] = None) -> int:
    """Carga CLAVE=valor desde ~/.config/gpmc/entorno sin pisar lo que ya este en
    el entorno. Asi la llave del proveedor de IA nunca pasa por el plist ni por
    el instalador. Devuelve cuantas variables cargo."""
    ruta = ruta if ruta is not None else Path.home() / ".config" / "gpmc" / "entorno"
    if not ruta.exists():
        return 0
    n = 0
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = (x.strip() for x in linea.split("=", 1))
        if clave and clave not in os.environ:
            os.environ[clave] = valor
            n += 1
    return n


def _proveedor_para_medir():
    from gpmc.agentes import crear_proveedor
    return crear_proveedor()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="gpmc", description="Compilador de tramites GPM")
    sub = parser.add_subparsers(dest="orden")

    c = sub.add_parser("compilar", help="manifiesto YAML -> archivo .gpm")
    c.add_argument("manifiesto", type=Path, nargs="?",
                   help="manifiesto YAML; omítelo si pasas --desde-expediente")
    c.add_argument("-o", "--salida", type=Path, required=True)
    # Vacío por omisión: compilar() deriva el proceso_id del nombre del trámite,
    # igual que el asistente web. La plataforma lo reasigna al importar (PLAT-4),
    # así que el valor emitido no llega a producción; lo que importa es que los dos
    # caminos —CLI y web— deriven igual y de forma determinista.
    c.add_argument("--proceso-id", default="")
    c.add_argument("--modo-pruebas", action="store_true",
                   help="agrupa todas las pantallas en una sola Tarea Inicial (Test UI)")
    c.add_argument("--desde-expediente", type=Path, default=None,
                   help="re-extrae del expediente y aplica la puerta del linter "
                        "(huecos bloqueantes o de falta de datos) antes de compilar")

    v = sub.add_parser("validar", help="revisa un .gpm existente")
    v.add_argument("archivo", type=Path)

    e = sub.add_parser("extraer", help="carpeta de expediente -> manifiesto YAML")
    e.add_argument("expediente", type=Path)
    e.add_argument("-o", "--salida", type=Path, required=True)
    e.add_argument("--huecos", "-H", action="store_true",
                   help="lista todos los huecos sin truncar")
    e.add_argument("--nombre", default="",
                   help="nombre del trámite cuando no hay AS-IS (P-03); "
                        "el asistente web lo pide en la portada")
    e.add_argument("--estricto", action="store_true",
                   help="no escribe el manifiesto si quedan huecos bloqueantes o "
                        "de falta de datos; sale con código 2 y lista lo que falta")

    s_ = sub.add_parser("estimar", help="complejidad y tiempo de ciclo de un manifiesto")
    s_.add_argument("manifiesto", type=Path)

    sim = sub.add_parser("simular", help="manifiesto -> simulador navegable en HTML")
    sim.add_argument("manifiesto", type=Path)
    sim.add_argument("-o", "--salida", type=Path, required=True)

    apr = sub.add_parser("aprobar", help="manifiesto -> HTML estático de aprobación")
    apr.add_argument("manifiesto", type=Path)
    apr.add_argument("-o", "--salida", type=Path, required=True)

    pl = sub.add_parser("planear", help="mide y proyecta el ciclo de Simplificacion")
    pl.add_argument("accion", choices=["iniciar", "hito", "cerrar", "estado", "capacidad",
                                       "proyectar", "sembrar"])
    pl.add_argument("nombre", nargs="?", default="")
    pl.add_argument("--analista", default="")
    pl.add_argument("--entregable", default="")
    pl.add_argument("--cantidad", type=int, default=1)
    pl.add_argument("--analistas", type=int, default=1)
    pl.add_argument("--wiki", type=Path)
    pl.add_argument("--registro", type=Path,
                    default=Path.home() / ".gpmc" / "tiempos.yaml")

    srv = sub.add_parser("servir", help="levanta el asistente web")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--puerto", type=int, default=8000)
    srv.add_argument(
        "--almacen",
        type=Path,
        default=None,
        help=(
            "carpeta donde guardar las sesiones; sin esto se usa un directorio "
            "temporal que el sistema borra al apagar"
        ),
    )

    diag = sub.add_parser("diagnostico", help="herramientas de diagnóstico")
    diag.add_argument("--sintaxis", action="store_true", help="genera archivos de prueba empírica de sintaxis")
    diag.add_argument("-o", "--salida", type=Path, default=Path("diagnostico-sintaxis"), help="carpeta de salida")

    med = sub.add_parser("medir-ia", help="mide el generador de IA sobre una carpeta de expedientes")
    med.add_argument("carpeta", type=Path, help="carpeta con un subdirectorio por expediente")
    med.add_argument("--almacen", type=Path, default=None, help="donde escribir la bitacora (default: temporal)")
    med.add_argument("--exportar", type=Path, default=None, help="copiar la bitacora-ia.jsonl a esta ruta")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if not args.orden:
        parser.print_help()
        return 2

    if args.orden == "compilar":
        if args.desde_expediente is not None:
            # La puerta del linter, tambien fuera del navegador: re-extrae del
            # expediente y no compila si quedan huecos sin resolver.
            try:
                r = extraer_expediente(args.desde_expediente)
            except SinPermiso as exc:
                print(f"\n{exc}\n", file=sys.stderr)
                return 2
            if r.manifiesto is None:
                print("No se pudo producir un manifiesto del expediente.\n", file=sys.stderr)
                for h in r.huecos:
                    print(f"  - {h}", file=sys.stderr)
                return 2
            faltan = bloquean(r.huecos)
            if faltan:
                print(f"No se genero el archivo: {len(faltan)} hueco(s) del "
                      f"expediente sin resolver.\n", file=sys.stderr)
                _imprimir_huecos(r.huecos, completo=True)
                return 2
            manifiesto = r.manifiesto
        elif args.manifiesto is not None:
            try:
                manifiesto = cargar(args.manifiesto)
            except (ValidationError, ValueError) as e:
                print(f"Error al leer el manifiesto:\n{e}", file=sys.stderr)
                return 2
        else:
            print("Falta el manifiesto (o --desde-expediente).", file=sys.stderr)
            return 2
        gpm = compilar(manifiesto, proceso_id=args.proceso_id, modo_pruebas=args.modo_pruebas)
        hallazgos = revisar(gpm)
        if any(h.gravedad == "bloqueante" for h in hallazgos):
            print("No se genero el archivo: hay hallazgos bloqueantes.\n")
            return _imprimir(hallazgos)
        escribir(gpm, args.salida)
        print(f"Generado: {args.salida}")
        return _imprimir(hallazgos)

    if args.orden == "validar":
        return _imprimir(revisar_archivo(args.archivo))

    if args.orden == "extraer":
        try:
            r = extraer_expediente(args.expediente)
        except SinPermiso as exc:
            print(f"\n{exc}\n", file=sys.stderr)
            return 2
        if r.manifiesto is None:
            print("No se pudo producir un manifiesto.\n", file=sys.stderr)
            for h in r.huecos:
                print(f"  - {h}", file=sys.stderr)
            return 2
        # P-03: sin AS-IS el nombre cae al de la carpeta y se filtra al archivo y al
        # proceso_id. --nombre lo suple, como la portada del asistente web.
        if args.nombre and args.nombre.strip():
            r.manifiesto.tramite.nombre = args.nombre.strip()
        if args.estricto:
            faltan = bloquean(r.huecos)
            if faltan:
                print(f"No se escribio el manifiesto: {len(faltan)} hueco(s) "
                      f"sin resolver.\n", file=sys.stderr)
                _imprimir_huecos(r.huecos, completo=True)
                return 2
        guardar(r.manifiesto, args.salida)
        print(f"Generado: {args.salida}")
        print(f"  {len(r.manifiesto.pantallas)} pantallas, "
              f"{sum(len(p.campos) for p in r.manifiesto.pantallas)} campos, "
              f"{len(r.manifiesto.actores)} actores, "
              f"{len(r.manifiesto.flujo.tareas)} tareas")
        if r.huecos:
            _imprimir_huecos(r.huecos, args.huecos)
        return 0

    if args.orden == "planear":
        reg = Registro(args.registro)
        a = args.accion

        if a == "iniciar":
            if not args.nombre:
                print("Falta el nombre del tramite.", file=sys.stderr)
                return 2
            e = reg.iniciar(args.nombre, analista=args.analista)
            print(f"Reloj iniciado: {e.nombre}")
            print(f"  analista: {e.analista or '(sin asignar)'} | inicio: {e.inicio}")
            return 0

        if a == "hito":
            try:
                reg.hito(args.nombre, args.entregable)
            except (KeyError, ValueError) as exc:
                print(str(exc), file=sys.stderr)
                return 2
            print(f"Hito registrado: {args.nombre} -> {args.entregable}")
            return 0

        if a == "cerrar":
            try:
                reg.cerrar(args.nombre)
            except KeyError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            e = reg.buscar(args.nombre)
            print(f"Cerrado: {e.nombre} — {e.dias} dias naturales")
            return 0

        if a == "sembrar":
            if not args.wiki:
                print("Falta --wiki con la ruta a wiki/expedientes.", file=sys.stderr)
                return 2
            n = sembrar_desde_wiki(reg, args.wiki)
            print(f"Sembrados {n} expedientes desde el wiki (origen: frontmatter).")
            return 0

        if a == "estado":
            s_ = estado(reg)
            print(f"Abiertos ({len(s_.abiertos)}):")
            for e in s_.abiertos:
                faltan = [x for x in ("as-is", "to-be", "bpmn", "diccionario",
                                      "wireframes", "control-acciones") if x not in e.hitos]
                print(f"  {e.dias:>3}d  {e.nombre[:44]:<46} {e.analista[:10]:<12}"
                      f"faltan: {len(faltan)}/6")
            print(f"\nCerrados ({len(s_.cerrados)}):")
            for e in s_.cerrados[-10:]:
                marca = "" if e.origen == "vivo" else "  [wiki]"
                print(f"  {e.dias:>3}d  {e.nombre[:44]:<46} {e.analista[:10]}{marca}")
            return 0

        if a == "capacidad":
            print("  La mediana usa SOLO expedientes completos (5 de 6 entregables).\n")
            for nombre, c in capacidad(reg).items():
                med = (f"{c.mediana_dias}d" if c.mediana_dias is not None
                       else "sin completos")
                print(f"  {nombre:<16} abiertos={c.abiertos:<4} cerrados={c.cerrados:<4} "
                      f"completos={c.completos:<4} mediana={med}")
            return 0

        if a == "proyectar":
            p = proyectar(reg, cantidad=args.cantidad, analistas=args.analistas)
            print(f"Proyeccion para {p.cantidad} tramite(s) con {p.analistas} analista(s)\n")
            if p.mediana_dias is None:
                print("  No hay base para proyectar.")
            else:
                print(f"  Mediana por expediente:  {p.mediana_dias} dias naturales "
                      f"(muestra: {p.muestra}, medidos en vivo: {p.muestra_viva})")
                print(f"  Simplificacion:          ~{p.dias_totales} dias naturales")
                print(f"  DGT por tramite:         {p.dias_dgt[0]}-{p.dias_dgt[1]} dias habiles")
                print(f"\n  {p.nota_dgt}")
            print("\nAdvertencias:")
            for adv in p.advertencias:
                print(f"  - {adv}")
            return 0

        return 2

    if args.orden == "servir":
        cargar_entorno()
        try:
            import uvicorn
        except ImportError:
            print("Falta el extra web. Instalar con: pip install -e '.[web]'", file=sys.stderr)
            return 2
        from gpmc.web import app as web_app

        print(f"Asistente en http://{args.host}:{args.puerto}  (Ctrl+C para detener)")
        if args.almacen is not None:
            args.almacen.mkdir(parents=True, exist_ok=True)
            print(f"Sesiones en {args.almacen}")
        else:
            print("AVISO: sesiones en un directorio temporal; se pierden al "
                  "cerrar. Usa --almacen para conservarlas.")
        # `crear_app` se resuelve por modulo, no por el nombre importado
        # arriba, para que una prueba pueda sustituirlo.
        uvicorn.run(
            web_app.crear_app(almacen=args.almacen),
            host=args.host,
            port=args.puerto,
            log_level="warning",
        )
        return 0

    if args.orden == "simular":
        try:
            m = cargar(args.manifiesto)
        except (ValidationError, ValueError) as exc:
            print(f"Error al leer el manifiesto:\n{exc}", file=sys.stderr)
            return 2
        Path(args.salida).write_text(generar_simulador(m), encoding="utf-8")
        print(f"Generado: {args.salida}")
        problemas = analizar(m).problemas
        if problemas:
            print(f"\n{len(problemas)} problema(s) de flujo detectado(s):\n")
            for p_ in problemas:
                print(f"  - {p_}")
            return 1
        print("Analisis de flujo: sin problemas.")
        return 0

    if args.orden == "aprobar":
        try:
            m = cargar(args.manifiesto)
        except (ValidationError, ValueError) as exc:
            print(f"Error al leer el manifiesto:\n{exc}", file=sys.stderr)
            return 2
        Path(args.salida).write_text(generar_aprobacion(m), encoding="utf-8")
        print(f"Generado documento de aprobación: {args.salida}")
        return 0

    if args.orden == "estimar":
        try:
            m = cargar(args.manifiesto)
        except (ValidationError, ValueError) as exc:
            print(f"Error al leer el manifiesto:\n{exc}", file=sys.stderr)
            return 2
        est = estimar(m)
        k = est.metricas
        print(f"Tramite: {m.tramite.nombre}\n")
        print("Metricas (conteos exactos):")
        print(f"  tareas={k.tareas}  bifurcaciones={k.bifurcaciones}  vistas={k.vistas}")
        print(f"  campos={k.campos}  acciones={k.acciones}  integraciones={k.integraciones}")
        print(f"\nNivel sugerido: {est.nivel}  ->  {est.dias}")
        for m_ in est.motivos:
            print(f"  - {m_}")
        print(f"\n{est.advertencia}")
        return 0

    if args.orden == "medir-ia":
        cargar_entorno()
        raiz = args.almacen or Path(tempfile.mkdtemp(prefix="gpmc-medir-"))
        raiz.mkdir(parents=True, exist_ok=True)
        prov = _proveedor_para_medir()
        tot = [0, 0, 0, 0]
        errores = 0
        print(f"{'expediente':40} {'DIC-08':>7} {'acept.':>7} {'rechaz.':>8} {'declino':>8}")
        for d in sorted(p for p in args.carpeta.iterdir() if p.is_dir()):
            if not any(d.glob("*iccionario*")):
                continue
            r = extraer_expediente(d)
            if r.manifiesto is None:
                continue
            n = sum(1 for h in r.huecos if h.codigo == "DIC-08")
            try:
                props = proponer_lote(r.manifiesto, r.huecos, prov, raiz, "medir" + "0" * 11)
            except (ErrorDeRed, RespuestaInvalida) as exc:
                # Una linea clara, no un traceback: la bitacora ya tiene el detalle.
                print(f"{d.name[:40]:40} {n:>7}   error del proveedor: {str(exc)[:80]}")
                errores += 1
                continue
            a = sum(1 for p in props if p.veredicto == "aceptable")
            dec = sum(1 for p in props if p.veredicto == "modelo_declino")
            rech = len(props) - a - dec
            for i, v in enumerate((n, a, rech, dec)):
                tot[i] += v
            print(f"{d.name[:40]:40} {n:>7} {a:>7} {rech:>8} {dec:>8}")
        print(f"{'TOTAL':40} {tot[0]:>7} {tot[1]:>7} {tot[2]:>8} {tot[3]:>8}")
        if args.exportar and (raiz / RUTA_BITACORA).exists():
            shutil.copy(raiz / RUTA_BITACORA, args.exportar)
            print(f"Bitácora exportada a {args.exportar}")
        if errores:
            print(f"{errores} expediente(s) con error del proveedor; detalle en {raiz / RUTA_BITACORA}")
            return 1
        return 0

    if args.orden == "diagnostico":
        if args.sintaxis:
            from gpmc.nucleo.manifiesto import Manifiesto
            import gpmc.nucleo.reglas as nreglas
            
            base = {
                "tramite": {"nombre": "Prueba Empírica Sintaxis", "dependencia": "DGT"},
                "actores": [{"id": "c", "nombre": "Ciudadano"}],
                "pantallas": [{"id": "p1", "nombre": "Pregunta", "actor": "c", "campos": [
                    {"nombre": "opcion", "etiqueta": "¿Qué rama tomar?", "tipo": "radio", "catalogo": [
                        {"etiqueta": "Rama 1", "valor": "r1"},
                        {"etiqueta": "Rama 2", "valor": "r2"}
                    ]}
                ]}],
                "flujo": {
                    "tareas": [
                        {"id": "t1", "nombre": "Elegir", "actor": "c", "inicial": True, "pantallas": ["p1"]},
                        {"id": "t2", "nombre": "Llegaste a Rama 1", "actor": "c", "terminal": True},
                        {"id": "t3", "nombre": "Llegaste a Rama 2", "actor": "c", "terminal": True}
                    ],
                    "conexiones": [
                        {"de": "t1", "a": "t2", "cuando": {"campo": "opcion", "igual": "r1"}},
                        {"de": "t1", "a": "t3", "cuando": {"campo": "opcion", "igual": "r2"}}
                    ]
                }
            }
            m = Manifiesto.model_validate(base)
            args.salida.mkdir(parents=True, exist_ok=True)
            
            nreglas.SINTAXIS_ESTRICTA = False
            gpm_laxo = compilar(m)
            escribir(gpm_laxo, args.salida / "1_modo_relajado.gpm")
            
            nreglas.SINTAXIS_ESTRICTA = True
            gpm_estricto = compilar(m)
            escribir(gpm_estricto, args.salida / "2_modo_estricto.gpm")
            
            # Restaurar por si acaso
            nreglas.SINTAXIS_ESTRICTA = False
            
            print(f"Archivos de prueba generados en {args.salida}/")
            print("Importa ambos en la plataforma y verifica cuál evalúa correctamente el radio button.")
            return 0
        print("Especifique un diagnóstico, ej. --sintaxis")
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
