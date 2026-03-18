from app.repositories.paper_store import paper_store, PaperStore


def get_paper_store() -> PaperStore:
    return paper_store
