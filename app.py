import requests
import xml.etree.ElementTree as ET
import socket
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ============================================
# Configuration (example placeholders — edit!)
# ============================================
# Scales list: (Display Name, XML endpoint URL)
SCALES = [
    ("Scale 1 (Main Line)", "http://192.168.1.15/xml"),
    ("Scale 2",             "http://192.168.1.16/xml"),
    ("Scale 3",             "http://192.168.1.17/xml"),
]
SCALE_MAP = {name: url for name, url in SCALES}
URL = SCALES[0][1]

# Printers list: (Display Name, IP)
# Port 9100 is typical for Zebra/RAW socket printing.
PRINTERS = [
    ("Printer 1 (192.168.1.5)", "192.168.1.5"),
    ("Printer 2 (192.168.1.6)", "192.168.1.6"),
    ("Printer 3 (192.168.1.7)", "192.168.1.7"),
    ("Printer 4 (192.168.1.8)", "192.168.1.8"),
]
PRN_MAP = {name: ip for name, ip in PRINTERS}
PRINTER_PORT = 9100

# Last measurement (used to populate ZPL)
last_data = {
    "net": "-", "gross": "-", "tare": "-",
    "serial": "-", "ticket": "-"
}

# Will be assigned after UI is created
status_var = None

# ============================================
# Helpers
# ============================================
def send_to_printer(ip: str, port: int, zpl: str) -> None:
    """Send ZPL to a network thermal printer via raw socket."""
    try:
        with socket.create_connection((ip, port), timeout=5) as s:
            # ^CI28 in the ZPL switches printer to UTF-8; we still send UTF-8.
            s.sendall(zpl.encode("utf-8"))
        if status_var:
            status_var.set(f"[OK] {ip}:{port} → ZPL sent.")
    except Exception as e:
        if status_var:
            status_var.set(f"[Error] {ip}:{port} → {e}")

def sanitize_for_code128(s: str) -> str:
    """Return an alphanumeric-only string (safe for Code128)."""
    return "".join(ch for ch in s if ch.isalnum())

def choose_barcode_value() -> str:
    """
    Prefer Ticket No → Serial No → timestamp.
    Filter to alphanumeric for Code128 safety.
    """
    candidates = [last_data.get("ticket", "-"), last_data.get("serial", "-"), ""]
    for c in candidates:
        if c and c.strip() and c != "-" and c.upper() != "ERROR":
            bc = sanitize_for_code128(c)
            if bc:
                return bc
    return datetime.now().strftime("%Y%m%d%H%M%S")

# ============================================
# Poll scale
# ============================================
def poll_scale():
    """Fetch XML from the selected scale and display the latest weights."""
    global URL
    try:
        response = requests.get(URL, timeout=2)
        if response.status_code == 200:
            root_xml = ET.fromstring(response.text)

            # Expected XML tags: net, brut, dara, serino, fisno
            net   = (root_xml.findtext("net", "ERROR") or "").strip()
            gross = (root_xml.findtext("brut", "ERROR") or "").strip()
            tare  = (root_xml.findtext("dara", "ERROR") or "").strip()
            serial = (root_xml.findtext("serino", "-") or "").strip()
            ticket = (root_xml.findtext("fisno", "-") or "").strip()

            net_label.config(text=f"Net: {net}")
            gross_label.config(text=f"Gross: {gross}")
            tare_label.config(text=f"Tare: {tare}")

            last_data.update({
                "net": net, "gross": gross, "tare": tare,
                "serial": serial, "ticket": ticket
            })

            listbox.insert(
                tk.END,
                f"READ | Net:{net} | Gross:{gross} | Tare:{tare} | Serial:{serial} | Ticket:{ticket}"
            )
        else:
            net_label.config(text="HTTP Error")
    except Exception as e:
        net_label.config(text=f"Error: {e}")

def on_scale_change(event=None):
    """When the scale combobox changes, update the base URL."""
    global URL
    selected_name = scale_var.get()
    URL = SCALE_MAP.get(selected_name, URL)
    selected_label.config(text=f"Selected Scale: {selected_name}  →  {URL}")

# ============================================
# Printing tab helpers
# ============================================
DEFAULT_ZPL = """^XA
^CI28
^PW800
^LL560
^CF0,50
^FO100,200^FDTEST LABEL PY^FS
^XZ
"""

def fill_test_zpl():
    zpl_text.delete("1.0", tk.END)
    zpl_text.insert(tk.END, DEFAULT_ZPL)

def fill_from_last_data_plain():
    # Plain text label (no barcode)
    zpl_from_data = f"""^XA
^CI28
^PW800
^LL560
^CF0,40
^FO40,40^FDNet: {last_data['net']}^FS
^FO40,100^FDGross: {last_data['gross']}^FS
^FO40,160^FDTare: {last_data['tare']}^FS
^FO40,220^FDSerial: {last_data['serial']}^FS
^FO40,280^FDTicket: {last_data['ticket']}^FS
^XZ
"""
    zpl_text.delete("1.0", tk.END)
    zpl_text.insert(tk.END, zpl_from_data)

def fill_from_last_data_barcode():
    # Label with Code128 barcode
    barcode_val = choose_barcode_value()
    zpl_from_data = f"""^XA
^CI28
^PW800
^LL560
^CF0,36
^FO40,30^FDNet: {last_data['net']}^FS
^FO40,80^FDGross: {last_data['gross']}^FS
^FO40,130^FDTare: {last_data['tare']}^FS
^FO40,180^FDSerial: {last_data['serial']}^FS
^FO40,230^FDTicket: {last_data['ticket']}^FS

^BY2,3,140
^FO60,290^BCN,140,Y,N,N
^FD{barcode_val}^FS

^FO60,445^A0N,28,28^FD{barcode_val}^FS
^XZ
"""
    zpl_text.delete("1.0", tk.END)
    zpl_text.insert(tk.END, zpl_from_data)

def print_current_zpl():
    name = printer_var.get()
    ip = PRN_MAP.get(name)
    if not ip:
        messagebox.showwarning("Warning", "Please select a printer.")
        return
    zpl = zpl_text.get("1.0", tk.END).strip()
    if not zpl:
        messagebox.showwarning("Warning", "ZPL area is empty.")
        return
    send_to_printer(ip, PRINTER_PORT, zpl)

def quick_print_printer1_barcode():
    """
    Quick print: send the last measurement + barcode
    directly to the first printer in the list.
    """
    if not PRINTERS:
        messagebox.showwarning("Warning", "No printers configured.")
        return
    ip = PRINTERS[0][1]
    barcode_val = choose_barcode_value()
    zpl = f"""^XA
^CI28
^PW800
^LL560
^CF0,36
^FO40,30^FDNet: {last_data['net']}^FS
^FO40,80^FDGross: {last_data['gross']}^FS
^FO40,130^FDTare: {last_data['tare']}^FS
^FO40,180^FDSerial: {last_data['serial']}^FS
^FO40,230^FDTicket: {last_data['ticket']}^FS

^BY2,3,140
^FO60,290^BCN,140,Y,N,N
^FD{barcode_val}^FS

^FO60,445^A0N,28,28^FD{barcode_val}^FS
^XZ
"""
    send_to_printer(ip, PRINTER_PORT, zpl)

# ============================================
# Tkinter UI
# ============================================
root = tk.Tk()
root.title("ScaleIoT — HTTP Scale Reader & ZPL Printer")
root.geometry("820x660")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# -------- TAB 1: Scale ----------
tab_scale = ttk.Frame(notebook)
notebook.add(tab_scale, text="Scale")

title = tk.Label(tab_scale, text="Scale → Read → Preview", font=("Arial", 16, "bold"))
title.pack(pady=8)

select_frame = ttk.LabelFrame(tab_scale, text="Scale Selection")
select_frame.pack(fill="x", padx=10, pady=8)

tk.Label(select_frame, text="Scale:").pack(side="left", padx=(10, 6), pady=8)

scale_var = tk.StringVar(value=SCALES[0][0])
scale_combo = ttk.Combobox(
    select_frame,
    textvariable=scale_var,
    values=[name for name, _ in SCALES],
    state="readonly",
    width=28
)
scale_combo.pack(side="left", padx=6, pady=8)
scale_combo.bind("<<ComboboxSelected>>", on_scale_change)

selected_label = tk.Label(select_frame, text=f"Selected Scale: {SCALES[0][0]}  →  {URL}", fg="#444")
selected_label.pack(side="left", padx=10)

# Measurements
net_label = tk.Label(tab_scale, text="Net: -", font=("Arial", 14))
net_label.pack()
gross_label = tk.Label(tab_scale, text="Gross: -", font=("Arial", 14))
gross_label.pack()
tare_label = tk.Label(tab_scale, text="Tare: -", font=("Arial", 14))
tare_label.pack(pady=8)

# "+" button to poll once
plus_btn = tk.Button(tab_scale, text="+", font=("Arial", 16, "bold"), width=4, command=poll_scale)
plus_btn.pack(pady=8)

# History list
listbox = tk.Listbox(tab_scale, width=100, height=14)
listbox.pack(padx=10, pady=10, fill="both", expand=True)

# -------- TAB 2: Printing ----------
tab_print = ttk.Frame(notebook)
notebook.add(tab_print, text="Printing")

prn_frame = ttk.LabelFrame(tab_print, text="Printer Selection")
prn_frame.pack(fill="x", padx=10, pady=(12, 6))

tk.Label(prn_frame, text="Printer:").pack(side="left", padx=(10, 6), pady=8)
printer_var = tk.StringVar(value=PRINTERS[0][0] if PRINTERS else "")
printer_combo = ttk.Combobox(
    prn_frame,
    textvariable=printer_var,
    values=[name for name, _ in PRINTERS],
    state="readonly",
    width=30
)
printer_combo.pack(side="left", padx=6, pady=8)

btns_frame = ttk.Frame(tab_print)
btns_frame.pack(fill="x", padx=10, pady=6)

btn_test = ttk.Button(btns_frame, text="Load TEST ZPL", command=fill_test_zpl)
btn_test.pack(side="left", padx=4)

btn_from_data_plain = ttk.Button(btns_frame, text="Last Measurement (Plain)", command=fill_from_last_data_plain)
btn_from_data_plain.pack(side="left", padx=4)

btn_from_data_bar = ttk.Button(btns_frame, text="Last Measurement + BARCODE", command=fill_from_last_data_barcode)
btn_from_data_bar.pack(side="left", padx=4)

btn_print = ttk.Button(btns_frame, text="Print to Selected Printer", command=print_current_zpl)
btn_print.pack(side="right", padx=4)

btn_quick = ttk.Button(btns_frame, text="Quick: Print to Printer 1 (Barcode)", command=quick_print_printer1_barcode)
btn_quick.pack(side="right", padx=8)

# ZPL editor
zpl_frame = ttk.LabelFrame(tab_print, text="ZPL Content")
zpl_frame.pack(fill="both", expand=True, padx=10, pady=8)

zpl_text = tk.Text(zpl_frame, height=18, wrap="none")
zpl_text.pack(fill="both", expand=True, padx=6, pady=6)
zpl_text.insert(tk.END, DEFAULT_ZPL)

# Status bar
status_var = tk.StringVar(value="Ready.")
status_bar = ttk.Label(root, textvariable=status_var, anchor="w")
status_bar.pack(fill="x", padx=8, pady=(0, 4))

root.mainloop()
