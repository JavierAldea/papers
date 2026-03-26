#!/usr/bin/env python3
"""
Genera un código de acceso SHA-256 para un nuevo usuario de TechVigilance.
Uso: python3 add_user.py <NombreUsuario> <contraseña>
Ejemplo: python3 add_user.py "Marta García" mi_password_2026

El hash generado debe añadirse al objeto USERS dentro de index.html.
"""

import sys
import hashlib


def usage_and_exit(msg: str = "") -> None:
    if msg:
        print(f"\n  ERROR: {msg}\n", file=sys.stderr)
    print(
        "  Uso:     python3 add_user.py <NombreUsuario> <contraseña>\n"
        "  Ejemplo: python3 add_user.py \"Marta García\" mi_password_2026\n",
        file=sys.stderr,
    )
    sys.exit(1)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    if len(sys.argv) < 3:
        usage_and_exit("Se requieren exactamente 2 argumentos: nombre y contraseña.")

    if len(sys.argv) > 3:
        usage_and_exit(
            "Demasiados argumentos. Si el nombre contiene espacios, "
            "enciérralo entre comillas: \"Nombre Apellido\"."
        )

    name: str = sys.argv[1].strip()
    password: str = sys.argv[2]

    if not name:
        usage_and_exit("El nombre de usuario no puede estar vacío.")

    if not password:
        usage_and_exit("La contraseña no puede estar vacía.")

    if len(password) < 8:
        print(
            "\n  AVISO: La contraseña tiene menos de 8 caracteres. "
            "Se recomienda usar contraseñas más largas.\n",
            file=sys.stderr,
        )

    hash_hex = sha256_hex(password)

    line = f'  "{hash_hex}": "{name}",'

    print()
    print("=" * 68)
    print("  TechVigilance v2 — Nuevo usuario")
    print("=" * 68)
    print()
    print(f"  Nombre de usuario : {name}")
    print(f"  SHA-256 del pass  : {hash_hex}")
    print()
    print("─" * 68)
    print("  LÍNEA A AÑADIR en index.html (dentro del objeto USERS):")
    print()
    print(line)
    print()
    print("─" * 68)
    print("  INSTRUCCIONES:")
    print()
    print("  1. Abre /Users/nomada/papers-page/index.html en tu editor.")
    print("  2. Busca el objeto USERS en el bloque <script>:")
    print()
    print("       const USERS = {")
    print('         "d1325278ceeeb1fe96b7c3b64e6c495c16074b8864c7b82af202573bfb4ff98f": "Javier",')
    print("         // ← añade la línea aquí")
    print("       };")
    print()
    print("  3. Pega la línea generada arriba dentro del objeto USERS.")
    print("  4. Guarda el archivo y despliega a GitHub Pages.")
    print()
    print("  IMPORTANTE: No compartas ni subas contraseñas en texto plano.")
    print("  Solo el hash SHA-256 se almacena en el código fuente.")
    print("=" * 68)
    print()


if __name__ == "__main__":
    main()
