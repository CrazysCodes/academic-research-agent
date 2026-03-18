from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def analyze():
    return {"message": "TODO"}
