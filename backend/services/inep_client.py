import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from backend.config import INEP_DOWNLOAD_BASE, INEP_PAGE_BASE, PDF_DIR

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# INEP download server may fail certificate validation on some Windows setups.
INEP_HTTP_VERIFY = False


def build_pdf_urls(year: int, caderno: int, day: int = 1) -> tuple[str, str]:
    prova = f"{INEP_DOWNLOAD_BASE}/{year}_PV_impresso_D{day}_CD{caderno}.pdf"
    gabarito = f"{INEP_DOWNLOAD_BASE}/{year}_GB_impresso_D{day}_CD{caderno}.pdf"
    return prova, gabarito


def _pdf_paths(year: int, caderno: int, day: int) -> tuple[Path, Path]:
    year_dir = PDF_DIR / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    prova_path = year_dir / f"D{day}_CD{caderno}_prova.pdf"
    gabarito_path = year_dir / f"D{day}_CD{caderno}_gabarito.pdf"
    return prova_path, gabarito_path


async def _url_exists(client: httpx.AsyncClient, url: str) -> bool:
    try:
        response = await client.head(url, follow_redirects=True)
        if response.status_code == 405:
            response = await client.get(url, follow_redirects=True)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def _discover_pdf_urls(
    client: httpx.AsyncClient, year: int, caderno: int, day: int = 1
) -> tuple[str, str] | None:
    page_url = f"{INEP_PAGE_BASE}/{year}"
    try:
        response = await client.get(page_url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    prova_url: str | None = None
    gabarito_url: str | None = None

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if ".pdf" not in href.lower():
            continue

        absolute = href
        if href.startswith("/"):
            absolute = f"https://www.gov.br{href}"
        elif not href.startswith("http"):
            continue

        href_upper = absolute.upper()
        text_upper = link.get_text(" ", strip=True).upper()

        is_day = f"D{day}" in href_upper or f"DIA_{day}" in href_upper or f"DIA {day}" in text_upper
        is_caderno = (
            f"CD{caderno}" in href_upper
            or f"CAD_{caderno:02d}" in href_upper
            or f"CAD_{caderno}" in href_upper
            or f"CADERNO {caderno}" in text_upper
            or f"CADERNO {caderno} " in text_upper
        )
        if not is_day or not is_caderno:
            continue

        if "GB" in href_upper or "GABARITO" in href_upper or "GABARITO" in text_upper:
            gabarito_url = absolute
        elif (
            "PV" in href_upper
            or "PROVA" in href_upper
            or "PROVA" in text_upper
        ) and "GABARITO" not in text_upper:
            prova_url = absolute

    if prova_url and gabarito_url:
        return prova_url, gabarito_url
    return None


async def _download_file(client: httpx.AsyncClient, url: str, destination: Path) -> None:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    destination.write_bytes(response.content)


async def download_exam_pdfs(year: int, caderno: int, day: int = 1) -> tuple[Path, Path]:
    prova_path, gabarito_path = _pdf_paths(year, caderno, day)
    if prova_path.exists() and gabarito_path.exists():
        return prova_path, gabarito_path

    prova_url, gabarito_url = build_pdf_urls(year, caderno, day)
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(
        headers=headers, timeout=60.0, verify=INEP_HTTP_VERIFY
    ) as client:
        urls_valid = await _url_exists(client, prova_url) and await _url_exists(
            client, gabarito_url
        )
        if not urls_valid:
            discovered = await _discover_pdf_urls(client, year, caderno, day)
            if not discovered:
                raise FileNotFoundError(
                    f"Não foi possível encontrar PDFs do ENEM {year} caderno {caderno}."
                )
            prova_url, gabarito_url = discovered

        await _download_file(client, prova_url, prova_path)
        await _download_file(client, gabarito_url, gabarito_path)

    return prova_path, gabarito_path


def normalize_legacy_filename(name: str) -> re.Match[str] | None:
    return re.search(r"ENEM[_-]?(\d{4}).*DIA[_-]?[12]", name, re.IGNORECASE)
