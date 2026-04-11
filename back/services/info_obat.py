import re
from datetime import date, datetime

VALID_OPERATORS = ["<", ">", "<=", ">=", "="]

def _safe_operator(op: str) -> str:
    if op in VALID_OPERATORS:
        return op
    return "<"

def resolve_medicine_name(database, partial_name: str) -> str:
    if not partial_name or not partial_name.strip():
        return None
    
    partial_lower = partial_name.strip().lower()
    
    sql = "SELECT DISTINCT name FROM medications ORDER BY name ASC;"
    with database.cursor() as cur:
        cur.execute(sql)
        all_medicines = [row[0] for row in cur.fetchall()]
    
    for medicine in all_medicines:
        if medicine.lower() == partial_lower:
            return medicine
            
    matches = [m for m in all_medicines if partial_lower in m.lower()]
    if matches:
        return max(matches, key=len)
    
    return partial_name


def search_by_stok(database, operator: str, nilai: int, nama_obat: str = None):
    operator = _safe_operator(operator)
    if nilai is None: nilai = 0

    if nama_obat:
        resolved_name = resolve_medicine_name(database, nama_obat)
        sql = f"""
            SELECT m.name, sum(b.stock_qty), 15000, max(b.expiry_date)
            FROM inventory_batches b JOIN medications m ON m.id = b.medication_id
            WHERE m.name = %s
            GROUP BY m.name
            HAVING sum(b.stock_qty) {operator} %s
        """
        with database.cursor() as cur:
            cur.execute(sql, (resolved_name, nilai))
            return cur.fetchall()
    else:
        sql = f"""
            SELECT m.name, sum(b.stock_qty), 15000, max(b.expiry_date)
            FROM inventory_batches b JOIN medications m ON m.id = b.medication_id
            GROUP BY m.name
            HAVING sum(b.stock_qty) {operator} %s
        """
        with database.cursor() as cur:
            cur.execute(sql, (nilai,))
            return cur.fetchall()


def search_by_harga(database, operator: str, nilai: int, nama_obat: str = None):
    # Harga is not in SUPER FINAL schema, mocking equivalent response
    return []


def search_by_kadaluarsa(database, operator: str, nilai, nama_obat: str = None):
    operator = _safe_operator(operator)

    if isinstance(nilai, str):
        try:
            nilai = datetime.strptime(nilai, "%Y-%m-%d").date()
        except:
            nilai = date.today()

    if nama_obat:
        resolved_name = resolve_medicine_name(database, nama_obat)
        sql = f"""
            SELECT m.name, sum(b.stock_qty), 15000, min(b.expiry_date)
            FROM inventory_batches b JOIN medications m ON m.id = b.medication_id
            WHERE b.expiry_date {operator} %s AND m.name = %s
            GROUP BY m.name
        """
        with database.cursor() as cur:
            cur.execute(sql, (nilai, resolved_name))
            return cur.fetchall()
    else:
        sql = f"""
            SELECT m.name, sum(b.stock_qty), 15000, min(b.expiry_date)
            FROM inventory_batches b JOIN medications m ON m.id = b.medication_id
            WHERE b.expiry_date {operator} %s
            GROUP BY m.name
        """
        with database.cursor() as cur:
            cur.execute(sql, (nilai,))
            return cur.fetchall()

def search_by_nama(database, nama_obat: str):
    if not nama_obat or not nama_obat.strip():
        return []
    
    sql = """
        SELECT m.name, sum(b.stock_qty), 15000, max(b.expiry_date)
        FROM inventory_batches b JOIN medications m ON m.id = b.medication_id
        WHERE m.name ILIKE %s
        GROUP BY m.name
    """
    
    with database.cursor() as cur:
        cur.execute(sql, (f"%{nama_obat}%",))
        return cur.fetchall()

def format_result(rows):
    if not rows:
        return "Data tidak ditemukan"

    hasil = []
    for r in rows:
        hasil.append(
            f"- {r[0]} | Stok: {r[1]} | Harga: Estimasi | Exp: {r[3]}"
        )

    return "\n".join(hasil)