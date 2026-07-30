"""Client for the mapforham.com API."""

import requests

BASE_URL = "https://www.mapforham.com/api/"
TIMEOUT = 15

MFH_FIELDS = [
    "my_gridsquare", "qso_date", "qso_date_off", "time_on", "time_off",
    "mode", "freq", "band", "comment", "callsign", "name", "gridsquare",
    "rst_sent", "rst_rcvd", "qth", "state", "tx_pwr",
    "my_pota_ref", "pota_ref", "notes",
]


def _params(tag: str, type_: str, data: str, api_key: str, fmt: str = "JSON") -> dict:
    return {"tag": tag, "type": type_, "data": data, "api_key": api_key, "format": fmt}


def read_logbook(username: str, api_key: str) -> dict:
    """Fetch the full logbook for *username* from MFH."""
    try:
        r = requests.get(
            BASE_URL,
            params=_params("LOGBOOK", "SELECT", username, api_key),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return {"ok": True, "data": r.json()}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def insert_qso(username: str, api_key: str, qso: dict) -> dict:
    """Insert a single QSO into MFH logbook via POST."""
    payload = {k: v for k, v in qso.items() if k in MFH_FIELDS and v}
    try:
        r = requests.post(
            BASE_URL,
            params=_params("LOGBOOK", "INSERT", username, api_key),
            data=payload,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return {"ok": True, "data": r.json()}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def delete_qso(username: str, api_key: str, mfh_id: str) -> dict:
    """Delete a QSO from MFH by its remote ID."""
    data_param = f"{mfh_id};{username}"
    try:
        r = requests.get(
            BASE_URL,
            params=_params("LOGBOOK", "DELETE", data_param, api_key),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return {"ok": True, "data": r.json()}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def lookup_callsign(callsign: str, api_key: str) -> dict:
    """Look up callbook data for a callsign."""
    try:
        r = requests.get(
            BASE_URL,
            params=_params("USERS", "SELECT", callsign.upper(), api_key),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return {"ok": True, "data": r.json()}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "error": str(exc)}
