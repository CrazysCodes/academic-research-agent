"""
In-memory paper metadata store (Phase 1).
Replace with PostgreSQL in Phase 4.
"""
import threading
from app.models.paper import Paper


class PaperStore:
    def __init__(self) -> None:
        self._store: dict[str, Paper] = {}
        self._lock = threading.Lock()

    def add(self, paper: Paper) -> Paper:
        with self._lock:
            self._store[paper.id] = paper
        return paper

    def get(self, paper_id: str) -> Paper | None:
        return self._store.get(paper_id)

    def list(self) -> list[Paper]:
        return list(self._store.values())

    def update(self, paper: Paper) -> Paper:
        with self._lock:
            self._store[paper.id] = paper
        return paper

    def delete(self, paper_id: str) -> bool:
        with self._lock:
            return self._store.pop(paper_id, None) is not None


paper_store = PaperStore()
