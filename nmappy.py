import html
import ipaddress
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="NetScan UI",
    page_icon="🔎",
    layout="wide",
)


def is_valid_target(target: str) -> bool:
    """
    Erlaubt IP-Adressen, Hostnamen, CIDR-Netze und einfache Nmap-Target-Syntax.
    Shell-Metazeichen werden blockiert, da subprocess ohne shell ausgeführt wird.
    """
    target = target.strip()

    if not target or len(target) > 255:
        return False

    forbidden = [";", "&", "|", "$", "`", ">", "<", "\n", "\r", "(", ")"]
    if any(char in target for char in forbidden):
        return False

    # Einzelne IP-Adresse
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        pass

    # CIDR-Netz
    try:
        ipaddress.ip_network(target, strict=False)
        return True
    except ValueError:
        pass

    # Hostname, FQDN oder Nmap-ähnliche Hostangabe
    hostname_pattern = r"^[A-Za-z0-9][A-Za-z0-9_.:/,-]*$"
    return bool(re.fullmatch(hostname_pattern, target))


def parse_nmap_xml(xml_path: str) -> tuple[list[dict], list[dict]]:
    hosts = []
    ports = []

    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return hosts, ports

    for host in root.findall("host"):
        address_element = host.find("address")
        status_element = host.find("status")

        address = (
            address_element.attrib.get("addr", "")
            if address_element is not None
            else ""
        )

        status = (
            status_element.attrib.get("state", "")
            if status_element is not None
            else ""
        )

        hostnames = []
        hostnames_element = host.find("hostnames")

        if hostnames_element is not None:
            for hostname in hostnames_element.findall("hostname"):
                name = hostname.attrib.get("name")
                if name:
                    hostnames.append(name)

        hosts.append(
            {
                "Adresse": address,
                "Status": status,
                "Hostnamen": ", ".join(hostnames),
            }
        )

        ports_element = host.find("ports")
        if ports_element is None:
            continue

        for port in ports_element.findall("port"):
            state_element = port.find("state")
            service_element = port.find("service")

            state = (
                state_element.attrib.get("state", "")
                if state_element is not None
                else ""
            )

            service_data = {
                "name": "",
                "product": "",
                "version": "",
                "extrainfo": "",
            }

            if service_element is not None:
                for key in service_data:
                    service_data[key] = service_element.attrib.get(key, "")

            ports.append(
                {
                    "Host": address,
                    "Protokoll": port.attrib.get("protocol", ""),
                    "Port": port.attrib.get("portid", ""),
                    "Status": state,
                    "Dienst": service_data["name"],
                    "Produkt": service_data["product"],
                    "Version": service_data["version"],
                    "Zusatzinfo": service_data["extrainfo"],
                }
            )

    return hosts, ports


def run_nmap(
    target: str,
    ports: str,
    scan_type: str,
    version_detection: bool,
    os_detection: bool,
    no_ping: bool,
    extra_args: list[str],
):
    with tempfile.NamedTemporaryFile(
        suffix=".xml",
        delete=False,
    ) as temp_file:
        xml_path = temp_file.name

    command = [
        "nmap",
        "-oX",
        xml_path,
        "--stats-every",
        "5s",
    ]

    if scan_type == "Stealth-/SYN-Scan":
        command.append("-sS")
    elif scan_type == "TCP-Connect-Scan":
        command.append("-sT")
    elif scan_type == "UDP-Scan":
        command.append("-sU")

    if ports.strip():
        command.extend(["-p", ports.strip()])

    if version_detection:
        command.append("-sV")

    if os_detection:
        command.append("-O")

    if no_ping:
        command.append("-Pn")

    command.extend(extra_args)
    command.append(target)

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except FileNotFoundError:
        return None, None, "Nmap wurde nicht gefunden. Bitte installiere Nmap und prüfe den PATH."
    except subprocess.TimeoutExpired:
        return None, None, "Der Scan wurde wegen eines Timeouts beendet."
    except Exception as error:
        return None, None, f"Fehler beim Starten des Scans: {error}"

    hosts, ports_result = parse_nmap_xml(xml_path)

    try:
        Path(xml_path).unlink(missing_ok=True)
    except OSError:
        pass

    return (
        hosts,
        ports_result,
        process.stderr.strip(),
        command,
        process.returncode,
    )


st.title("🔎 NetScan UI")
st.caption("Grafische Nmap-Oberfläche für autorisierte Sicherheitsprüfungen")

with st.sidebar:
    st.header("Scan-Konfiguration")

    target = st.text_input(
        "Ziel",
        placeholder="z. B. 192.168.1.10 oder scanme.nmap.org",
    )

    ports = st.text_input(
        "Ports",
        value="1-1024",
        help="Beispiele: 22,80,443 oder 1-1024 oder T:22,80,U:53",
    )

    scan_type = st.selectbox(
        "Scan-Typ",
        [
            "TCP-Connect-Scan",
            "Stealth-/SYN-Scan",
            "UDP-Scan",
        ],
    )

    version_detection = st.checkbox(
        "Service- und Versionserkennung",
        value=True,
    )

    os_detection = st.checkbox(
        "Betriebssystemerkennung",
        value=False,
        help="Kann Administratorrechte benötigen.",
    )

    no_ping = st.checkbox(
        "Host Discovery überspringen (-Pn)",
        value=False,
    )

    st.subheader("Zusätzliche Optionen")

    timing = st.selectbox(
        "Timing",
        ["Standard", "-T2", "-T3", "-T4"],
        index=0,
    )

    extra_args = []

    if timing != "Standard":
        extra_args.append(timing)

    show_command = st.checkbox(
        "Ausgeführten Nmap-Befehl anzeigen",
        value=True,
    )

    start_scan = st.button(
        "▶ Scan starten",
        type="primary",
        use_container_width=True,
    )

if start_scan:
    if not is_valid_target(target):
        st.error("Bitte gib ein gültiges Ziel ein.")
        st.stop()

    if not ports.strip():
        st.error("Bitte gib mindestens einen Port oder Portbereich an.")
        st.stop()

    with st.spinner("Scan läuft …"):
        result = run_nmap(
            target=target,
            ports=ports,
            scan_type=scan_type,
            version_detection=version_detection,
            os_detection=os_detection,
            no_ping=no_ping,
            extra_args=extra_args,
        )

    hosts, ports_result, error_text, command, return_code = result

    if hosts is None:
        st.error(error_text)
        st.stop()

    if show_command:
        st.code(" ".join(command), language="bash")

    if error_text:
        st.warning(error_text)

    if return_code != 0 and not hosts and not ports_result:
        st.error(f"Nmap wurde mit dem Exit-Code {return_code} beendet.")
        st.stop()

    st.success("Scan abgeschlossen.")

    tab_hosts, tab_ports, tab_raw = st.tabs(
        ["Hosts", "Ports und Dienste", "Rohdaten"]
    )

    with tab_hosts:
        if hosts:
            st.dataframe(
                pd.DataFrame(hosts),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Keine Hosts gefunden.")

    with tab_ports:
        if ports_result:
            dataframe = pd.DataFrame(ports_result)

            open_ports = dataframe[
                dataframe["Status"].isin(["open", "open|filtered"])
            ]

            st.metric("Gefundene Ports", len(dataframe))
            st.metric("Offene oder möglicherweise offene Ports", len(open_ports))

            st.dataframe(
                dataframe,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Keine Portinformationen gefunden.")

    with tab_raw:
        st.info(
            "Die Rohdaten werden intern im XML-Format verarbeitet. "
            "Für eine ausführliche Terminalausgabe kann der Befehl oben verwendet werden."
        )

else:
    st.info(
        "Konfiguriere links einen Scan und klicke anschließend auf "
        "„Scan starten“."
    )

st.markdown(
    """
    <small>
    Verwende diese Anwendung nur gegen eigene Systeme oder Ziele,
    für die eine ausdrückliche Genehmigung vorliegt.
    </small>
    """,
    unsafe_allow_html=True,
)
