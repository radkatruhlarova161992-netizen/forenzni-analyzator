"""Zdroj ADIS / registr DPH."""

from functools import lru_cache
from typing import Any
from xml.etree import ElementTree as ET

import requests

from core.config import ADIS_NS, ADIS_URL, REQUEST_TIMEOUT


@lru_cache(maxsize=256)
def fetch_dph_status(ico: str, dic_hint: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "dph_status": "neznámý",
        "nespolehlivy_platce": None,
        "datum_zverejneni": None,
        "dph_chyba": None,
        "zdroj_dph": (
            "https://adisrws.mfcr.cz/adistc/axis2/services/"
            "rozhraniCRPDPH.rozhraniCRPDPHSOAP?wsdl"
        ),
    }

    dic = dic_hint or ico
    soap_body = f"""<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <StatusNespolehlivyPlatceRequest xmlns="http://adis.mfcr.cz/rozhraniCRPDPH/">
      <dic>{dic}</dic>
    </StatusNespolehlivyPlatceRequest>
  </soapenv:Body>
</soapenv:Envelope>"""

    try:
        resp = requests.post(
            ADIS_URL,
            data=soap_body.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        status_platce = root.find(f".//{ADIS_NS}statusPlatceDPH")

        if status_platce is None:
            out["dph_status"] = "nenalezeno"
            return out

        nespolehlivy = status_platce.attrib.get("nespolehlivyPlatce", "NE")
        out["nespolehlivy_platce"] = nespolehlivy == "ANO"
        out["datum_zverejneni"] = status_platce.attrib.get("datumZverejneniNespolehlivosti")
        out["dph_status"] = "ok"
    except requests.exceptions.Timeout:
        out["dph_status"] = "failed"
        out["dph_chyba"] = "Registr DPH (ADIS) neodpověděl včas."
    except requests.exceptions.RequestException as exc:
        out["dph_status"] = "failed"
        out["dph_chyba"] = f"Chyba spojení s registrem DPH: {exc}"
    except ET.ParseError as exc:
        out["dph_status"] = "failed"
        out["dph_chyba"] = f"Nelze zpracovat odpověď registru DPH (XML): {exc}"

    return out
