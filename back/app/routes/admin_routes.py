
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Dict

from back.app.controllers.auth_controller import AuthController
from back.app.middleware.auth import require_admin
from back.core.llm import get_llm
from back.database.mongo import get_mongo_client
from back.core.settings import settings

router = APIRouter(prefix="/admin", tags=["Admin"])
auth_controller = AuthController()


class CreatePharmacistRequest(BaseModel):
    name: str
    email: EmailStr
    password: str



@router.get("/users")
async def list_users(current_user: Dict = Depends(require_admin)):
    """Ambil semua user (hanya admin)"""
    try:
        users = await auth_controller.list_all_users()
        return {"users": users, "total": len(users)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/users/pharmacist", status_code=status.HTTP_201_CREATED)
async def create_pharmacist(
    request: CreatePharmacistRequest,
    current_user: Dict = Depends(require_admin),
):
    """Buat akun apoteker baru (hanya admin)"""
    try:
        result = await auth_controller.register(
            name=request.name,
            email=request.email,
            password=request.password,
            role="pharmacist",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))



@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Dict = Depends(require_admin),
):
    """Hapus user (hanya admin)"""
    if user_id == current_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat menghapus akun sendiri.",
        )
    try:
        result = await auth_controller.delete_user(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/llm/status")
async def get_llm_status(current_user: Dict = Depends(require_admin)):
    """Cek status LLM (hanya admin)"""
    try:
        llm = get_llm()
        # Ensure connection check
        is_available = llm.debug_connection(verbose=False)
        return {"status": "on" if is_available else "off", "model": llm.model}
    except Exception as e:
        return {"status": "off", "model": None, "error": str(e)}

@router.get("/dashboard-stats")
async def get_dashboard_stats(current_user: Dict = Depends(require_admin)):
    """Ambil statistik untuk admin dashboard"""
    try:
        users = await auth_controller.list_all_users()
        total_patients = sum(1 for u in users if u.get("role") == "patient")
        pharmacists = [u for u in users if u.get("role") == "pharmacist"]
        active_pharmacists = sum(1 for u in users if u.get("role") == "pharmacist")
        
        client = get_mongo_client()
        db = client[settings.MONGO_DB]
        
        validated_count = db["api_request_logs"].count_documents({
            "endpoint": "/api/v1/validasi-obat/",
            "method": "POST",
            "status": "success"
        })
        
        # Build pharmacist activities
        pharmacist_activities = []
        import datetime
        now = datetime.datetime.utcnow()
        for p in pharmacists:
            email = p.get("email")
            name = p.get("name")
            initials = "".join([n[0] for n in name.split()[:2]]).upper()
            
            latest_log = db["api_request_logs"].find_one(
                {"user_id": email},
                sort=[("created_at", -1)]
            )
            
            status = "Offline"
            time_str = "Belum pernah login"
            
            if latest_log:
                created_at = latest_log.get("created_at")
                if created_at:
                    diff = now - created_at
                    minutes_ago = int(diff.total_seconds() / 60)
                    if minutes_ago < 60:
                        time_str = f"{minutes_ago} menit lalu" if minutes_ago > 0 else "Baru saja"
                        status = "Online"
                    else:
                        hours_ago = minutes_ago // 60
                        days_ago = hours_ago // 24
                        if hours_ago < 24:
                            time_str = f"{hours_ago} jam lalu"
                        else:
                            time_str = f"{days_ago} hari lalu"
                        status = "Offline"
                    
            pharmacist_activities.append({
                "name": name,
                "initials": initials,
                "status": status,
                "time": time_str
            })
            
        return {
            "total_patients": total_patients,
            "active_pharmacists": active_pharmacists,
            "validated_prescriptions": validated_count,
            "pharmacist_activities": pharmacist_activities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
