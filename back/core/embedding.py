import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
from back.core.settings import settings
from typing import List, Optional
from back.database.pgvektor import get_cursor


def get_embedding_model():
    return SentenceTransformer(
        settings.EMBEDDING_MODEL,
        device=settings.EMBEDDING_DEVICE
    )

# csv_file = Path(__file__).resolve().parent.parent / "test.csv"
# df = pd.read_csv(csv_file)

def load_csv(csv_path: Path, content_columns: Optional[List[str]] = None, content_column_name: str = "content") -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"File CSV tidak ditemukan: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        df = pd.read_csv(csv_path, sep=";")

    if len(df.columns) == 1 and ";" in df.columns[0]:
        df = pd.read_csv(csv_path, sep=";")

    df = df.dropna(how="all").reset_index(drop=True)

    if content_columns is None:
        content_columns = list(df.columns)

    missing_cols = [c for c in content_columns if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Columns tidak ditemukan di CSV: {missing_cols}")

    df[content_column_name] = (
        df[content_columns]
        .astype(str)
        .fillna("")
        .agg(" ".join, axis=1)
        .str.strip()
    )

    return df

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks


def buat_embedding(df: pd.DataFrame, text_column: str = "content", chunk_size: int = 800, overlap: int = 150):
    try:
        model = get_embedding_model()
        conn, curr = get_cursor()

        sql_query = """
            INSERT INTO documents (content, embedding)
            VALUES (%s, %s)
            ON CONFLICT (content) DO NOTHING;
        """

        total_chunks = 0

        for index, row in df.iterrows():

            full_text = str(row[text_column])

            chunks = chunk_text(
                full_text,
                chunk_size=chunk_size,
                overlap=overlap
            )

            if not chunks:
                continue

            vectors = model.encode(
                chunks,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            for chunk_text_value, embedding in zip(chunks, vectors):
                curr.execute(
                    sql_query,
                    (chunk_text_value, embedding.tolist())
                )
                total_chunks += 1

            print(f"Row {index} → {len(chunks)} chunks ditambahkan")

        conn.commit()
        curr.close()
        conn.close()

        print(f"\n Total chunks tersimpan: {total_chunks}")

        return total_chunks

    except Exception as e:
        print(f"Error embedding: {e}")
        return None


if __name__ == "__main__":
    from pathlib import Path

    csv_file = Path("test.csv")

    df = load_csv(
        csv_file
    )

    print("Creating embeddings with chunking...")

    total = buat_embedding(
        df,
        chunk_size=400,
        overlap=80
    )

    print("CSV path   :", csv_file)
    print("Columns    :", df.columns.tolist())
    print("Total rows :", len(df))
    print("Total chunks :", total)
    print("\nPreview:")
    print(df.head())
