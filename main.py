# # main.py

# from fastapi import FastAPI
# from core.database import connect_to_mongo, close_mongo_connection, get_mongo_client
# from api.endpoints import websocket
# # from services.scraping_service import GoldScrapingService
# from services.playwright_scraper_service import PlaywrightGoldScrapingService as GoldScrapingService

# from services.repositories.price_repo import PriceRepository
# import asyncio
# from contextlib import asynccontextmanager 
# from concurrent.futures import ThreadPoolExecutor 
# from starlette.middleware.cors import CORSMiddleware
# from services.repositories.user_repo import UserRepository
# from api.endpoints import users
# from api.endpoints.admin import router as admin_router 
# from api.endpoints import auth, admin 
# executor: ThreadPoolExecutor = None

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("--- APPLICATION STARTUP ---")
    
#     await connect_to_mongo()
#     mongo_client = get_mongo_client() 
    
#     global executor
#     loop = asyncio.get_event_loop() 
#     executor = ThreadPoolExecutor(max_workers=5)
#     loop.set_default_executor(executor)

#     app.state.user_repo = UserRepository(mongo_client) 
    

#     # global user_repo 
#     # user_repo = UserRepository(mongo_client) 

  

#     # Start the synchronous scraping task, passing the loop object
#     loop.run_in_executor(
#         None,
#         scraper.run_scraper_loop, 
#         mongo_client,
#         loop
#     )
    
#     yield 
    
#     print("--- APPLICATION SHUTDOWN ---")
    
#     if scraper.driver:
#         scraper.driver.quit()
#         print("WebDriver closed.")

#     if executor:
#         executor.shutdown(wait=False)
#         print("Thread pool shut down.")

#     await close_mongo_connection()


# app = FastAPI(
#     title="RealTime Price Scraper API", 
#     version="1.0.0",
#     lifespan=lifespan 
# )

# origins = [
#     "http://localhost:3000",
#     "http://localhost:3001",
#     "http://127.0.0.1:3000",
#     "http://localhost:8000",
#     "http://127.0.0.1:8000",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # -----------------------------------------------------------------------------

# price_repo = PriceRepository()
# scraper = GoldScrapingService(repo=price_repo)


# # --- API Routes ---
# app.include_router(websocket.router)
# app.include_router(auth.router)
# app.include_router(admin.router)
# app.include_router(users.router)
# app.include_router(admin_router)

# @app.get("/")
# def read_root():
#     return {"status": "running", "message": "WebSocket server is active."}






# without thread 


# main.py

from fastapi import FastAPI
from core.database import connect_to_mongo, close_mongo_connection, get_mongo_client
from api.endpoints import websocket, users, auth, admin
from services.playwright_scraper_service import PlaywrightGoldScrapingService as GoldScrapingService
from services.repositories.price_repo import PriceRepository
from services.repositories.user_repo import UserRepository
from starlette.middleware.cors import CORSMiddleware
from config.settings import settings
from datetime import datetime
import asyncio
from services.websocket_manager import manager

app = FastAPI(title="RealTime Price Scraper API", version="1.0.0")

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://live-price-tracker.netlify.app",

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# WebSocket Manager
from fastapi import WebSocket
from typing import List, Dict, Any

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_broadcasted_data: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        if self.last_broadcasted_data:
            await websocket.send_json(self.last_broadcasted_data)

    async def broadcast(self, data: Dict[str, Any]):
        self.last_broadcasted_data = data
        to_remove = []
        for conn in self.active_connections:
            try:
                await conn.send_json(data)
            except Exception as e:
                print(f"Removing disconnected client: {e}")
                to_remove.append(conn)
        for conn in to_remove:
            self.disconnect(conn)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total active: {len(self.active_connections)}")


manager = ConnectionManager()

# Initialize repos and scraper
price_repo = PriceRepository()
scraper = GoldScrapingService(repo=price_repo)

@app.on_event("startup")
async def startup_event():
    print("--- APPLICATION STARTUP ---")
    await connect_to_mongo()
    mongo_client = get_mongo_client()
    app.state.user_repo = UserRepository(mongo_client)

    # Start async scraper loop
    asyncio.create_task(scraper.run_scraper_loop_async(mongo_client))


@app.on_event("shutdown")
async def shutdown_event():
    print("--- APPLICATION SHUTDOWN ---")
    if scraper.browser:
        await scraper._close_browser()
    await close_mongo_connection()


# Include routers
app.include_router(websocket.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(users.router)

@app.get("/")
def read_root():
    return {"status": "running", "message": "WebSocket server is active."}
