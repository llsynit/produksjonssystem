#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys
import traceback
from urllib.parse import quote
from requests.auth import HTTPBasicAuth

import requests


def load_dotenv(path=".env"):
    """
    Enkel .env-leser uten python-dotenv.
    Støtter linjer som:
        KEY=value
        KEY="value"
        KEY='value'
    """
    if not os.path.isfile(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if (
                len(value) >= 2
                and (
                    (value[0] == '"' and value[-1] == '"')
                    or (value[0] == "'" and value[-1] == "'")
                )
            ):
                value = value[1:-1]

            os.environ.setdefault(key, value)


def normalize_base_url(url):
    if not url:
        return None

    url = url.strip().strip('"').strip("'")

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    return url.rstrip("/")


def print_header(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_json(obj, max_chars=5000):
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        text = repr(obj)

    if len(text) > max_chars:
        print(text[:max_chars])
        print("\n... [avkortet]")
    else:
        print(text)


def print_text(text, max_chars=3000):
    if text is None:
        print("None")
        return

    text = str(text)

    if len(text) > max_chars:
        print(text[:max_chars])
        print("\n... [avkortet]")
    else:
        print(text)


def try_parse_xml(label, text):
    print_header(f"XML-sjekk: {label}")

    if text is None:
        print("Ingen tekst å parse.")
        return False

    try:
        from lxml import etree as ElementTree
        ElementTree.fromstring(text.encode("utf-8"))
        print("OK: kunne parses som XML med lxml.")
        return True
    except Exception:
        print("FEIL: kunne ikke parses som XML.")
        print(traceback.format_exc())
        return False


def direct_get_json(url, timeout=20, auth=None):
    print(f"GET {url}")
    response = requests.get(url, timeout=timeout, auth=auth)
    print(f"HTTP {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")

    try:
        data = response.json()
        print_json(data)
        return response, data
    except Exception:
        print("Kunne ikke parse JSON. Første del av tekstrespons:")
        print_text(response.text, max_chars=2000)
        return response, None


def direct_get_text(url, timeout=20, auth=None):
    print(f"GET {url}")
    response = requests.get(url, timeout=timeout, auth=auth)
    print(f"HTTP {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print_text(response.text, max_chars=3000)
    return response


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "produksjonsnummer",
        help="Produksjonsnummer/artikkelnummer/edition identifier, f.eks. 864115",
    )

    parser.add_argument(
        "--project-dir",
        default="produksjonssystem",
        help="Mappe som inneholder core/utils/metadata.py. Default: produksjonssystem",
    )

    parser.add_argument(
        "--env-file",
        default=".env",
        help="Sti til .env-fil. Default: .env",
    )

    parser.add_argument(
        "--nlb-api-url",
        default=None,
        help="Overstyr NLB_API_URL fra .env.",
    )

    parser.add_argument(
        "--lmsyn-api-url",
        default=None,
        help="Overstyr LMSYN_API_URL fra .env.",
    )

    parser.add_argument(
        "--lmsyn-username",
        default=None,
        help="Overstyr LMSYN_USERNAME fra .env.",
    )

    parser.add_argument(
        "--lmsyn-password",
        default=None,
        help="Overstyr LMSYN_PASSWORD fra .env.",
    )

    parser.add_argument(
        "--no-direct-nlb",
        action="store_true",
        help="Hopp over direkte kall mot NLB API.",
    )

    parser.add_argument(
        "--no-direct-lmsyn",
        action="store_true",
        help="Hopp over direkte kall mot LMSyn API.",
    )

    args = parser.parse_args()

    load_dotenv(args.env_file)

    produksjonsnummer = str(args.produksjonsnummer)

    nlb_api_url = normalize_base_url(
        args.nlb_api_url or os.environ.get("NLB_API_URL") or "https://api.nlb.no/v1"
    )

    lmsyn_api_url = normalize_base_url(
        args.lmsyn_api_url or os.environ.get("LMSYN_API_URL")
    )

    lmsyn_username = args.lmsyn_username or os.environ.get("LMSYN_USERNAME")
    lmsyn_password = args.lmsyn_password or os.environ.get("LMSYN_PASSWORD")

    lmsyn_auth = None
    if lmsyn_username and lmsyn_password:
        lmsyn_auth = HTTPBasicAuth(lmsyn_username, lmsyn_password)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s: %(message)s",
    )
    report = logging.getLogger("metadata-api-test")

    project_dir = os.path.abspath(args.project_dir)
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    print_header("Import og konfig")
    print(f"project_dir: {project_dir}")
    print(f"env_file: {os.path.abspath(args.env_file)}")
    print(f"produksjonsnummer: {produksjonsnummer}")
    print(f"nlb_api_url: {nlb_api_url}")
    print(f"lmsyn_api_url: {lmsyn_api_url}")
    print(f"lmsyn_username: {'satt' if lmsyn_username else 'MANGLER'}")
    print(f"lmsyn_password: {'satt' if lmsyn_password else 'MANGLER'}")
    print(f"lmsyn_auth: {'Basic Auth aktiv' if lmsyn_auth else 'IKKE aktiv'}")

    if not lmsyn_api_url:
        print("FEIL: LMSYN_API_URL mangler.")
        return 2

    try:
        import core.utils.metadata as metadata_module
        from core.utils.metadata import Metadata
        from core.config import Config
    except Exception:
        print("FEIL: Klarte ikke å importere core.utils.metadata.")
        print("Sjekk at --project-dir peker på mappen som inneholder core/.")
        print(traceback.format_exc())
        return 2

    print(f"metadata.py importert fra: {metadata_module.__file__}")

    # -------------------------------------------------------------------------
    # Monkeypatch Config.get
    # -------------------------------------------------------------------------

    original_config_get = Config.get

    config_overrides = {
        "nlb_api_url": nlb_api_url,
        "lmsyn_api_url": lmsyn_api_url,
        "lmsyn_username": lmsyn_username,
        "lmsyn_password": lmsyn_password,
        "LMSYN_API_URL": lmsyn_api_url,
        "LMSYN_USERNAME": lmsyn_username,
        "LMSYN_PASSWORD": lmsyn_password,
        "NLB_API_URL": nlb_api_url,
    }

    def patched_config_get(key, *get_args, **get_kwargs):
        if key in config_overrides:
            return config_overrides[key]
        return original_config_get(key, *get_args, **get_kwargs)

    Config.get = staticmethod(patched_config_get)
    metadata_module.Config.get = staticmethod(patched_config_get)

    # -------------------------------------------------------------------------
    # Monkeypatch Metadata.requests_get
    # -------------------------------------------------------------------------

    def traced_requests_get(url, cache_timeout=30):
        print(f"[Metadata.requests_get] GET {url}")

        auth = None
        if lmsyn_api_url and url.startswith(lmsyn_api_url):
            auth = lmsyn_auth

        try:
            response = requests.get(url, timeout=20, auth=auth)
            print(f"[Metadata.requests_get] HTTP {response.status_code}")
            return response
        except Exception:
            print("[Metadata.requests_get] FEIL ved request:")
            print(traceback.format_exc())
            return None

    Metadata.requests_get = staticmethod(traced_requests_get)

    # -------------------------------------------------------------------------
    # Direkte LMSyn-kall
    # -------------------------------------------------------------------------

    lmsyn_raw_json = None

    if not args.no_direct_lmsyn:
        print_header("Direkte LMSyn-kall")
        lmsyn_url = "{}/produksjon/metadata/artikkelnr/{}".format(
            lmsyn_api_url,
            quote(produksjonsnummer, safe=""),
        )

        lmsyn_response, lmsyn_raw_json = direct_get_json(
            lmsyn_url,
            auth=lmsyn_auth,
        )

        if lmsyn_response.status_code != 200:
            print("LMSyn svarte ikke 200. Hopper over konvertering av LMSyn-respons.")
            lmsyn_raw_json = None

    # -------------------------------------------------------------------------
    # Test konverteringsmetoden direkte
    # -------------------------------------------------------------------------

    if lmsyn_raw_json is not None:
        print_header("Metadata.convert_lmsyn_metadata_to_nlb_shape(raw_lmsyn_json)")
        try:
            converted = Metadata.convert_lmsyn_metadata_to_nlb_shape(lmsyn_raw_json)
            print_json(converted)
        except Exception:
            print("FEIL i convert_lmsyn_metadata_to_nlb_shape:")
            print(traceback.format_exc())

    # -------------------------------------------------------------------------
    # Direkte NLB-kall
    # -------------------------------------------------------------------------

    if not args.no_direct_nlb:
        print_header("Direkte NLB-kall: /editions/{id}")
        nlb_edition_url = "{}/editions/{}".format(
            nlb_api_url,
            quote(produksjonsnummer, safe=""),
        )
        direct_get_json(nlb_edition_url)

        print_header("Direkte NLB-kall: /editions/{id}/metadata?format=opf")
        nlb_opf_url = "{}/editions/{}/metadata?format=opf".format(
            nlb_api_url,
            quote(produksjonsnummer, safe=""),
        )
        direct_get_text(nlb_opf_url)

        print_header("Direkte NLB-kall: /editions/{id}/metadata?format=html")
        nlb_html_url = "{}/editions/{}/metadata?format=html".format(
            nlb_api_url,
            quote(produksjonsnummer, safe=""),
        )
        direct_get_text(nlb_html_url)

    # -------------------------------------------------------------------------
    # Metadata.get_edition_from_lmsyn_api
    # -------------------------------------------------------------------------

    for fmt in ["json", "opf", "html"]:
        print_header(f"Metadata.get_edition_from_lmsyn_api(..., format='{fmt}')")

        try:
            result = Metadata.get_edition_from_lmsyn_api(
                produksjonsnummer,
                format=fmt,
                report=report,
            )

            if fmt == "json":
                print_json(result)
            else:
                print_text(result)
                try_parse_xml(f"LMSyn {fmt}", result)

        except Exception:
            print("FEIL:")
            print(traceback.format_exc())

    # -------------------------------------------------------------------------
    # Metadata.get_edition_from_api med normal Config
    # -------------------------------------------------------------------------

    for fmt in ["json", "opf", "html"]:
        print_header(f"Metadata.get_edition_from_api(..., format='{fmt}') med normal Config")

        try:
            result = Metadata.get_edition_from_api(
                produksjonsnummer,
                format=fmt,
                report=report,
            )

            if fmt == "json":
                print_json(result)
            else:
                print_text(result)
                try_parse_xml(f"get_edition_from_api {fmt}", result)

        except Exception:
            print("FEIL:")
            print(traceback.format_exc())

    # -------------------------------------------------------------------------
    # Tvungen fallback
    # -------------------------------------------------------------------------

    print_header("TVUNGET FALLBACK: nlb_api_url=None")

    config_overrides["nlb_api_url"] = None

    for fmt in ["json", "opf", "html"]:
        print_header(f"Tvunget fallback, format='{fmt}'")

        try:
            result = Metadata.get_edition_from_api(
                produksjonsnummer,
                format=fmt,
                report=report,
            )

            if fmt == "json":
                print_json(result)
            else:
                print_text(result)
                try_parse_xml(f"tvunget fallback {fmt}", result)

        except Exception:
            print("FEIL:")
            print(traceback.format_exc())

    print_header("Ferdig")
    print("Se særlig etter:")
    print("- HTTP 200 fra LMSyn")
    print("- at LMSyn-responsen inneholder artikkelNr/tittel/isbn")
    print("- at OPF/HTML fra fallback kan parses som XML")
    print("- at get_edition_from_api fungerer når nlb_api_url tvinges til None")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
