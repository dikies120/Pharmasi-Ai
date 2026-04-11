from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import date


class ChatRequest(BaseModel):
    question: str = Field(..., description="Pertanyaan apapun tentang obat, stok, harga, atau kadaluarsa")
    user_id: Optional[str] = Field(default="user_1", description="User identifier")


class ToolResponse(BaseModel):
    tool: str = Field(..., description="Nama tool yang digunakan")
    result: str = Field(..., description="Hasil dari tool")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Jawaban dari sistem")
    tool_used: Optional[str] = Field(default=None, description="Tool yang digunakan")
    user_id: Optional[str] = Field(default=None, description="User identifier")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Status aplikasi")
    mcp_connected: bool = Field(..., description="Status koneksi MCP")
    version: str = Field(..., description="Versi aplikasi")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Deskripsi error")
    error_type: Optional[str] = Field(default=None, description="Tipe error")
