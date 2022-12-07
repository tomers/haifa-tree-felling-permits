#!/usr/bin/env python3
"""Fetch Haifa tree felling permit and export them in Excel format
"""
import os
import re
import shlex
import subprocess
from pathlib import Path
from tempfile import gettempdir
import click
import pandas as pd
import pdfplumber
from bidi.algorithm import get_display
from geopy.geocoders import GoogleV3
from tqdm import tqdm

INPUT_FILE_URL = 'http://www1.haifa.muni.il/trees/rptPirsum.pdf'
OUTPUT_DIR = Path(gettempdir()).joinpath('build')
OUTPUT_PDF_FILE = OUTPUT_DIR.joinpath(Path(INPUT_FILE_URL).name)
OUTPUT_PARQUET_FILE = OUTPUT_PDF_FILE.with_suffix('.parquet')
OUTPUT_XLSX_FILE = OUTPUT_PDF_FILE.with_suffix('.xlsx')
GCP_API_KEY = os.getenv('GCP_API_KEY')
GEO_LOCATOR = GoogleV3(api_key=GCP_API_KEY) if GCP_API_KEY else None


def download_pdf_file():
    """Download the data file from web"""
    assert OUTPUT_PDF_FILE.parent.exists(), \
        f'Please mount output directory {OUTPUT_PDF_FILE.parent} as docker volume'
    cmd = f'wget -q {INPUT_FILE_URL} --output-document {OUTPUT_PDF_FILE}'
    subprocess.run(shlex.split(cmd), check=True)


def parse_cell(text):
    """Convert cell containing multi-line Hebrew text into a single line string"""
    # join lines (it is parsed in reverse for some reason),
    # and also strip excessive spaces
    line = ' '.join(map(lambda x: re.sub(
        ' +', ' ', x.strip()), text.split('\n')[::-1]))
    # fix Hebrew using Bidi
    return get_display(line)


def pdf_to_rows():
    """Generator that parses the input PDF file and return its rows.
        It joins all tables on all pages. Assuming single header line in first
        table
    """
    with pdfplumber.open(OUTPUT_PDF_FILE) as pdf:
        header = None
        for page in tqdm(pdf.pages, desc='Parsing PDF', unit=' page'):
            for table in page.extract_tables():
                for row in table:
                    row = [parse_cell(cell) for cell in row]
                    if header is None:
                        header = row
                        continue
                    yield dict(zip(header, row))


def parse_pdf_to_dataframe():
    """Parse tables in PDF and return its content as a dataframe"""
    rows = pdf_to_rows()
    df = pd.DataFrame.from_dict(rows)
    return df


def enrich_geo_data(row):
    """Send street address to Geo service and return GRO coordinates"""
    assert GEO_LOCATOR is not None, 'Missing GEO_LOCATOR'
    raw_address = ('%s %s' % (row.loc['רח'], row.loc['בית'])).strip()ip()
    raw_address += ', חיפה, ישראל'
    geo = GEO_LOCATOR.geocode(raw_address)
    return pd.Series([
        raw_address,
        geo.address,
        geo.altitude,
        geo.latitude,
        geo.longitude
    ])


def enrich_data(df):
    """Extend dataframe with GEO data retrieved from Geo locator service"""
    tqdm.pandas(desc='Fetching GEO data', unit=' address')
    df[['raw_address', 'address', 'altitude', 'latitude', 'longitude']] = \
        df.progress_apply(enrich_geo_data, axis=1)
    return df


@click.command()
@click.option('--download', is_flag=True, default=False, help='Download PDF file')
@click.option('--save-xlsx', is_flag=True, default=True, help='Save as Excel file')
@click.option('--enrich', is_flag=True, default=False, help='Save as Excel file')
def cli(download, save_xlsx, enrich):
    """Entrypoint for CLI commands"""
    if not download and OUTPUT_PARQUET_FILE.exists():
        df = pd.read_parquet(OUTPUT_PARQUET_FILE)
    else:
        download_pdf_file()
        df = parse_pdf_to_dataframe()
        if enrich:
            df = enrich_data(df)
        df.to_parquet(OUTPUT_PARQUET_FILE)

    if save_xlsx:
        df.to_excel(OUTPUT_XLSX_FILE)


if __name__ == '__main__':
    cli()
