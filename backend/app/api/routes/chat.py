from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def chat_stream():
    return {"message": "TODO"}
