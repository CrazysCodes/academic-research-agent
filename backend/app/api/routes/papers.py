from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_papers():
    return {"papers": []}


@router.post("/upload")
async def upload_paper():
    return {"message": "TODO"}


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str):
    return {"message": "TODO"}
