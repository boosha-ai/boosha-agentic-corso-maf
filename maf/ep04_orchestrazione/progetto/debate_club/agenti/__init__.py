"""Il cast del Debate Club.

Un file per agente, e ogni agente e' una **factory** (`crea_...`) invece di un oggetto
gia' costruito. Cosi' importare il modulo non richiede la chiave API, e ogni run parte
da un agente pulito invece di riusare uno stato lasciato dal run precedente.

Chi c'e', in una riga a testa:
- Ricercatore  - ha i tool, produce il dossier. Nato in EP 2.
- Fan          - difende il film, solo dal dossier, nessun tool.
- Critico      - attacca il film, solo dal dossier, nessun tool.
- Moderatore   - decide chi parla. Non argomenta e non giudica.
- Giudice      - arrivera' in EP 6.
"""

from debate_club.agenti._client import MODELLO, client
from debate_club.agenti.critico import crea_critico
from debate_club.agenti.fan import crea_fan
from debate_club.agenti.moderatore import crea_moderatore
from debate_club.agenti.ricercatore import crea_ricercatore

__all__ = [
    "MODELLO",
    "client",
    "crea_critico",
    "crea_fan",
    "crea_moderatore",
    "crea_ricercatore",
]
