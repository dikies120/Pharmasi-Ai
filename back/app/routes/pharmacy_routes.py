
from fastapi import APIRouter, Depends, Request

from back.app.controllers.pharmacy_controller import PharmacyController
from back.app.middleware.auth import require_pharmacist_or_admin
from back.app.request_audit import persist_api_io

router = APIRouter(
    prefix="/pharmacy", 
    tags=["Pharmacy"],
    dependencies=[Depends(require_pharmacist_or_admin)]
)
pharmacy_controller = PharmacyController()


@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(require_pharmacist_or_admin)):
    result = await pharmacy_controller.get_dashboard_data()
    persist_api_io(
        endpoint="/api/v1/pharmacy/dashboard",
        method="GET",
        status="success",
        user_id=current_user.get("email")
    )
    return result


@router.get("/inventory/realtime")
async def get_inventory_realtime(current_user: dict = Depends(require_pharmacist_or_admin)):
    result = await pharmacy_controller.get_inventory_realtime()
    persist_api_io(
        endpoint="/api/v1/pharmacy/inventory",
        method="GET",
        status="success",
        user_id=current_user.get("email")
    )
    return result


@router.get("/medicines")
async def get_medicines():
    return await pharmacy_controller.get_medicines_list()

@router.get("/queue/validation")
async def get_validation_queue(current_user: dict = Depends(require_pharmacist_or_admin)):
    result = await pharmacy_controller.get_validation_queue()
    persist_api_io(
        endpoint="/api/v1/pharmacy/validasi",
        method="GET",
        status="success",
        user_id=current_user.get("email")
    )
    return result

@router.post("/inventory/batches")
async def add_inventory_batch(request: Request):
    data = await request.json()
    return await pharmacy_controller.add_inventory_batch(data)

@router.put("/inventory/batches/{batch_id}")
async def update_inventory_batch(batch_id: int, request: Request):
    data = await request.json()
    return await pharmacy_controller.update_inventory_batch(batch_id, data)

@router.delete("/inventory/batches/{batch_id}")
async def delete_inventory_batch(batch_id: int):
    return await pharmacy_controller.delete_inventory_batch(batch_id)


