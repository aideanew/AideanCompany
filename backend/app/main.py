# -*- coding: utf-8 -*-
"""主应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import subscriptions, engines
from app.core.config import settings

app = FastAPI(
    title="AideanAgentFleet API",
    description="知识库平台后端 API",
    version="0.1.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3333"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["subscriptions"])
app.include_router(engines.router, prefix="/api/v1/engines", tags=["engines"])

@app.get("/")
async def root():
    return {"message": "AideanAgentFleet API 正在运行"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "aideanbot-backend"}
EOF
__zcode_status=$?
if [ "$__zcode_status" -eq 0 ]; then pwd -P > '/c/Users/EDY/AppData/Local/Temp/zcode-9c31bd75-57a8-4fd0-856c-663202155a6c-cwd'; fi
exit "$__zcode_status"
