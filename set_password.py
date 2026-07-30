#!/usr/bin/env python3
"""
Utility to set the login password for Ham Radio Logbook.

Usage:
    python set_password.py

Outputs the AUTH_PASSWORD_HASH line to add to your .env file.
"""
import getpass
from auth import make_hash

def main():
    print("=== Ham Radio Logbook — imposta password ===\n")
    while True:
        pwd = getpass.getpass("Nuova password: ")
        if len(pwd) < 8:
            print("✗ La password deve essere di almeno 8 caratteri.\n")
            continue
        confirm = getpass.getpass("Conferma password: ")
        if pwd != confirm:
            print("✗ Le password non coincidono.\n")
            continue
        break

    h = make_hash(pwd)
    print(f"\n✓ Aggiungi questa riga al file .env:\n")
    print(f"AUTH_PASSWORD_HASH={h}\n")

if __name__ == "__main__":
    main()
