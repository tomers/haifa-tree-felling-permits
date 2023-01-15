#!/usr/bin/env python3
"""Fetch Haifa tree felling permit and export them in Excel format
"""
import logging
import os
import re
import shlex
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
import boto3
import click
import pandas as pd
import pdfplumber
from bidi.algorithm import get_display
from geopy.geocoders import GoogleV3
from scrapingbee import ScrapingBeeClient
from tqdm import tqdm

fmt = '%(asctime)s %(name)s <%(levelname)s> %(message)s'
logging.basicConfig(level=logging.INFO, format=fmt)
LOG = logging.getLogger('haifa-tree-felling-permits')

INPUT_FILE_URL = 'http://www1.haifa.muni.il/trees/rptPirsum.pdf'
OUTPUT_DIR = Path('/output')
if not OUTPUT_DIR.exists():
    OUTPUT_DIR = Path(tempfile.mkdtemp())
OUTPUT_PDF_FILE = OUTPUT_DIR.joinpath(Path(INPUT_FILE_URL).name)
OUTPUT_PARQUET_FILE = OUTPUT_PDF_FILE.with_suffix('.parquet')
OUTPUT_XLSX_FILE = OUTPUT_PDF_FILE.with_suffix('.xlsx')
SCRAPINGBEE_API_KEY = os.getenv('SCRAPINGBEE_API_KEY')
GCP_API_KEY = os.getenv('GCP_API_KEY')
GEO_LOCATOR = GoogleV3(api_key=GCP_API_KEY) if GCP_API_KEY else None
AWS_FAKE_ENDPOINT = os.getenv('AWS_FAKE_ENDPOINT')
S3_CLIENT = boto3.client('s3', endpoint_url=AWS_FAKE_ENDPOINT)


def download_pdf_file(proxy_country=None):
    """Download the data file from web"""
    LOG.info("Downloading PDF file")
    assert OUTPUT_PDF_FILE.parent.exists()

    if proxy_country:
        # Download using ScrapingBee proxy
        assert SCRAPINGBEE_API_KEY, "Missing ScrapingBee API KEY"
        client = ScrapingBeeClient(api_key=SCRAPINGBEE_API_KEY)
        params = dict(country_code=proxy_country, premium_proxy=True)
        response = client.get(INPUT_FILE_URL, params=params)
        assert response.ok, f"Failed downloading file through proxy: {response}"
        OUTPUT_PDF_FILE.write_bytes(response.content)
    else:
        # Direct download
        cmd = f'wget -q {INPUT_FILE_URL} --output-document {OUTPUT_PDF_FILE}'
        try:
            subprocess.run(shlex.split(cmd), check=True)
        except subprocess.CalledProcessError as e:
            LOG.error("Failed downloading file: %s", cmd)
            if e.stdout:
                LOG.error("Stdout: %s", e.stdout.decode())
            if e.stderr:
                LOG.error("Stderr: %s", e.stderr.decode())
            raise


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
    LOG.info("Parsing PDF")
    rows = pdf_to_rows()
    return pd.DataFrame.from_dict(rows)


def enrich_geo_data(row):
    """Send street address to Geo service and return GRO coordinates"""
    assert GEO_LOCATOR is not None, "Missing GEO_LOCATOR"
    raw_address = f'{row.loc["רח"]} {row.loc["בית"]}'.strip()
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
    LOG.info("Enriching dataframe")
    tqdm.pandas(desc='Fetching GEO data', unit=' address')
    df[['raw_address', 'address', 'altitude', 'latitude', 'longitude']] = \
        df.progress_apply(enrich_geo_data, axis=1)
    return df


def upload_files_to_s3(s3_bucket, s3_path):
    """Upload output files to S3"""
    LOG.info("Uploading files to S3")
    now = datetime.now()
    backup_path = f'year={now.year}/month={now.month}/day={now.day}'
    for file in (OUTPUT_PDF_FILE, OUTPUT_PARQUET_FILE, OUTPUT_XLSX_FILE):
        basename = file.name
        if s3_path:
            basename = f'{s3_path}/{basename}'
        for s3_key in (basename, f'{backup_path}/{basename}'):
            LOG.info("Uploading to s3://%s/%s", s3_bucket, s3_key)
            S3_CLIENT.upload_file(Bucket=s3_bucket, Key=s3_key,
                                  Filename=str(file))


@click.command()
@click.option('--download', is_flag=True, default=False, help='Download PDF file')
@click.option('--save-xlsx', is_flag=True, default=True, help='Save as Excel file')
@click.option('--enrich', is_flag=True, default=False, help='Save as Excel file')
@click.option('--upload', is_flag=True, default=False, help='Upload files to S3')
@click.option('--s3-bucket', help='S3 bucket to upload to')
@click.option('--s3-path', help='S3 path to upload to')
@click.option('--proxy-country', help='Use scrapingbee proxy from the given country code')
@click.option('-v', '--verbose', count=True)
def cli(download, save_xlsx, enrich, upload, s3_bucket, s3_path, proxy_country, verbose):
    """Entrypoint for CLI commands"""
    # pylint: disable=too-many-arguments

    if not download and OUTPUT_PARQUET_FILE.exists():
        LOG.info("Reading Parquet file")
        df = pd.read_parquet(OUTPUT_PARQUET_FILE)
    else:
        download_pdf_file(proxy_country)
        df = parse_pdf_to_dataframe()
        if enrich:
            df = enrich_data(df)
        LOG.info("Storing Parquet file")
        df.to_parquet(OUTPUT_PARQUET_FILE)
    if verbose:
        LOG.info("\n%s", df)

    if save_xlsx:
        LOG.info("Storing Excel file")
        df.to_excel(OUTPUT_XLSX_FILE)

    if upload:
        assert s3_bucket, 'S3 bucket must be specified'
        upload_files_to_s3(s3_bucket, s3_path)


if __name__ == '__main__':
    cli()
