from typing import Protocol, List

class DeckIO(Protocol):
    def get_cached(self, ids: List[str]) -> dict[str, dict]: ...

    #def insert_cached(self):
        #TO DO
      

