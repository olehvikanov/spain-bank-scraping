from bs4 import BeautifulSoup
import requests
import io
from datetime import datetime
import pdfplumber
import requests
import json
from langdetect import detect
from pdf2image import convert_from_bytes
from PIL import Image
import logging


base_url = "https://www.bde.es"
site_url = "https://www.bde.es/wbe/en/noticias-eventos/actualidad-banco-espana/notas-banco-espana/"

site_list = [
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-banco-espana/notas-banco-espana/",
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-banco-espana/intervenciones-publicas/",
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-banco-espana/articulos-entrevistas-alta-administracion/",
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-bce/notas-prensa-bce/",
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-bce/decisiones-politica-monetaria/",
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-bce/resenas-las-reuniones-politica-monetaria/",
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-bce/otras-decisiones-consejo-gobierno/",
    "https://www.bde.es/wbe/en/noticias-eventos/actualidad-bce/mecanismo-unico-supervision-mus/",
    "https://www.bde.es/wbe/en/noticias-eventos/otras-instituciones/mecanismo-unico-resolucion-mur/",
    "https://www.bde.es/wbe/en/noticias-eventos/otras-instituciones/junta-riesgo-sistemico-jers/",
    "https://www.bde.es/wbe/en/noticias-eventos/otras-instituciones/comite-supervision-bancaria-basilea-bcbs/",
    "https://www.bde.es/wbe/en/noticias-eventos/otras-instituciones/autoridad-bancaria-europea-eba/",
]

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "X-Amzn-Trace-Id": "Root=1-6563ac04-59e8d3725755f0b33d81e17d",
}

#### JSON FORMAT ####
query_start_date = ""
query_end_date = ""
run_start_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
datetime_accessed = ""
document_html = ""
document_text = ""
document_title = ""
document_text_source_language = ""
document_html_source_language = ""
document_title_source_language = ""
document_author = ""
document_url = ""

result = {
    "metadata": {
        "query_start_date": query_start_date,
        "query_end_date": query_end_date,
        "run_start_datetime": run_start_datetime,
    },
    "errors": [],
    "successes": [],
}

logging.basicConfig(
    filename=datetime.now().strftime("%Y-%m-%d") + "-run.log",
    filemode="a",  # 'w' to overwrite each time or 'a' to append
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def initial_json():
    global document_html, document_text, document_title, document_text_source_language, document_html_source_language, document_title_source_language, document_author, document_url
    document_html = ""
    document_text = ""
    document_title = ""
    document_text_source_language = ""
    document_html_source_language = ""
    document_title_source_language = ""
    document_author = ""
    document_url = ""


def get_pdf_url(article):
    try:
        article_url = article.find("a").get("href")
        article_response = requests.get(base_url + article_url, headers=headers)
        article_soup = BeautifulSoup(article_response.content, "html.parser")
        pdf_url = (
            article_soup.find(class_="block-entry-content__file__title")
            .find("a")
            .get("href")
        )
        title = article_soup.find("h1").text
        global document_title
        document_title = title
        global document_url
        document_url = base_url + pdf_url

        return document_url
    except Exception as e:
        print(e)
        add_error_to_json("No Link")


def extract_pdf(article):
    initial_json()
    try:
        pdf_url = get_pdf_url(article)
        print(pdf_url)
        pdf = requests.get(pdf_url, headers=headers)
        origin_text = ""
        if pdf.ok:
            logging.info(f"DOWNLOAD SUCCESS URL {pdf_url}")
            pdf_stream = io.BytesIO(pdf.content)
            with pdfplumber.open(pdf_stream) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    global document_text_source_language, document_text
                    if page_text:
                        origin_text += page_text + "\n"
                        if detect(origin_text) == "en":
                            document_text = origin_text
                        else:
                            document_text_source_language = origin_text
                    elif page_text is None:  ### ocr
                        im = page.to_image()
                        page_text = im.debug_tablefinder()
                        if page_text:
                            origin_text += page_text + "\n"
                            if detect(origin_text) == "en":
                                document_text = origin_text
                            else:
                                document_text_source_language = origin_text

            add_success_to_json()
        else:
            logging.error(f"DOWNLOAD FAILED URL: {pdf_url}")
            print(f"Failed to retrieve the PDF: status code {pdf.status_code}")
            add_error_to_json(
                f"Failed to retrieve the PDF: status code {pdf.status_code}"
            )
    except Exception as e:
        print("Error:: extract_pdf(): ", e)
        # add_error_to_json(f"Failed to retrieve the PDF: status code {pdf.status_code}")


def add_success_to_json():
    global result
    sub_json = {
        "datatime_accessed": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "document_html": document_html,
        "document_text": document_text,
        "document_title": document_title,
        "document_html_source_language": document_html_source_language,
        "document_text_source_language": document_text_source_language,
        "document_title_source_language": document_title_source_language,
        "document_author": document_author,
        "document_url": document_url,
    }
    result["successes"].append(sub_json)


def add_error_to_json(error):
    global result
    sub_json = {
        "datetime_accessed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "document_url": document_url,
        "processing_error": error,
    }
    result["errors"].append(sub_json)


def generate_json():
    global result
    with open("output.json", "w") as f:
        json.dump(result, f, indent=4)


def set_url_params(page, start, end, site_url):
    url = f"{site_url}?page={str(page)}&start={start}&end={end}&sort=DESC"
    print("URL:", url)
    return url


def convert_date(date):
    year = date.split("-")[0]
    month = date.split("-")[1]
    new_formart = f"{month}{year}"
    print(new_formart)
    return new_formart


def run_scrape(start, end, document_types):
    global result
    result["metadata"]["query_start_date"] = start
    result["metadata"]["query_end_date"] = end

    response = requests.get(
        set_url_params(1, convert_date(start), convert_date(end), site_url), headers=headers
    )
    if response.status_code == 200:
        logging.info(
            f"Page Load SUCCESS URL: {set_url_params(1, convert_date(start), convert_date(end), site_url)}"
        )
        soup = BeautifulSoup(response.content, "html.parser")
        count = soup.find(id="results-number").text.split()[0]
        count = int(count)
        if count % 10:
            page_count = count // 10 + 1
        else:
            page_count = count // 10
        print(page_count)
        for page in range(1, page_count + 1):
            response = requests.get(
                set_url_params(page, convert_date(start), convert_date(end), site_url), headers=headers
            )
            if response.status_code == 200:
                logging.info(
                    f"Page Load SUCCESS URL: {set_url_params(page, convert_date(start), convert_date(end), site_url)}"
                )
                soup = BeautifulSoup(response.content, "html.parser")
                article_list = soup.find_all(class_="block-search-result")
                for article in article_list:
                    extract_pdf(article)
            else:
                logging.error(
                    f"Page Load FAILED URL: {set_url_params(page, convert_date(start), convert_date(end), site_url)}"
                )
        generate_json()
    else:
        logging.error(
            f"Page Load FAILED URL: {set_url_params(1, convert_date(start), convert_date(end), site_url)}"
        )


run_scrape("2022-01-01", "2022-12-01", [])
