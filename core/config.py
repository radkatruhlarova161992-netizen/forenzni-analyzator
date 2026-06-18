"""Konfigurace aplikace a veřejných zdrojů dat."""

from pathlib import Path

APP_TITLE = "Forenzní analyzátor firemních struktur"
APP_ICON = "🔎"
APP_LAYOUT = "wide"

REQUEST_TIMEOUT = 12
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Forensic-Analyzer/1.0"
}

ARES_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
ARES_VR_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty-vr/{ico}"

ADIS_URL = "https://adisrws.mfcr.cz/adistc/axis2/services/rozhraniCRPDPH.rozhraniCRPDPHSOAP"
ADIS_NS = "{http://adis.mfcr.cz/rozhraniCRPDPH/}"

JUSTICE_SBIRKA_URL = "https://or.justice.cz/ias/ui/vypis-sl-firma?subjektId={subjekt_id}"
JUSTICE_VYPIS_URL = "https://or.justice.cz/ias/ui/rejstrik-$firma?ico={ico}"
JUSTICE_REJSTRIK_API = "https://or.justice.cz/ias/ui/rejstrik-$firma.json?ico={ico}"

ISIR_SEARCH_URL = "https://isir.justice.cz/isir/common/index.do"
KURZY_SEARCH_URL = "https://rejstrik-firem.kurzy.cz/hledej/?s={query}&r={only_valid}"

APP_STATE_PATH = Path(__file__).resolve().parent.parent / "app_state.json"
