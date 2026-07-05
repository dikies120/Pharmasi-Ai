from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from passlib.context import CryptContext

from back.app.core.jwt import create_access_token, decode_access_token
from back.database.pgvektor import get_db_connection

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


class AuthController:

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    async def _find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            # Coba ambil dengan kolom role, fallback ke pharmacist jika kolom belum ada
            try:
                cursor.execute(
                    "SELECT id, name, email, password_hash, role, nik FROM users WHERE email = %s",
                    (email,)
                )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return {"id": row[0], "name": row[1], "email": row[2], "password": row[3], "role": row[4] or "patient", "nik": row[5]}
            except Exception:
                # Fallback jika kolom role belum ada — default patient karena register publik
                cursor.close()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, email, password_hash, nik FROM users WHERE email = %s",
                    (email,)
                )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return {"id": row[0], "name": row[1], "email": row[2], "password": row[3], "role": "patient", "nik": row[4]}
            return None
        finally:
            conn.close()

    async def _ensure_role_column(self, conn) -> None:
        """Pastikan kolom role ada di tabel users"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'pharmacist'
            """)
            cursor.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS nik VARCHAR(50)
            """)
            conn.commit()
            cursor.close()
        except Exception as e:
            logger.warning(f"Could not add role column (may already exist): {e}")
            conn.rollback()

    async def register(self, name: str, email: str, password: str, role: str = "patient", nik: str = None) -> Dict[str, Any]:
        if await self._find_user_by_email(email):
            raise ValueError("Email sudah terdaftar")
            
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
            
        try:
            cursor = conn.cursor()
            if nik:
                cursor.execute("SELECT id FROM users WHERE nik = %s", (nik,))
                if cursor.fetchone():
                    raise ValueError("NIK ini sudah didaftarkan pada akun lain")
            cursor.close()
        except ValueError:
            raise
        except Exception:
            pass
            
        try:
            await self._ensure_role_column(conn)
            user_id = str(uuid.uuid4())
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, name, email, password_hash, role, nik, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, name, email, self._hash_password(password), role, nik, datetime.now(), datetime.now())
            )
            conn.commit()
            cursor.close()
            return {"user": {"id": user_id, "name": name, "email": email, "role": role, "nik": nik}, "message": "Registrasi berhasil"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Register error: {e}")
            raise ValueError(f"Gagal registrasi: {str(e)}")
        finally:
            conn.close()

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        user = await self._find_user_by_email(email.strip().lower())
        if not user or not self._verify_password(password, user["password"]):
            raise ValueError("Email atau password salah")
        role = user.get("role", "pharmacist")
        access_token = create_access_token({
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": role
        })
        return {
            "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": role, "nik": user.get("nik")},
            "access_token": access_token,
            "token_type": "bearer",
            "message": "Login berhasil"
        }

    async def change_password(self, email: str, new_password: str) -> Dict[str, Any]:
        if not await self._find_user_by_email(email):
            raise ValueError("User tidak ditemukan")
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = %s, updated_at = %s WHERE email = %s",
                (self._hash_password(new_password), datetime.now(), email)
            )
            conn.commit()
            cursor.close()
            return {"message": "Password berhasil diubah"}
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Gagal mengubah password: {str(e)}")
        finally:
            conn.close()

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        return decode_access_token(token)

    async def list_all_users(self) -> list:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "role": row[3] or "patient",
                    "created_at": row[4].isoformat() if row[4] else None,
                }
                for row in rows
            ]
        finally:
            conn.close()

    async def update_user_role(self, user_id: str, role: str) -> Dict[str, Any]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET role = %s, updated_at = %s WHERE id = %s RETURNING id, name, email, role",
                (role, datetime.now(), user_id)
            )
            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            if not row:
                raise ValueError("User tidak ditemukan")
            return {
                "message": f"Role berhasil diubah ke '{role}'",
                "user": {"id": row[0], "name": row[1], "email": row[2], "role": row[3]}
            }
        except ValueError:
            raise
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Gagal update role: {str(e)}")
        finally:
            conn.close()

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM users WHERE id = %s RETURNING id, name, email",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            if not row:
                raise ValueError("User tidak ditemukan")
            return {"message": f"User '{row[1]}' berhasil dihapus"}
        except ValueError:
            raise
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Gagal hapus user: {str(e)}")
        finally:
            conn.close()
