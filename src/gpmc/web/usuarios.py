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
                 horas: int = HORAS_TOKEN, ahora: Optional[datetime] = None,
                 rol: Optional[str] = None) -> str:
    t0 = _ahora(ahora)
    cuerpo = {"sub": correo, "nombre": nombre, "dependencia": dependencia,
              "iat": int(t0.timestamp()), "exp": int((t0 + timedelta(hours=horas)).timestamp())}
    if rol is not None:
        cuerpo["rol"] = rol
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

ROLES = ("admin", "analista")
ESTADOS = ("pendiente", "activo", "inactivo")
HORAS_RECUPERACION = 1


@dataclass
class Usuario:
    correo: str
    nombre: str
    dependencia: str
    rol: str = "analista"          # admin = superusuario: aprueba cuentas y cambia roles
    estado: str = "activo"         # pendiente (registro sin aprobar) | activo | inactivo

    @property
    def activo(self) -> bool:
        return self.estado == "activo"


def _norm(correo: str) -> str:
    return (correo or "").strip().lower()


def correo_institucional(correo: str, dominio: str) -> Optional[str]:
    """El correo normalizado si es del dominio institucional; None si no.
    Solo se admiten cuentas @hidalgo.gob.mx (decisión del 2026-09-25)."""
    c = _norm(correo)
    if "@" not in c or c.count("@") != 1:
        return None
    usuario, dom = c.split("@")
    if not usuario or dom != dominio.lower():
        return None
    return c


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


class AlmacenEnMemoria:
    """El contrato, en memoria: lo que ven las pruebas de la API."""

    def __init__(self):
        self._usuarios = {}      # correo -> (Usuario, hash)
        self._auditoria = []
        self._recuperaciones = {}   # hash del token -> (correo, expira, usado)

    def crear_tablas(self) -> None:   # mismo contrato que Postgres; aqui no hay nada que crear
        pass

    def vaciar(self) -> None:
        self._usuarios.clear(); self._auditoria.clear(); self._recuperaciones.clear()

    def alta(self, correo: str, nombre: str, dependencia: str, contrasena: str,
             rol: str = "analista", estado: str = "activo") -> Usuario:
        c = _norm(correo)
        if c in self._usuarios:
            raise ValueError(f"ya existe un usuario con el correo {c}")
        u = Usuario(correo=c, nombre=nombre.strip(), dependencia=dependencia.strip(), rol=rol, estado=estado)
        self._usuarios[c] = (u, hash_contrasena(contrasena))
        return u

    def por_correo(self, correo: str) -> Optional[Usuario]:
        fila = self._usuarios.get(_norm(correo))
        return fila[0] if fila else None

    def aprobar(self, correo: str) -> None:
        fila = self._usuarios.get(_norm(correo))
        if fila:
            fila[0].estado = "activo"

    def cambiar_rol(self, correo: str, rol: str) -> None:
        fila = self._usuarios.get(_norm(correo))
        if fila:
            fila[0].rol = rol

    def cambiar_contrasena(self, correo: str, contrasena: str) -> None:
        c = _norm(correo)
        if c in self._usuarios:
            self._usuarios[c] = (self._usuarios[c][0], hash_contrasena(contrasena))

    def crear_recuperacion(self, correo: str, ahora: Optional[datetime] = None) -> Optional[str]:
        c = _norm(correo)
        if c not in self._usuarios:
            return None
        token = secrets.token_urlsafe(32)
        self._recuperaciones[_hash_token(token)] = [c, _ahora(ahora) + timedelta(hours=HORAS_RECUPERACION), False]
        return token

    def consumir_recuperacion(self, token: str, ahora: Optional[datetime] = None) -> Optional[str]:
        fila = self._recuperaciones.get(_hash_token(token or ""))
        if not fila or fila[2] or _ahora(ahora) > fila[1]:
            return None
        fila[2] = True
        return fila[0]

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
            fila[0].estado = "inactivo"

    def usuarios(self, estado: Optional[str] = None) -> list:
        return [u for u, _ in self._usuarios.values() if estado is None or u.estado == estado]

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
    rol             TEXT NOT NULL DEFAULT 'analista',
    estado          TEXT NOT NULL DEFAULT 'activo',
    creado          TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rol TEXT NOT NULL DEFAULT 'analista';
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'activo';
CREATE TABLE IF NOT EXISTS recuperaciones (
    token_hash  TEXT PRIMARY KEY,
    correo      TEXT NOT NULL,
    expira      TIMESTAMPTZ NOT NULL,
    usado       BOOLEAN NOT NULL DEFAULT FALSE
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
            con.execute("DELETE FROM auditoria; DELETE FROM recuperaciones; DELETE FROM usuarios;")

    _COLS = "correo, nombre, dependencia, rol, estado"

    def alta(self, correo: str, nombre: str, dependencia: str, contrasena: str,
             rol: str = "analista", estado: str = "activo") -> Usuario:
        c = _norm(correo)
        with self._con() as con:
            if con.execute("SELECT 1 FROM usuarios WHERE correo = %s", (c,)).fetchone():
                raise ValueError(f"ya existe un usuario con el correo {c}")
            con.execute("INSERT INTO usuarios (correo, nombre, dependencia, hash_contrasena, rol, estado) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (c, nombre.strip(), dependencia.strip(), hash_contrasena(contrasena), rol, estado))
        return Usuario(correo=c, nombre=nombre.strip(), dependencia=dependencia.strip(), rol=rol, estado=estado)

    def por_correo(self, correo: str) -> Optional[Usuario]:
        with self._con() as con:
            f = con.execute(f"SELECT {self._COLS} FROM usuarios WHERE correo = %s", (_norm(correo),)).fetchone()
        return Usuario(*f) if f else None

    def autenticar(self, correo: str, contrasena: str) -> Optional[Usuario]:
        with self._con() as con:
            fila = con.execute(f"SELECT {self._COLS}, hash_contrasena FROM usuarios WHERE correo = %s",
                               (_norm(correo),)).fetchone()
        if fila is None:
            verificar_contrasena(contrasena, hash_contrasena("x"))
            return None
        u = Usuario(*fila[:5])
        if not u.activo or not verificar_contrasena(contrasena, fila[5]):
            return None
        return u

    def _set(self, correo: str, columna: str, valor) -> None:
        with self._con() as con:
            con.execute(f"UPDATE usuarios SET {columna} = %s WHERE correo = %s", (valor, _norm(correo)))

    def aprobar(self, correo: str) -> None:
        self._set(correo, "estado", "activo")

    def desactivar(self, correo: str) -> None:
        self._set(correo, "estado", "inactivo")

    def cambiar_rol(self, correo: str, rol: str) -> None:
        self._set(correo, "rol", rol)

    def cambiar_contrasena(self, correo: str, contrasena: str) -> None:
        self._set(correo, "hash_contrasena", hash_contrasena(contrasena))

    def usuarios(self, estado: Optional[str] = None) -> list:
        sql = f"SELECT {self._COLS} FROM usuarios" + (" WHERE estado = %s" if estado else "") + " ORDER BY creado"
        with self._con() as con:
            filas = con.execute(sql, (estado,) if estado else ()).fetchall()
        return [Usuario(*f) for f in filas]

    def crear_recuperacion(self, correo: str, ahora: Optional[datetime] = None) -> Optional[str]:
        if self.por_correo(correo) is None:
            return None
        token = secrets.token_urlsafe(32)
        with self._con() as con:
            con.execute("INSERT INTO recuperaciones (token_hash, correo, expira) VALUES (%s, %s, %s)",
                        (_hash_token(token), _norm(correo), _ahora(ahora) + timedelta(hours=HORAS_RECUPERACION)))
        return token

    def consumir_recuperacion(self, token: str, ahora: Optional[datetime] = None) -> Optional[str]:
        with self._con() as con:
            f = con.execute("SELECT correo, expira, usado FROM recuperaciones WHERE token_hash = %s",
                            (_hash_token(token or ""),)).fetchone()
            if not f or f[2] or _ahora(ahora) > f[1]:
                return None
            con.execute("UPDATE recuperaciones SET usado = TRUE WHERE token_hash = %s", (_hash_token(token),))
        return f[0]

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
