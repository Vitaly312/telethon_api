from fastapi import FastAPI
from routers import auth
from contextlib import asynccontextmanager
import uvicorn


@asynccontextmanager
async def lifespan(app):
    await auth.telegram_clients_repository.async_init()
    yield
    auth.telegram_clients_repository.dump()

app = FastAPI(lifespan=lifespan)
app.include_router(auth.router)

if __name__ == '__main__':
    uvicorn.run(app)