#!/usr/bin/env python3
"""Find Roku devices on the local network.

Uses SSDP (the discovery protocol Roku devices answer to), then queries each
device's External Control Protocol (ECP) on port 8060 for its name and model.

Usage:  python3 find_roku.py [--timeout SECONDS]
Requires only the Python 3 standard library. Run it on a computer connected
to the same Wi-Fi/LAN as the Roku.
"""
import argparse
import socket
import time
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

SSDP_ADDR = ("239.255.255.250", 1900)
SEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    "Host: 239.255.255.250:1900\r\n"
    'Man: "ssdp:discover"\r\n'
    "ST: roku:ecp\r\n"
    "MX: 3\r\n\r\n"
).encode()


def discover(timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(0.5)
    for _ in range(3):
        sock.sendto(SEARCH, SSDP_ADDR)
    found = {}
    end = time.time() + timeout
    while time.time() < end:
        try:
            data, _addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        headers = {}
        for line in data.decode(errors="replace").split("\r\n")[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        loc = headers.get("location")
        if loc and "roku" in (headers.get("st", "") + headers.get("server", "")).lower():
            found[loc.rstrip("/") + "/"] = headers.get("usn", "")
    sock.close()
    return found


def device_info(base):
    try:
        with urllib.request.urlopen(base + "query/device-info", timeout=3) as r:
            root = ET.fromstring(r.read())
        get = lambda tag: (root.findtext(tag) or "").strip()
        return {
            "name": get("user-device-name") or get("friendly-device-name"),
            "model": f"{get('model-name')} ({get('model-number')})".strip(" ()"),
            "serial": get("serial-number"),
            "is_tv": get("is-tv"),
            "power": get("power-mode"),
            "software": get("software-version"),
        }
    except Exception as e:  # device reachable via SSDP but ECP query failed
        return {"error": str(e)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()

    print(f"Searching for Roku devices for {args.timeout:.0f}s...")
    devices = discover(args.timeout)
    if not devices:
        print("No Roku devices found. Check that this computer is on the same "
              "network as the Roku, and that the Roku is powered on.")
        return
    for base in sorted(devices):
        ip = urlparse(base).hostname
        info = device_info(base)
        print(f"\nRoku at {ip}  ({base})")
        for k, v in info.items():
            if v:
                print(f"  {k:9}: {v}")


if __name__ == "__main__":
    main()
