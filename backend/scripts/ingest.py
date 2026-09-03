"""
Data ingestion script: loads anonymised feedback from the Excel file into PostgreSQL,
generates OpenAI embeddings, and seeds demo user accounts.

Excel columns used:
  Year              → year        (stored as string e.g. "2022")
  program           → program     (e.g. "Computer Science")
  Needs_improvement → comment_text

Usage (from the backend/ directory):
    python scripts/ingest.py
    python scripts/ingest.py --file path/to/other.xlsx
    python scripts/ingest.py --batch-size 100
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')

import pandas as pd
from app.core.config import settings
from app.db.base import init_db, SessionLocal
from app.repositories.user_repo import user_repo
from app.repositories.feedback_repo import feedback_repo
from app.services.embedding_service import embedding_service

EXCEL_DEFAULT = Path(__file__).resolve().parents[2] / 'CommentsData06032026a.xlsx'


def load_excel(file_path: Path) -> list[dict]:
    print(f'Loading Excel: {file_path}')
    df = pd.read_excel(file_path, sheet_name='release')
    df = df.rename(columns={
        'Year': 'year',
        'program': 'program',
        'Needs_improvement': 'comment_text',
    })
    df = df[['year', 'program', 'comment_text']].dropna()
    records = []
    for idx, row in df.iterrows():
        year = str(int(row['year']))          # "2022", "2023", "2024"
        records.append({
            'comment_id': str(int(idx) + 1),
            'program': str(row['program']).strip(),
            'year': year,
            'comment_text': str(row['comment_text']).strip(),
        })
    print(f'  Loaded {len(records)} records.')
    return records


def chunk(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def ingest(file_path: Path, batch_size: int = 200, no_drop: bool = False) -> None:
    from app.db.base import Base, engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        conn.commit()
    if no_drop:
        print('Skipping table drop — upserting into existing schema …')
        Base.metadata.create_all(bind=engine)
    else:
        print('Dropping & recreating tables to apply new schema …')
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print('Tables recreated.')

    db = SessionLocal()
    try:
        print('Seeding demo users …')
        user_repo.seed_demo_users(db)

        records = load_excel(file_path)
        total = len(records)
        done = 0

        print(f'Generating embeddings in batches of {batch_size} …')
        for batch in chunk(records, batch_size):
            texts = [r['comment_text'] for r in batch]
            embeddings = embedding_service.embed_batch(texts)
            for record, emb in zip(batch, embeddings):
                feedback_repo.upsert(
                    db,
                    comment_id=record['comment_id'],
                    program=record['program'],
                    year=record['year'],
                    comment_text=record['comment_text'],
                    embedding=emb,
                )
            done += len(batch)
            print(f'  {done}/{total} ({done/total*100:.1f}%) ingested …')

        print('\nIngest complete.')
        print(f'  Programmes : {feedback_repo.get_programs(db)}')
        print(f'  Years      : {feedback_repo.get_years(db)}')
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest feedback data into PostgreSQL.')
    parser.add_argument('--file', type=Path, default=EXCEL_DEFAULT)
    parser.add_argument('--batch-size', type=int, default=200)
    parser.add_argument('--no-drop', action='store_true', help='Skip drop/recreate — upsert only')
    args = parser.parse_args()
    if not args.file.exists():
        print(f'Error: file not found: {args.file}', file=sys.stderr)
        sys.exit(1)
    ingest(args.file, args.batch_size, no_drop=args.no_drop)
