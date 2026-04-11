import logging
from typing import Optional

from back.services.info_obat import (
    search_by_stok,
    search_by_harga,
    search_by_kadaluarsa,
    format_result,
)

logger = logging.getLogger(__name__)

def search_obat_by_stock(pg_conn, operator: str, nilai: int, nama_obat: Optional[str] = None) -> dict:
    """Cari obat berdasarkan stok dengan parameter yang sudah diekstrak dari agent
    
    Flow:
    1. Terima partial nama_obat dari agent
    2. RESOLVE: partial name → full name dari database
    3. Query DB dengan resolved full name
    4. Return hasil dengan info tentang nama yang di-resolve
    """
    try:
        logger.info(f"[TOOL] search_obat_by_stock called: operator={operator}, nilai={nilai} (type={type(nilai).__name__}), nama_obat={nama_obat}")
        
        # Resolve partial medicine name if provided
        resolved_name = None
        if nama_obat:
            from back.services.info_obat import resolve_medicine_name
            resolved_name = resolve_medicine_name(pg_conn, nama_obat)
            logger.info(f"✓ Name Resolution: '{nama_obat}' → '{resolved_name}'")
        
        rows = search_by_stok(pg_conn, operator, nilai, nama_obat=nama_obat)

        if not rows:
            msg = f"Tidak ada data stok ditemukan untuk {resolved_name or nama_obat}" if nama_obat else "Tidak ada data stok ditemukan"
            logger.info(msg)
            return {
                "tool": "search_obat_by_stock",
                "status": "not_found",
                "resolved_name": resolved_name,
                "context": msg
            }

        result_text = format_result(rows)
        logger.info(f"Found {len(rows)} stock records")
        return {
            "tool": "search_obat_by_stock",
            "status": "success",
            "count": len(rows),
            "resolved_name": resolved_name,
            "context": result_text
        }

    except Exception as e:
        logger.error(f"Error in search_obat_by_stock: {str(e)}", exc_info=True)
        return {
            "tool": "search_obat_by_stock",
            "status": "error",
            "context": f"Error: {str(e)}"
        }


def search_obat_by_harga(pg_conn, operator: str, nilai: int, nama_obat: Optional[str] = None) -> dict:
    """Cari obat berdasarkan harga dengan parameter yang sudah diekstrak dari agent
    
    Flow:
    1. Terima partial nama_obat dari agent
    2. RESOLVE: partial name → full name dari database
    3. Query DB dengan resolved full name
    4. Return hasil dengan info tentang nama yang di-resolve
    """
    try:
        logger.info(f"Searching price: operator={operator}, nilai={nilai}, nama_obat={nama_obat}")
        
        # Resolve partial medicine name if provided
        resolved_name = None
        if nama_obat:
            from back.services.info_obat import resolve_medicine_name
            resolved_name = resolve_medicine_name(pg_conn, nama_obat)
            logger.info(f"✓ Name Resolution: '{nama_obat}' → '{resolved_name}'")
        
        rows = search_by_harga(pg_conn, operator, nilai, nama_obat=nama_obat)

        if not rows:
            msg = f"Tidak ada data harga ditemukan untuk {resolved_name or nama_obat}" if nama_obat else "Tidak ada data harga ditemukan"
            logger.info(msg)
            return {
                "tool": "search_obat_by_harga",
                "status": "not_found",
                "resolved_name": resolved_name,
                "context": msg
            }

        result_text = format_result(rows)
        logger.info(f"Found {len(rows)} price records")
        return {
            "tool": "search_obat_by_harga",
            "status": "success",
            "count": len(rows),
            "resolved_name": resolved_name,
            "context": result_text
        }

    except Exception as e:
        logger.error(f"Error in search_obat_by_harga: {str(e)}", exc_info=True)
        return {
            "tool": "search_obat_by_harga",
            "status": "error",
            "context": f"Error: {str(e)}"
        }


def search_obat_by_kadaluarsa(pg_conn, operator: str, tanggal: str, nama_obat: Optional[str] = None) -> dict:
    """Cari obat berdasarkan tanggal kadaluarsa dengan parameter yang sudah diekstrak dari agent
    
    Flow:
    1. Terima partial nama_obat dari agent
    2. RESOLVE: partial name → full name dari database
    3. Query DB dengan resolved full name
    4. Return hasil dengan info tentang nama yang di-resolve
    """
    try:
        logger.info(f"Searching expiry: operator={operator}, tanggal={tanggal}, nama_obat={nama_obat}")
        
        # Resolve partial medicine name if provided
        resolved_name = None
        if nama_obat:
            from back.services.info_obat import resolve_medicine_name
            resolved_name = resolve_medicine_name(pg_conn, nama_obat)
            logger.info(f"✓ Name Resolution: '{nama_obat}' → '{resolved_name}'")
        
        rows = search_by_kadaluarsa(pg_conn, operator, tanggal, nama_obat=nama_obat)

        if not rows:
            msg = f"Tidak ada data kadaluarsa ditemukan untuk {resolved_name or nama_obat}" if nama_obat else "Tidak ada data kadaluarsa ditemukan"
            logger.info(msg)
            return {
                "tool": "search_obat_by_kadaluarsa",
                "status": "not_found",
                "resolved_name": resolved_name,
                "context": msg
            }

        result_text = format_result(rows)
        logger.info(f"Found {len(rows)} expiry records")
        return {
            "tool": "search_obat_by_kadaluarsa",
            "status": "success",
            "count": len(rows),
            "resolved_name": resolved_name,
            "context": result_text
        }

    except Exception as e:
        logger.error(f"Error in search_obat_by_kadaluarsa: {str(e)}", exc_info=True)
        return {
            "tool": "search_obat_by_kadaluarsa",
            "status": "error",
            "context": f"Error: {str(e)}"
        }
