#!/usr/bin/env python3
import shlex
import subprocess
from pathlib import Path
import click
import pandas as pd
import pdfplumber
from tqdm import tqdm

INPUT_FILE_URL = 'http://www1.haifa.muni.il/trees/rptPirsum.pdf'
OUTPUT_DIR = Path.cwd().joinpath('build')
OUTPUT_PDF_FILE = OUTPUT_DIR.joinpath(Path(INPUT_FILE_URL).name)
OUTPUT_PARQUET_FILE = OUTPUT_PDF_FILE.with_suffix('.parquet')
OUTPUT_XLSX_FILE = OUTPUT_PDF_FILE.with_suffix('.xlsx')


def download_pdf_file():
    """Download the data file from web"""
    cmd = f'wget -q {INPUT_FILE_URL} --output-document {OUTPUT_PDF_FILE}'
    subprocess.run(shlex.split(cmd), check=True)


def join_hebrew_multiline_text(text):
    """Convert multi-line Hebrew text into a single line string"""
    return ' '.join(text.strip().split('\n')[::-1])


def pdf_to_rows():
    """Generator that parses the input PDF file and return its rows.
        It joins all tables on all pages. Assuming single header line in first
        table
    """
    pdf = pdfplumber.open(OUTPUT_PDF_FILE)
    header = None
    for page in tqdm(pdf.pages, desc='Parsing PDF', unit=' page'):
        for table in page.extract_tables():
            for row in table:
                if header is None:
                    header = [join_hebrew_multiline_text(c) for c in row]
                    continue
                yield dict(zip(header, row))


def parse_pdf_to_dataframe():
    rows = pdf_to_rows()
    df = pd.DataFrame.from_dict(rows)
    return df


def normalize_data(df):
    df = df.applymap(join_hebrew_multiline_text)
    # reverse header row which contains all-Hebrew strings
    df.rename(columns={x: x[::-1] for x in df.columns}, inplace=True)

    # reverse specific columns with Hebrew text
    col_idxs_with_hebrew = [
        0,  # הערות לעצים
        2,  # שם עץ
        3,  # סוג עץ
        4,  # הערות לבקשה
        5,  # בית
        6,  # רח
        7,  # מקום הבקשה
        8,  # סיבה 2
        9,  # סיבה
        10,  # שם
        11,  # פעולה
    ]
    cols_with_hebrew = [df.columns[pos]
                        for pos in col_idxs_with_hebrew]
    for col in cols_with_hebrew:
        df[col] = df.loc[:, col].apply(lambda x: x[::-1])
    return df


@click.command()
@click.option('--download', is_flag=True, default=False, help='Download PDF file')
@click.option('--save-xlsx', is_flag=True, default=True, help='Save as Excel file')
def cli(download, save_xlsx):
    if not download and OUTPUT_PARQUET_FILE.exists():
        df = pd.read_parquet(OUTPUT_PARQUET_FILE)
    else:
        download_pdf_file()
        df = parse_pdf_to_dataframe()
        df = normalize_data(df)
        df.to_parquet(OUTPUT_PARQUET_FILE)

    if save_xlsx:
        df.to_excel(OUTPUT_XLSX_FILE)


if __name__ == '__main__':
    cli()
