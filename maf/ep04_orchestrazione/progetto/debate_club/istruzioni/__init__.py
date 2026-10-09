"""Le istruzioni degli agenti stanno in file .md, non dentro il codice Python.

Non e' pignoleria: un prompt e' testo che cambia spesso, lo rileggi ad alta voce, lo fai
rivedere a qualcuno che non programma. Tenerlo in una tripla virgoletta in mezzo a una
classe lo rende invisibile e scomodo da diffare. Qui invece `git diff istruzioni/` ti
dice esattamente come e' cambiato il carattere di un agente.
"""

from pathlib import Path

_QUI = Path(__file__).parent


def carica(nome: str) -> str:
    """Le istruzioni dell'agente `nome`, dal file `istruzioni/<nome>.md`."""
    f = _QUI / f"{nome}.md"
    if not f.exists():
        disponibili = ", ".join(sorted(p.stem for p in _QUI.glob("*.md")))
        raise FileNotFoundError(f"nessuna istruzione per '{nome}'. Disponibili: {disponibili}")
    return f.read_text(encoding="utf-8").strip()
