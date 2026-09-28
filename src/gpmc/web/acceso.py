"""Sesión con JWT y bitácora de acciones para el asistente (spec 2026-09-25).

`instalar(app, usuarios, secreto)` hace tres cosas:

1. Un middleware que exige sesión en todo lo que no sea entrar, capacidades o
   la propia SPA (el shell y sus assets deben cargar para mostrar la entrada).
   El token viaja en la cabecera `Authorization: Bearer` (la SPA) o en la
   cookie `gpmc_sesion` (las páginas del servidor —simulador, aprobación,
   descargas— se abren con un enlace, no con `fetch`).
2. Las rutas `POST /api/v1/sesion` (entrar), `GET /api/v1/sesion` (quién
   soy), `POST /api/v1/salir` y `GET /api/v1/auditoria`.
3. La auditoría: el mismo middleware, al salir la respuesta, traduce
   (método, ruta) a una acción y la registra con el usuario. Así ningún
   manejador tiene que acordarse de auditar, y añadir una ruta a la lista es
   una línea.

Sin `usuarios` ni `secreto` no se instala nada y la app se comporta como
siempre: es lo que ven las pruebas de arriba y `gpmc servir --sin-usuarios`.
"""
import logging
import re
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gpmc.web.usuarios import HORAS_TOKEN, ROLES, correo_institucional, emitir_token, leer_token

log = logging.getLogger(__name__)

COOKIE = "gpmc_sesion"
DOMINIO_POR_OMISION = "hidalgo.gob.mx"
MIN_CONTRASENA = 8

# Lo que se puede pedir sin sesión: entrar, saber si el servidor propone, y la
# SPA misma (shell + assets). Todo lo que atiende un manejador real del backend
# va protegido; el resto de GET es el shell de la SPA (catch-all).
_ABIERTAS = re.compile(r"^/api/v1/(sesion|capacidades|registro|recuperar|restablecer)$")
# Solo el superusuario (rol admin): cuentas pendientes, roles, bajas.
_SOLO_ADMIN = re.compile(r"^/api/v1/usuarios(/|$)")
_PROTEGIDAS = re.compile(
    r"^/(api/|simulador/|aprobacion/|historial$|vistas/|descargar/|descargar-plantilla|extraer$|resolver/|reconocer/)"
)

# (método, patrón) -> acción. `sid` sale del grupo con ese nombre si existe.
_ACCIONES = [
    ("POST", re.compile(r"^/api/v1/expedientes$"), "expediente.subir"),
    ("POST", re.compile(r"^/extraer$"), "expediente.subir"),
    ("POST", re.compile(r"^/api/v1/expedientes/proponer$"), "as_is.proponer"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/generados/(?P<doc>[^/]+)/decision$"), "propuesta.decidir"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/generados/(?P<doc>[^/]+)/subir$"), "propuesta.subir"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/resolver$"), "hueco.resolver"),
    ("POST", re.compile(r"^/resolver/(?P<sid>[^/]+)$"), "hueco.resolver"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/reconocer$"), "hueco.reconocer"),
    ("POST", re.compile(r"^/reconocer/(?P<sid>[^/]+)$"), "hueco.reconocer"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/propuestas/(?P<pid>[^/]+)/decision$"), "propuesta_ia.decidir"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/documentos/analizar$"), "documentos.analizar"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/documentos/aceptar-verificados$"), "documentos.decidir"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/documentos/[^/]+/decision$"), "documentos.decidir"),
    ("POST", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/comparativa/declarar$"), "comparativa.declarar"),
    ("GET", re.compile(r"^/api/v1/expedientes/(?P<sid>[^/]+)/gpm$"), "gpm.descargar"),
    ("GET", re.compile(r"^/descargar/(?P<sid>[^/]+)/gpm(-pruebas)?$"), "gpm.descargar"),
]


class Sesion:
    """Lo que el middleware deja en `request.state.usuario`."""

    def __init__(self, correo: str, nombre: str, dependencia: str, rol: str = "analista"):
        self.correo, self.nombre, self.dependencia, self.rol = correo, nombre, dependencia, rol

    def dict(self) -> dict:
        return {"correo": self.correo, "nombre": self.nombre, "dependencia": self.dependencia, "rol": self.rol}


class EntradaIn(BaseModel):
    correo: str
    contrasena: str


class RegistroIn(BaseModel):
    correo: str
    nombre: str
    dependencia: str
    contrasena: str


class RecuperarIn(BaseModel):
    correo: str


class RestablecerIn(BaseModel):
    token: str
    contrasena: str


class RolIn(BaseModel):
    rol: str


def usuario_de(request: Request) -> Optional[Sesion]:
    return getattr(request.state, "usuario", None)


def _token_de(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE)


def _ip(request: Request) -> Optional[str]:
    # Detrás de CloudFront/ALB la IP real viene en X-Forwarded-For.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _detalle(request: Request, m: "re.Match", codigo: int, cuerpo_json: Optional[dict]) -> str:
    partes = []
    g = m.groupdict()
    if "doc" in g:
        partes.append(g["doc"])
    if cuerpo_json and isinstance(cuerpo_json.get("decision"), str):
        partes.append(cuerpo_json["decision"])
    if cuerpo_json and isinstance(cuerpo_json.get("codigo"), str):
        partes.append(cuerpo_json["codigo"])
    if request.url.path.endswith("/gpm") or request.url.path.endswith("/gpm-pruebas"):
        partes.append("pruebas" if request.url.path.endswith("-pruebas")
                      or request.query_params.get("modo") == "pruebas" else "produccion")
    texto = ": ".join(partes[:1] + [", ".join(partes[1:])]) if len(partes) > 1 else "".join(partes)
    return f"{texto} ({codigo})" if codigo >= 400 else texto


def instalar(app: FastAPI, usuarios, secreto: str, correo=None,
             dominio: str = DOMINIO_POR_OMISION) -> None:
    @app.middleware("http")
    async def _sesion_y_auditoria(request: Request, call_next):
        ruta = request.url.path
        request.state.usuario = None
        token = _token_de(request)
        cuerpo = leer_token(secreto, token) if token else None
        if cuerpo:
            request.state.usuario = Sesion(cuerpo["sub"], cuerpo.get("nombre", ""), cuerpo.get("dependencia", ""),
                                           cuerpo.get("rol", "analista"))
        if _PROTEGIDAS.match(ruta) and not _ABIERTAS.match(ruta) and request.state.usuario is None:
            return JSONResponse(status_code=401, content={"error": "hace falta entrar"})
        if _SOLO_ADMIN.match(ruta) and request.state.usuario.rol != "admin":
            return JSONResponse(status_code=403, content={"error": "solo el superusuario puede administrar cuentas"})
        # El cuerpo JSON se lee aquí para el detalle de la auditoría; Starlette
        # lo vuelve a servir al manejador desde la caché de `request.body()`.
        cuerpo_json = None
        if request.method == "POST" and request.headers.get("content-type", "").startswith("application/json"):
            try:
                cuerpo_json = await request.json()
            except ValueError:
                cuerpo_json = None
        resp = await call_next(request)
        u = request.state.usuario
        if u is not None:
            for metodo, patron, accion in _ACCIONES:
                m = patron.match(ruta)
                if request.method == metodo and m:
                    sid = m.groupdict().get("sid") or getattr(request.state, "sid", None)
                    usuarios.auditar(u.correo, u.dependencia, accion, sid,
                                     _detalle(request, m, resp.status_code, cuerpo_json), _ip(request))
                    break
        return resp

    def _emitir(u) -> str:
        return emitir_token(secreto, u.correo, u.nombre, u.dependencia, rol=getattr(u, "rol", "analista"))

    @app.post("/api/v1/sesion")
    async def entrar(cuerpo: EntradaIn, request: Request):
        u = usuarios.autenticar(cuerpo.correo, cuerpo.contrasena)
        if u is None:
            usuarios.auditar(cuerpo.correo, "", "sesion.fallo", None, "", _ip(request))
            existente = usuarios.por_correo(cuerpo.correo)
            if existente is not None and existente.estado == "pendiente":
                # Solo si la contraseña es la suya: no se revela el estado a un tercero.
                return JSONResponse(status_code=401, content={
                    "error": "tu cuenta está pendiente de aprobación por el superusuario"})
            return JSONResponse(status_code=401, content={"error": "correo o contraseña incorrectos"})
        token = _emitir(u)
        usuarios.auditar(u.correo, u.dependencia, "sesion.entrar", None, "", _ip(request))
        resp = JSONResponse(content={"token": token, "usuario": _sesion_de(u).dict()})
        # `secure` lo pone el despliegue detrás de HTTPS (CloudFront); en la
        # Mac de pruebas la liga es http y la cookie no viajaría.
        resp.set_cookie(COOKIE, token, max_age=HORAS_TOKEN * 3600, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https")
        return resp

    @app.get("/api/v1/sesion")
    async def quien_soy(request: Request):
        u = usuario_de(request)
        return {"usuario": u.dict() if u else None}

    @app.post("/api/v1/salir")
    async def salir(request: Request):
        u = usuario_de(request)
        if u is not None:
            usuarios.auditar(u.correo, u.dependencia, "sesion.salir", None, "", _ip(request))
        resp = JSONResponse(content={"ok": True})
        resp.delete_cookie(COOKIE)
        return resp

    @app.post("/api/v1/registro", status_code=201)
    async def registro(cuerpo: RegistroIn, request: Request):
        c = correo_institucional(cuerpo.correo, dominio)
        if c is None:
            return JSONResponse(status_code=422, content={"error": f"solo se admiten correos @{dominio}"})
        if len(cuerpo.contrasena) < MIN_CONTRASENA:
            return JSONResponse(status_code=422, content={"error": f"la contraseña debe tener al menos {MIN_CONTRASENA} caracteres"})
        if not cuerpo.nombre.strip() or not cuerpo.dependencia.strip():
            return JSONResponse(status_code=422, content={"error": "hacen falta el nombre y la dependencia"})
        try:
            usuarios.alta(c, cuerpo.nombre, cuerpo.dependencia, cuerpo.contrasena, estado="pendiente")
            usuarios.auditar(c, cuerpo.dependencia.strip(), "usuario.registro", None, "pendiente", _ip(request))
        except ValueError:
            # Ya existe: misma respuesta, para no decir quién tiene cuenta.
            pass
        return JSONResponse(status_code=201, content={"estado": "pendiente", "correo": c})

    @app.post("/api/v1/recuperar")
    async def recuperar(cuerpo: RecuperarIn, request: Request):
        mensaje = ("Si el correo tiene cuenta, recibirá una liga para restablecer la contraseña. "
                   "Caduca en 1 hora.")
        token = usuarios.crear_recuperacion(cuerpo.correo)
        if token is None:
            return {"mensaje": mensaje}
        u = usuarios.por_correo(cuerpo.correo)
        usuarios.auditar(u.correo, u.dependencia, "recuperacion.pedir", None, "", _ip(request))
        liga = f"{str(request.base_url).rstrip('/')}/restablecer?token={token}"
        if correo is None:
            # Sin SMTP configurado no se finge el envío: se dice, y la liga
            # queda en el log para poder probar el flujo en la Mac.
            log.warning("recuperacion para %s sin correo configurado; liga: %s", u.correo, liga)
            return {"mensaje": "El envío de correos no está configurado en este servidor. "
                               "Pide a la DGT que restablezca tu contraseña."}
        correo.enviar(u.correo, "Compilador GPM: restablecer contraseña",
                      f"Hola, {u.nombre}.\n\nPara restablecer tu contraseña abre esta liga (caduca en 1 hora "
                      f"y sirve una sola vez):\n\n{liga}\n\nSi no pediste esto, ignora este correo.\n")
        return {"mensaje": mensaje}

    @app.post("/api/v1/restablecer")
    async def restablecer(cuerpo: RestablecerIn, request: Request):
        if len(cuerpo.contrasena) < MIN_CONTRASENA:
            return JSONResponse(status_code=422, content={"error": f"la contraseña debe tener al menos {MIN_CONTRASENA} caracteres"})
        c = usuarios.consumir_recuperacion(cuerpo.token)
        if c is None:
            return JSONResponse(status_code=400, content={"error": "la liga no es válida, ya se usó o caducó"})
        usuarios.cambiar_contrasena(c, cuerpo.contrasena)
        u = usuarios.por_correo(c)
        usuarios.auditar(c, u.dependencia if u else "", "recuperacion.restablecer", None, "", _ip(request))
        return {"ok": True}

    @app.get("/api/v1/usuarios")
    async def listar_usuarios():
        return {"usuarios": [_publico(u) for u in usuarios.usuarios()]}

    def _admin(request: Request, correo_objetivo: str, accion: str, cambio):
        u = usuarios.por_correo(correo_objetivo)
        if u is None:
            return JSONResponse(status_code=404, content={"error": "no existe esa cuenta"})
        cambio(u)
        yo = usuario_de(request)
        usuarios.auditar(yo.correo, yo.dependencia, accion, None, u.correo, _ip(request))
        return {"usuario": _publico(usuarios.por_correo(u.correo))}

    @app.post("/api/v1/usuarios/{correo_objetivo}/aprobar")
    async def aprobar_usuario(correo_objetivo: str, request: Request):
        return _admin(request, correo_objetivo, "usuario.aprobar", lambda u: usuarios.aprobar(u.correo))

    @app.post("/api/v1/usuarios/{correo_objetivo}/desactivar")
    async def desactivar_usuario(correo_objetivo: str, request: Request):
        if usuario_de(request).correo == correo_objetivo.strip().lower():
            return JSONResponse(status_code=409, content={"error": "no puedes desactivar tu propia cuenta"})
        return _admin(request, correo_objetivo, "usuario.desactivar", lambda u: usuarios.desactivar(u.correo))

    @app.post("/api/v1/usuarios/{correo_objetivo}/rol")
    async def rol_usuario(correo_objetivo: str, cuerpo: RolIn, request: Request):
        if cuerpo.rol not in ROLES:
            return JSONResponse(status_code=422, content={"error": f"rol desconocido; vale: {', '.join(ROLES)}"})
        return _admin(request, correo_objetivo, "usuario.rol", lambda u: usuarios.cambiar_rol(u.correo, cuerpo.rol))

    @app.get("/api/v1/auditoria")
    async def leer_auditoria(sid: Optional[str] = None, usuario: Optional[str] = None,
                             desde: Optional[str] = None, limite: int = 200):
        from datetime import datetime
        d = None
        if desde:
            try:
                d = datetime.fromisoformat(desde)
            except ValueError:
                return JSONResponse(status_code=422, content={"error": "desde debe ser una fecha ISO"})
        return {"filas": usuarios.auditoria(sid=sid, usuario=usuario, desde=d, limite=min(max(limite, 1), 1000))}



def _sesion_de(u) -> Sesion:
    return Sesion(u.correo, u.nombre, u.dependencia, getattr(u, "rol", "analista"))


def _publico(u) -> dict:
    return {"correo": u.correo, "nombre": u.nombre, "dependencia": u.dependencia,
            "rol": u.rol, "estado": u.estado}
