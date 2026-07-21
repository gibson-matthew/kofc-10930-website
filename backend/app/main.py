# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Define allowed origins (can be specific domains or "*")
# For production, avoid "*" and list only trusted domains
origins = [
    "http://localhost",
    "http://localhost:5173",
    "https://yourdomain.com"
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # List of allowed origins
    allow_credentials=True,           # Allow cookies/auth headers
    allow_methods=["*"],               # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],               # Allow all headers
)

# Test route
@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI!"}