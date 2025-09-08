# ScaleIoT Labeler

IoT-friendly desktop tool to read weights from HTTP-exposed scales (XML) and print ZPL labels (with optional Code128 barcodes) to network thermal printers over RAW 9100.

> **Note:** All IPs and names are placeholders. Replace them with your local values.

---

## Features

- **Multiple IoT scales**: select from a dropdown; each is an HTTP XML endpoint  
- **One-click read** of latest measurement (Net / Gross / Tare)  
- **Built-in ZPL editor**:
  - Load **Test ZPL**
  - Build ZPL from **last measurement (plain)**
  - Build ZPL from **last measurement + Code128 barcode**
- **Network printing** via socket (**RAW 9100**)  
- **Quick Print** shortcut to the first configured printer

---

## Requirements

- Python **3.10+**
- A scale exposing an HTTP XML endpoint like:

  ```xml
  <root>
    <net>12.34</net>
    <brut>13.00</brut>
    <dara>0.66</dara>
    <serino>ABC123</serino>
    <fisno>TK000045</fisno>
  </root>
  ```

- A Zebra-compatible (or RAW-socket capable) network label printer.

Install dependencies:

```bash
pip install requests
```

> `tkinter` ships with most desktop Python installs. On minimal Linux builds, install your OS’s `tk` package.

---

## Run

```bash
python app.py
```

---

## Configuration

Edit the top of `app.py`:

```python
SCALES = [
    ("Scale 1 (Main Line)", "http://192.168.1.15/xml"),
    ("Scale 2",             "http://192.168.1.16/xml"),
    ("Scale 3",             "http://192.168.1.17/xml"),
]

PRINTERS = [
    ("Printer 1 (192.168.1.5)", "192.168.1.5"),
    ("Printer 2 (192.168.1.6)", "192.168.1.6"),
]
PRINTER_PORT = 9100
```

- **Scales:** Each entry points to an **XML** endpoint returning the tags above.  
- **Printers:** Use the **IP** of your network printer. Port **9100** is typical for RAW/ZPL.

---

## Barcode Logic

When building a barcode label, the app picks:
1. **Ticket No** (`fisno`) if available, otherwise
2. **Serial No** (`serino`), otherwise
3. **Current timestamp** (`YYYYMMDDHHMMSS`)

The chosen value is **alphanumeric-filtered** for Code128 safety.

---

## ZPL Notes

- Default ZPL includes `^CI28` (UTF-8).  
- Adjust label geometry via `^PW`, `^LL`, `^FO`, `^BC`.  
- Example barcode label:

  ```zpl
  ^XA
  ^CI28
  ^PW800
  ^LL560
  ^CF0,36
  ^FO40,30^FDNet: 12.34^FS
  ^FO40,80^FDGross: 13.00^FS
  ^FO40,130^FDTare: 0.66^FS
  ^FO40,180^FDSerial: ABC123^FS
  ^FO40,230^FDTicket: TK000045^FS

  ^BY2,3,140
  ^FO60,290^BCN,140,Y,N,N
  ^FDTK000045^FS

  ^FO60,445^A0N,28,28^FDTK000045^FS
  ^XZ
  ```

---

## Security

This is intended for **local/LAN** use. Keep your scales and printers on a trusted network and avoid exposing endpoints publicly.

---

## License

MIT (or choose the license you prefer).
