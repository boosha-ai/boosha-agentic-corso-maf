"""EP 1 - Il tuo primo agente con MAF, come script da terminale.

Stesso agente del notebook, ma come programma standalone.
Lancialo da terminale:  uv run python agente.py

Cosa fa in più del notebook:
- fa rispondere DUE agenti opposti (Fan e Critico) sulla stessa motion;
- salva sempre ogni risposta in un file output_<nome>.md;
- se hai configurato Pushover nel .env, manda ogni risposta come notifica push.

Su Pushover: oggi e' il NOSTRO codice a mandare la notifica (un side-effect).
Dagli episodi con i tool sara' l'agente a decidere quando chiamarla.
"""

import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from agent_framework import Agent
# OpenAIChatClient e' un export lazy (PEP 562): a runtime c'e', ma Pylint non lo vede.
from agent_framework.openai import OpenAIChatClient  # pylint: disable=no-name-in-module

load_dotenv()  # MAF non carica .env da solo


def salva_su_file(nome: str, domanda: str, testo: str) -> None:
    """Salva la risposta dell'agente in output_<nome>.md (un file per agente)."""
    percorso = Path(f"output_{nome.lower()}.md")
    percorso.write_text(
        f"# {nome}\n\n**Motion:** {domanda}\n\n{testo}\n",
        encoding="utf-8",
    )
    print(f"(output salvato in {percorso})")


def notifica(messaggio: str, titolo: str = "Fan") -> None:
    """Manda una notifica push via Pushover, se le chiavi sono nel .env.

    E' un side-effect del nostro codice: da EP 2 diventera' un tool che
    l'agente decide di chiamare da solo.
    """
    token = os.environ.get("PUSHOVER_TOKEN")
    user = os.environ.get("PUSHOVER_USER")
    if not (token and user):
        print("(Pushover non configurato: salto la notifica)")
        return
    resp = httpx.post(
        "https://api.pushover.net/1/messages.json",
        data={"token": token, "user": user, "message": messaggio[:1024], "title": titolo},
    )
    ok = resp.json().get("status") == 1
    print("(notifica inviata)" if ok else f"(Pushover errore: {resp.text})")


client = OpenAIChatClient(model="gpt-4o-mini")  # stesso client per entrambi gli agenti
fan = Agent(
    client=client,
    name="Fan",
    instructions=(
        "Sei un fan accanito di M. Night Shyamalan. Difendi anche i suoi film più criticati, "
        "trovando sempre il lato geniale. In italiano, appassionato ma concreto."
    ),
)
critico = Agent(
    client=client,
    name="Critico",
    instructions=(
        "Sei un critico severo di M. Night Shyamalan. Argomenta perché i suoi film più discussi "
        "non funzionano, con esempi precisi. In italiano, tagliente ma onesto."
    ),
)


async def main() -> None:
    """Fa rispondere i due agenti opposti, poi fa uscire ogni output: file + (se configurata) push."""
    motion = "The Happening è il peggior film di Shyamalan."
    for agente in (fan, critico):
        risposta = await agente.run(motion)
        print(f"== {agente.name} ==\n{risposta.text}\n")

        salva_su_file(agente.name, motion, risposta.text)   # sempre
        notifica(risposta.text, titolo=agente.name)         # se Pushover e' configurato


if __name__ == "__main__":
    asyncio.run(main())  # in uno script l'event loop lo avvii tu
