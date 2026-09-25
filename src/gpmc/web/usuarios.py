"""Usuarios, contraseñas, JWT y bitácora de acciones (spec 2026-09-25).

Decisiones de la DGT y la DSA: PostgreSQL en RDS (instancia mínima) con dos
tablas, `usuarios` y `auditoria`; nada de SQLite. Las sesiones siguen en
archivos. Sin ORM: dos tablas no lo justifican, y el SQL es el mismo que se
lee en la consola de RDS.

Sin librería de JWT ni de hashing: HS256 son tres líneas de `hmac`, y
`hashlib.scrypt` viene con Python. Menos dependencias, mismas garantías.
`psycopg` se importa perezoso: solo el servidor con Postgres lo necesita; las
pruebas de la API corren con `AlmacenEnMemoria`, que cumple el mismo contrato
(el patrón de `ProveedorFalso`).
"""
import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

HORAS_TOKEN = 8
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}


# --- contraseñas -------------------------------------------------------------------

def hash_contrasena(contrasena: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, **_SCRYPT)
    return f"scrypt${sal.hex()}${h.hex()}"


def verificar_contrasena(contrasena: str, guardado: str) -> bool:
    try:
        esquema, sal, esperado = guardado.split("$")
        if esquema != "scrypt":
            return False
        h = hashlib.scrypt(contrasena.encode("utf-8"), salt=bytes.fromhex(sal), **_SCRYPT)
        return hmac.compare_digest(h.hex(), esperado)
    except (ValueError, AttributeError):
        return False


# --- JWT (HS256) ----------------------------------------------------------------------

def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _des64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _ahora(ahora: Optional[datetime]) -> datetime:
    return ahora if ahora is not None else datetime.now(timezone.utc)


def emitir_token(secreto: str, correo: str, nombre: str, dependencia: str,
                 horas: int = HORAS_TOKEN, ahora: Optional[datetime] = None) -> str:
    t0 = _ahora(ahora)
    cuerpo = {"sub": correo, "nombre": nombre, "dependencia": dependencia,
              "iat": int(t0.timestamp()), "exp": int((t0 + timedelta(hours=horas)).timestamp())}
    cabecera = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    datos = _b64(json.dumps(cuerpo, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    firma = hmac.new(secreto.encode("utf-8"), f"{cabecera}.{datos}".encode("ascii"), hashlib.sha256).digest()
    return f"{cabecera}.{datos}.{_b64(firma)}"


def leer_token(secreto: str, token: str, ahora: Optional[datetime] = None) -> Optional[dict]:
    """El cuerpo del token si la firma es correcta y no ha vencido; None si no."""
    try:
        cabecera, datos, firma = token.split(".")
        esperada = hmac.new(secreto.encode("utf-8"), f"{cabecera}.{datos}".encode("ascii"),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(_des64(firma), esperada):
            return None
        cuerpo = json.loads(_des64(datos).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(cuerpo, dict) or "sub" not in cuerpo or "exp" not in cuerpo:
        return None
    if _ahora(ahora).timestamp() > cuerpo["exp"]:
        return None
    return cuerpo


# --- almacén -----------------------------------------------------------------------------

@dataclass
class Usuario:
    correo: str
    nombre: str
    dependencia: str
    activo: bool = True


def _norm(correo: str) -> str:
    return (correo or "").strip().lower()


class AlmacenEnMemoria:
    """El contrato, en memoria: lo que ven las pruebas de la API."""

    def __init__(self):
        self._usuarios = {}      # correo -> (Usuario, hash)
        self._auditoria = []

    def crear_tablas(self) -> None:   # mismo contrato que Postgres; aqui no hay nada que crear
        pass

    def alta(self, correo: str, nombre: str, dependencia: str, contrasena: str) -> Usuario:
        c = _norm(correo)
        if c in self._usuarios:
            raise ValueError(f"ya existe un usuario con el correo {c}")
        u = Usuario(correo=c, nombre=nombre.strip(), dependencia=dependencia.strip())
        self._usuarios[c] = (u, hash_contrasena(contrasena))
        return u

    def autenticar(self, correo: str, contrasena: str) -> Optional[Usuario]:
        fila = self._usuarios.get(_norm(correo))
        if fila is None:
            # Se verifica igual para que el tiempo no diga si el correo existe.
            verificar_contrasena(contrasena, hash_contrasena("x"))
            return None
        u, h = fila
        return u if u.activo and verificar_contrasena(contrasena, h) else None

    def desactivar(self, correo: str) -> None:
        fila = self._usuarios.get(_norm(correo))
        if fila:
            fila[0].activo = False

    def usuarios(self) -> list:
        return [u for u, _ in self._usuarios.values()]

    def auditar(self, usuario: str, dependencia: str, accion: str, sid: Optional[str],
                detalle: str = "", ip: Optional[str] = None) -> None:
        # `id` correlativo: dos acciones en el mismo microsegundo se ordenan
        # como en Postgres (fecha, id), no al azar.
        self._auditoria.append({"id": len(self._auditoria) + 1, "fecha": datetime.now(timezone.utc),
                                "usuario": _norm(usuario), "dependencia": dependencia, "accion": accion,
                                "sid": sid, "detalle": detalle or "", "ip": ip})

    def auditoria(self, sid: Optional[str] = None, usuario: Optional[str] = None,
                  desde: Optional[datetime] = None, limite: int = 200) -> list:
        filas = [f for f in self._auditoria
                 if (sid is None or f["sid"] == sid)
                 and (usuario is None or f["usuario"] == _norm(usuario))
                 and (desde is None or f["fecha"] >= desde)]
        filas = sorted(filas, key=lambda f: (f["fecha"], f["id"]), reverse=True)[:limite]
        return [{k: v for k, v in {**f, "fecha": f["fecha"].isoformat()}.items() if k != "id"} for f in filas]


_DDL = """
CREATE TABLE IF NOT EXISTS usuarios (
    correo          TEXT PRIMARY KEY,
    nombre          TEXT NOT NULL,
    dependencia     TEXT NOT NULL,
    hash_contrasena TEXT NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS auditoria (
    id          BIGSERIAL PRIMARY KEY,
    fecha       TIMESTAMPTZ NOT NULL DEFAULT now(),
    usuario     TEXT NOT NULL,
    dependencia TEXT NOT NULL,
    accion      TEXT NOT NULL,
    sid         TEXT,
    detalle     TEXT NOT NULL DEFAULT '',
    ip          TEXT
);
CREATE INDEX IF NOT EXISTS auditoria_sid ON auditoria (sid);
CREATE INDEX IF NOT EXISTS auditoria_usuario ON auditoria (usuario);
CREATE INDEX IF NOT EXISTS auditoria_fecha ON auditoria (fecha DESC);
"""


class AlmacenPostgres:
    """El mismo contrato sobre PostgreSQL (RDS). Una conexión por operación:
    el asistente hace pocas escrituras y así no hay pool que cuidar ni
    conexión que se muera en la noche."""

    def __init__(self, dsn: str):
        import psycopg  # ImportError -> falta el extra [web]
        self._psycopg = psycopg
        self._dsn = dsn

    def _con(self):
        return self._psycopg.connect(self._dsn)

    def crear_tablas(self) -> None:
        with self._con() as con:
            con.execute(_DDL)

    def vaciar(self) -> None:
        """Solo para pruebas: nadie borra auditoría en producción."""
        with self._con() as con:
            con.execute("DELETE FROM auditoria; DELETE FROM usuarios;")

    def alta(self, correo: str, nombre: str, dependencia: str, contrasena: str) -> Usuario:
        c = _norm(correo)
        with self._con() as con:
            if con.execute("SELECT 1 FROM usuarios WHERE correo = %s", (c,)).fetchone():
                raise ValueError(f"ya existe un usuario con el correo {c}")
            con.execute("INSERT INTO usuarios (correo, nombre, dependencia, hash_contrasena) VALUES (%s, %s, %s, %s)",
                        (c, nombre.strip(), dependencia.strip(), hash_contrasena(contrasena)))
        return Usuario(correo=c, nombre=nombre.strip(), dependencia=dependencia.strip())

    def autenticar(self, correo: str, contrasena: str) -> Optional[Usuario]:
        with self._con() as con:
            fila = con.execute("SELECT correo, nombre, dependencia, activo, hash_contrasena FROM usuarios WHERE correo = %s",
                               (_norm(correo),)).fetchone()
        if fila is None:
            verificar_contrasena(contrasena, hash_contrasena("x"))
            return None
        correo_, nombre, dependencia, activo, h = fila
        if not activo or not verificar_contrasena(contrasena, h):
            return None
        return Usuario(correo=correo_, nombre=nombre, dependencia=dependencia, activo=activo)

    def desactivar(self, correo: str) -> None:
        with self._con() as con:
            con.execute("UPDATE usuarios SET activo = FALSE WHERE correo = %s", (_norm(correo),))

    def usuarios(self) -> list:
        with self._con() as con:
            filas = con.execute("SELECT correo, nombre, dependencia, activo FROM usuarios ORDER BY creado").fetchall()
        return [Usuario(*f) for f in filas]

    def auditar(self, usuario: str, dependencia: str, accion: str, sid: Optional[str],
                detalle: str = "", ip: Optional[str] = None) -> None:
        with self._con() as con:
            con.execute("INSERT INTO auditoria (usuario, dependencia, accion, sid, detalle, ip) VALUES (%s, %s, %s, %s, %s, %s)",
                        (_norm(usuario), dependencia, accion, sid, detalle or "", ip))

    def auditoria(self, sid: Optional[str] = None, usuario: Optional[str] = None,
                  desde: Optional[datetime] = None, limite: int = 200) -> list:
        cond, args = [], []
        if sid is not None:
            cond.append("sid = %s"); args.append(sid)
        if usuario is not None:
            cond.append("usuario = %s"); args.append(_norm(usuario))
        if desde is not None:
            cond.append("fecha >= %s"); args.append(desde)
        sql = ("SELECT fecha, usuario, dependencia, accion, sid, detalle, ip FROM auditoria"
               + (" WHERE " + " AND ".join(cond) if cond else "")
               + " ORDER BY fecha DESC, id DESC LIMIT %s")
        with self._con() as con:
            filas = con.execute(sql, (*args, limite)).fetchall()
        return [{"fecha": f[0].isoformat(), "usuario": f[1], "dependencia": f[2], "accion": f[3],
                 "sid": f[4], "detalle": f[5], "ip": f[6]} for f in filas]
