from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import os


def setup_cors(app: FastAPI):
    allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")

    # Jika "*" allow semua origin
    if allowed_origins_str.strip() == "*":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        allowed_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
