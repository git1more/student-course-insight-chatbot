from pathlib import Path
import pandas as pd


class ExcelService:
    def __init__(self):
        self._records = None

        self._program_aliases = {
            "cs": "Computer Science",
            "comp sci": "Computer Science",
            "computer science": "Computer Science",
            "eng": "Engineering",
            "engineering": "Engineering",
            "comm": "Commerce",
            "commerce": "Commerce",
            "sci": "Science",
            "science": "Science",
        }

    def load_records(self):
        if self._records is not None:
            return self._records

        file_path = Path(__file__).resolve().parents[3] / "CommentsData06032026a.xlsx"
        df = pd.read_excel(file_path, sheet_name="release")

        df = df.rename(columns={
            "Year": "year",
            "program": "program",
            "Needs_improvement": "comment",
        })

        df = df[["year", "program", "comment"]].dropna()

        records = []
        for idx, row in df.iterrows():
            records.append({
                "comment_id": int(idx) + 1,
                "year": int(row["year"]),
                "program": str(row["program"]).strip(),
                "comment": str(row["comment"]).strip(),
            })

        self._records = records
        return self._records

    def get_programs(self):
        records = self.load_records()
        programs = sorted({r["program"] for r in records})
        return programs

    def get_years(self):
        records = self.load_records()
        years = sorted({int(r["year"]) for r in records})
        return years

    def normalize_program(self, program: str):
        raw = program.strip()
        key = raw.lower()

        if key in self._program_aliases:
            return self._program_aliases[key]

        available_programs = self.get_programs()

        for item in available_programs:
            if item.lower() == key:
                return item

        for item in available_programs:
            if key in item.lower():
                return item

        return raw

    def filter_records(self, program: str, year: int):
        records = self.load_records()
        normalized_program = self.normalize_program(program)
        program_norm = normalized_program.strip().lower()
        year_int = int(year)

        return [
            r for r in records
            if r["program"].strip().lower() == program_norm and int(r["year"]) == year_int
        ]


excel_service = ExcelService()