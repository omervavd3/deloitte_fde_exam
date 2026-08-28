from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    provider = request.app.state.provider
    return {"status": "ok", "provenance": provider.provenance()}
