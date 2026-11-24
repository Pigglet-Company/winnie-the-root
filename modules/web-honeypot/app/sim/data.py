"""Datos 100 % FICTICIOS para los simuladores. Nada de aquí es real.

Empresa inventada: "Nexora Industries" (dominio .local, no enrutable).
Los hashes son MD5 de contraseñas triviales y archiconocidas (admin, 123456, password...).
"""
from __future__ import annotations

MYSQL_VERSION = "8.0.32-0ubuntu0.20.04.2"
DB_NAME = "intranet"
DB_USER = "intranet_app@localhost"
HOSTNAME = "web01"

# Consulta simulada: SELECT id, name, department FROM employees WHERE name LIKE '%{q}%'
EMP_COLUMNS = ("id", "name", "department")
EMPLOYEES: list[tuple[int, str, str]] = [
    (1, "Laura Gómez", "Recursos Humanos"),
    (2, "Carlos Ruiz", "Sistemas"),
    (3, "Marta Soler", "Finanzas"),
    (4, "Javier Prieto", "Sistemas"),
    (5, "Elena Vidal", "Comercial"),
    (6, "Pablo Navarro", "Logística"),
    (7, "Sofía Herrera", "Marketing"),
    (8, "David Molina", "Calidad"),
]

USER_COLUMNS = ("id", "username", "email", "role", "password_hash")
USERS: list[tuple[int, str, str, str, str]] = [
    (1, "admin", "admin@intranet.nexora.local", "administrator", "21232f297a57a5a743894a0e4a801fc3"),
    (2, "cruiz", "cruiz@intranet.nexora.local", "sysadmin", "e10adc3949ba59abbe56e057f20f883e"),
    (3, "lgomez", "lgomez@intranet.nexora.local", "hr", "5f4dcc3b5aa765d61d8327deb882cf99"),
    (4, "msoler", "msoler@intranet.nexora.local", "finance", "25f9e794323b453885f5181f1b624d0b"),
    (5, "backup", "backup@intranet.nexora.local", "service", "96e79218965eb72c92a549dd5a330112"),
]

TABLES = ("audit_log", "departments", "employees", "sessions", "users")
