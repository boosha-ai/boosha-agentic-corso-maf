"""Il client verso il modello, in un posto solo.

Sta qui e non dentro ogni agente per un motivo pratico: quando vorrai cambiare modello,
o puntare a un altro provider, cambi una riga invece di cinque. E' anche il posto dove
carichiamo il .env, perche' MAF non lo fa da solo.
"""

import os

from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

load_dotenv()  # MAF non carica il .env da solo

MODELLO = os.environ.get("DEBATE_CLUB_MODEL", "gpt-4o-mini")


def client() -> OpenAIChatClient:
    """Il client condiviso. Se la chiave manca lo diciamo chiaramente qui, perche'
    l'errore che arriverebbe da MAF parla di 'base_url' e manda fuori strada."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "Manca OPENAI_API_KEY. Mettila nel .env alla radice del progetto e riprova. "
            "(Senza, l'errore che vedresti parlerebbe di 'base_url'/'endpoint': e' fuorviante.)"
        )
    return OpenAIChatClient(model=MODELLO)
