# main.py

from fastapi import FastAPI
from core.database import connect_to_mongo, close_mongo_connection, get_mongo_client
from api.endpoints import websocket
from services.scraping_service import GoldScrapingService
from services.repositories.price_repo import PriceRepository
import asyncio
from contextlib import asynccontextmanager 
from concurrent.futures import ThreadPoolExecutor 
from starlette.middleware.cors import CORSMiddleware
from services.repositories.user_repo import UserRepository
from api.endpoints import users
from api.endpoints.admin import router as admin_router 
from api.endpoints import auth, admin 
executor: ThreadPoolExecutor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- APPLICATION STARTUP ---")
    
    await connect_to_mongo()
    mongo_client = get_mongo_client() 
    
    global executor
    loop = asyncio.get_event_loop() 
    executor = ThreadPoolExecutor(max_workers=5)
    loop.set_default_executor(executor)

    app.state.user_repo = UserRepository(mongo_client) 
    

    # global user_repo 
    # user_repo = UserRepository(mongo_client) 

  

    # Start the synchronous scraping task, passing the loop object
    loop.run_in_executor(
        None,
        scraper.run_scraper_loop, 
        mongo_client,
        loop
    )
    
    yield 
    
    print("--- APPLICATION SHUTDOWN ---")
    
    if scraper.driver:
        scraper.driver.quit()
        print("WebDriver closed.")

    if executor:
        executor.shutdown(wait=False)
        print("Thread pool shut down.")

    await close_mongo_connection()


app = FastAPI(
    title="RealTime Price Scraper API", 
    version="1.0.0",
    lifespan=lifespan 
)

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------------------------------------------------------

price_repo = PriceRepository()
scraper = GoldScrapingService(repo=price_repo)


# --- API Routes ---
app.include_router(websocket.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(admin_router)

@app.get("/")
def read_root():
    return {"status": "running", "message": "WebSocket server is active."}