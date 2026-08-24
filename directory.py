import csv
import io
import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Website Directory Scanner",
    page_icon="🔎",
    layout="wide",
)


DEFAULT_WORDLIST = """admin
administrator
api
assets
backup
config
css
downloads
images
include
js
login
old
private
robots.txt
sitemap.xml
test
uploads
wp-admin
"""


def normalize_target(target: str) -> str:
    target = target.strip()

    if not target:
        raise ValueError("Bitte eine Domain oder URL eingeben.")

    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    parsed = urlparse(target)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Ungültige URL. Beispiel: https://example.com")

    if parsed.username or parsed.password:
        raise ValueError("Benutzername und Passwort in URLs sind nicht erlaubt.")

    return target.rstrip("/") + "/"


def is_public_host(hostname: str) -> bool:
    """
    Verhindert standardmäßig Scans gegen lokale/private Ziele.
    Dies ist ein zusätzlicher Schutz gegen versehentliche SSRF-Ziele.
    """
    if not hostname:
        return False

    try:
        addresses = socket.getaddrinfo(hostname, None)
        ips = {item[4][0] for item in addresses}

        for ip in ips:
            parsed_ip = ipaddress.ip_address(ip)

            if (
                parsed_ip.is_private
                or parsed_ip.is_loopback
                or parsed_ip.is_link_local
                or parsed_ip.is_multicast
                or parsed_ip.is_reserved
            ):
                return False

        return True

    except socket.gaierror:
        return False


def parse_wordlist(raw_wordlist: str) -> list[str]:
    entries = []

    for line in raw_wordlist.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        # Führende Slashes entfernen, damit urljoin sauber arbeitet
        entries.append(line.lstrip("/"))

    # Duplikate entfernen, Reihenfolge beibehalten
    return list(dict.fromkeys(entries))


def scan_path(
    session: requests.Session,
    base_url: str,
    path: str,
    timeout: float,
    follow_redirects: bool,
    delay: float,
) -> dict:
    target_url = urljoin(base_url, path)

    start = time.perf_counter()

    try:
        response = session.get(
            target_url,
            timeout=timeout,
            allow_redirects=follow_redirects,
            headers={
                "User-Agent": "Authorized-Directory-Scanner/1.0",
                "Accept": "*/*",
            },
        )

        elapsed_ms = round((time.perf_counter() - start) * 1000)

        result = {
            "Pfad": path,
            "URL": target_url,
            "Status": response.status_code,
            "Größe": len(response.content),
            "Dauer (ms)": elapsed_ms,
            "Weiterleitung": response.url if response.url != target_url else "",
            "Fehler": "",
        }

    except requests.RequestException as exc:
        result = {
            "Pfad": path,
            "URL": target_url,
            "Status": None,
            "Größe": 0,
            "Dauer (ms)": None,
            "Weiterleitung": "",
            "Fehler": str(exc),
        }

    # Delay pro Worker; bei Threads ist der effektive Gesamtdurchsatz höher.
    # Für strikte Limits wird standardmäßig nur ein Worker verwendet.
    if delay > 0:
        time.sleep(delay)

    return result


def run_scan(
    base_url: str,
    paths: list[str],
    requests_per_second: float,
    timeout: float,
    follow_redirects: bool,
    max_workers: int,
    progress_placeholder,
    status_placeholder,
) -> list[dict]:
    session = requests.Session()

    # Der Delay wird aus dem gewünschten Limit berechnet.
    delay = 1 / requests_per_second if requests_per_second > 0 else 0

    # Bei mehreren Workern wird der theoretische Gesamtdurchsatz höher.
    # Deshalb wird bei parallelen Requests vorsichtshalber gedrosselt.
    if max_workers > 1:
        delay = max(delay, max_workers / requests_per_second)

    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                scan_path,
                session,
                base_url,
                path,
                timeout,
                follow_redirects,
                delay,
            )
            for path in paths
        ]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            completed += 1
            progress_placeholder.progress(completed / len(paths))
            status_placeholder.write(
                f"Geprüft: {completed}/{len(paths)} – zuletzt: `{result['Pfad']}`"
            )

    return results


def results_to_csv(results: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "Pfad",
            "URL",
            "Status",
            "Größe",
            "Dauer (ms)",
            "Weiterleitung",
            "Fehler",
        ],
    )

    writer.writeheader()
    writer.writerows(results)

    return buffer.getvalue().encode("utf-8")


st.title("🔎 Website Directory Scanner")
st.caption("Für autorisierte Tests und eigene Systeme")

with st.sidebar:
    st.header("Scan-Optionen")

    target = st.text_input(
        "Domain oder URL",
        placeholder="https://example.com",
    )

    requests_per_second = st.slider(
        "Rate Limit – Requests pro Sekunde",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1,
        help="Niedrige Werte reduzieren die Belastung des Zielsystems.",
    )

    timeout = st.number_input(
        "Timeout pro Request in Sekunden",
        min_value=1.0,
        max_value=60.0,
        value=10.0,
        step=1.0,
    )

    follow_redirects = st.checkbox(
        "Weiterleitungen folgen",
        value=False,
    )

    max_workers = st.select_slider(
        "Parallele Worker",
        options=[1, 2, 3],
        value=1,
        help="Ein Worker ist am schonendsten und entspricht einem einfachen Rate Limit.",
    )

    st.divider()

    show_status_codes = st.multiselect(
        "Anzeigen: HTTP-Statuscodes",
        options=[200, 204, 301, 302, 307, 308, 401, 403, 404, 429, 500],
        default=[200, 204, 301, 302, 307, 308, 401, 403],
    )

st.write(
    "Gib eine eigene Wordlist ein. Jeder Eintrag wird relativ zur angegebenen "
    "Domain geprüft."
)

wordlist_text = st.text_area(
    "Wordlist",
    value=DEFAULT_WORDLIST,
    height=280,
    placeholder="admin\napi\nbackup\nrobots.txt",
)

col1, col2 = st.columns([1, 3])

with col1:
    start_scan = st.button(
        "Scan starten",
        type="primary",
        use_container_width=True,
    )

with col2:
    st.info(
        "Der Scanner sendet standardmäßig höchstens wenige Requests pro Sekunde "
        "und verwendet einen klar erkennbaren User-Agent."
    )

if start_scan:
    try:
        base_url = normalize_target(target)
        parsed_target = urlparse(base_url)

        if not is_public_host(parsed_target.hostname):
            st.error(
                "Das Ziel konnte nicht als öffentliche Domain bestätigt werden. "
                "Lokale und private IP-Adressen werden standardmäßig blockiert."
            )
            st.stop()

        paths = parse_wordlist(wordlist_text)

        if not paths:
            st.error("Die Wordlist enthält keine gültigen Einträge.")
            st.stop()

        if len(paths) > 5000:
            st.error(
                "Die Wordlist ist auf 5.000 Einträge begrenzt, um unbeabsichtigte "
                "Belastung zu vermeiden."
            )
            st.stop()

        st.subheader(f"Scan von `{base_url}`")
        st.write(f"{len(paths)} Pfade werden mit maximal {requests_per_second} RPS geprüft.")

        progress = st.progress(0)
        scan_status = st.empty()

        started_at = time.perf_counter()

        results = run_scan(
            base_url=base_url,
            paths=paths,
            requests_per_second=requests_per_second,
            timeout=timeout,
            follow_redirects=follow_redirects,
            max_workers=max_workers,
            progress_placeholder=progress,
            status_placeholder=scan_status,
        )

        elapsed = round(time.perf_counter() - started_at, 2)

        # Nach Pfad sortieren
        results.sort(key=lambda row: row["Pfad"].lower())

        st.success(f"Scan abgeschlossen: {len(results)} Pfade in {elapsed} Sekunden.")

        dataframe = pd.DataFrame(results)

        visible_results = dataframe[
            dataframe["Status"].isin(show_status_codes)
            | dataframe["Status"].isna()
        ]

        metric1, metric2, metric3 = st.columns(3)

        with metric1:
            st.metric("Gefundene Antworten", len(visible_results))

        with metric2:
            st.metric(
                "Erfolgreich",
                int(dataframe["Status"].isin([200, 204]).sum()),
            )

        with metric3:
            st.metric(
                "Fehler/Timeouts",
                int(dataframe["Status"].isna().sum()),
            )

        st.dataframe(
            visible_results,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            label="Ergebnisse als CSV herunterladen",
            data=results_to_csv(results),
            file_name="directory_scan_results.csv",
            mime="text/csv",
        )

    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unerwarteter Fehler: {exc}")
