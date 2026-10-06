import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid
import base64
import textwrap
import streamlit.components.v1 as components

st.set_page_config(page_title="ระบบจัดการห้องเช่า", layout="wide")

DB_FILE = "rental.db"

# ==========================================================
# DAMAGE / LOST / DIRTY ITEM MASTER
# รายการนี้เป็น "รายการกลาง" ไม่ผูกกับประเภทห้อง
# อ้างอิงจากไฟล์รายการทรัพย์สินของใช้ภายในห้องพักที่แนบมา
# ==========================================================
DAMAGE_ITEMS = [
    (1, "ผ้าเช็ดตัวผืนใหญ่ / Large towel", 1200, 500),
    (2, "ผ้าเช็ดตัวผืนเล็ก / Small towel", 1000, 500),
    (3, "ผ้าเช็ดเท้า / Bath towel", 1000, 500),
    (4, "ปลอกดูเว่ใหญ่ / Large duvet sleeve", 1200, 500),
    (5, "ปลอกดูเว่เล็ก / Small duvet sleeve", 1200, 500),
    (6, "หมอนใหญ่ / Big pillow", 1200, 500),
    (7, "หมอนอิงเล็ก / Small pillow", 1000, 500),
    (8, "ปลอกหมอนใหญ่ / Big pillowcase", 1200, 500),
    (9, "ปลอกหมอนอิงเล็ก / Small pillowcase", 1000, 500),
    (10, "ไส้นวมใหญ่ / Large duvet filling", 1200, 700),
    (11, "ไส้นวมเล็ก / Small duvet filling", 1200, 500),
    (12, "ผ้าปูเตียงใหญ่ / Big bed sheet", 1200, 700),
    (13, "ผ้าปูเตียงเล็ก / Small bed sheet", 1200, 500),
    (14, "ฐานเตียง / Bedstead", None, None),
    (15, "ฟูกเตียง / Mattress bed", None, None),
    (16, "ที่รองจาน / Placemat", 100, None),
    (17, "ไม้แขวนเสื้อ / Clothes hanger", 200, None),
    (18, "ไดร์เป่าผม / Hair dryer", 1000, None),
    (19, "โซฟา / Sofa", None, None),
    (20, "ถังขยะ / Rubbish", 200, None),
    (21, "แก้วกาแฟ / Coffee mug", 150, None),
    (22, "จานรองแก้ว / Coasters", 100, None),
    (23, "ช้อนกาแฟ / Coffee spoon", 100, None),
    (24, "รีโมททีวี / TV remote", 200, None),
    (25, "รีโมทแอร์ / Air conditioner remote", 200, None),
    (26, "ตู้เย็น / Fridge", None, None),
    (27, "TV", None, None),
    (28, "โคมไฟ / Lamp", None, None),
    (29, "กาน้ำร้อน / Kettle", None, None),
    (30, 'จานใบเล็ก 8.5" / Plate', 300, None),
    (31, 'จานใบใหญ่ 10.5" / Plate', 250, None),
    (32, "ช้อนส้อม / Fork & Spoon", 100, None),
    (33, "ถ้วยชาม / Bowl", 200, None),
    (34, "แก้วน้ำ / Water glass", 200, None),
    (35, "ชุดมีด / Knife set", 100, None),
    (36, "กระทะ / Saucepan", 500, None),
    (37, "ตะหลิว / Flipper", 150, None),
    (38, "หม้อ / Pot", 500, None),
    (39, "อุปกรณ์ตกแต่งห้อง / Decorations", 500, None),
    (40, "คีย์การ์ด / Keycard", 1000, None),
    (41, "กุญแจ / Key", 500, None),
    (42, "แก้วน้ำอุ่น / Tea cup", 300, None),
    (43, "โต๊ะกลาง / Center table", None, None),
    (44, "โต๊ะกินข้าว / Dining table", None, None),
    (45, "โต๊ะระเบียง / Terrace table", None, None),
    (46, "ไมโครเวฟ / Microwave", None, None),
    (47, "เก้าอี้ / Chair", 1500, None),
    (48, "Android Box", 2500, None),
    (49, "เตาไฟฟ้า / Electric stove", 2000, None),
    (50, "ผ้าม่าน / Curtains", None, None),
    (51, "เตารีดผ้า / Cloth iron", None, None),
    (52, "เตาปิ้งขนมปัง / Toaster", None, None),
]

# ==========================================================
# DATABASE
# ==========================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        building TEXT NOT NULL,
        unit_no TEXT NOT NULL,
        room_type TEXT DEFAULT '-',
        floor TEXT DEFAULT '-',
        UNIQUE(building, unit_no)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS bookings (
        id TEXT PRIMARY KEY,
        building TEXT NOT NULL,
        unit_no TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_type TEXT,
        phone TEXT,
        check_in DATE NOT NULL,
        check_out DATE NOT NULL,
        rent_amount REAL DEFAULT 0,
        deposit REAL DEFAULT 0,
        status TEXT DEFAULT 'booked',
        booking_no TEXT UNIQUE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS checkouts (
        id TEXT PRIMARY KEY,
        booking_no TEXT UNIQUE,
        water_meter_before REAL DEFAULT 0,
        water_meter_after REAL DEFAULT 0,
        water_rate REAL DEFAULT 0,
        elec_meter_before REAL DEFAULT 0,
        elec_meter_after REAL DEFAULT 0,
        elec_rate REAL DEFAULT 0,
        cleaning_fee REAL DEFAULT 0,
        damage_fee REAL DEFAULT 0,
        other_fee REAL DEFAULT 0,
        receipt_no TEXT UNIQUE,
        refund_no TEXT UNIQUE
    )""")

    # รูปมิเตอร์ก่อน/หลัง สำหรับตรวจสอบย้อนหลัง
    photo_columns = {
        "water_meter_before_photo": "BLOB",
        "water_meter_after_photo": "BLOB",
        "elec_meter_before_photo": "BLOB",
        "elec_meter_after_photo": "BLOB",
    }
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(checkouts)").fetchall()}
    for col_name, col_type in photo_columns.items():
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE checkouts ADD COLUMN {col_name} {col_type}")


    # รายการของเสียหาย/สูญหาย/สกปรก เป็นข้อมูลกลาง
    c.execute("""CREATE TABLE IF NOT EXISTS damage_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_no INTEGER UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        damage_price REAL,
        dirty_price REAL,
        active INTEGER DEFAULT 1
    )""")

    # รายการที่ถูกหักเงินจริงในการคืนห้องแต่ละครั้ง
    c.execute("""CREATE TABLE IF NOT EXISTS checkout_damages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checkout_id TEXT NOT NULL,
        booking_no TEXT NOT NULL,
        item_no INTEGER,
        item_name TEXT NOT NULL,
        condition_type TEXT NOT NULL,
        quantity REAL DEFAULT 1,
        unit_price REAL DEFAULT 0,
        amount REAL DEFAULT 0
    )""")

    for item_no, item_name, damage_price, dirty_price in DAMAGE_ITEMS:
        c.execute(
            """INSERT OR IGNORE INTO damage_items
               (item_no, item_name, damage_price, dirty_price, active)
               VALUES (?, ?, ?, ?, 1)""",
            (item_no, item_name, damage_price, dirty_price)
        )

    # รายการรับ/คืนเงินประกัน แยกจากรายการคืนห้อง
    c.execute("""CREATE TABLE IF NOT EXISTS deposit_transactions (
        id TEXT PRIMARY KEY,
        booking_no TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        amount REAL DEFAULT 0,
        doc_no TEXT UNIQUE,
        transaction_date DATE NOT NULL,
        note TEXT DEFAULT ''
    )""")

    palm_rooms = [
        ("Palm", "2104", "2 Bedroom", "1"),
        ("Palm", "2106", "1 Bedroom", "1"),
        ("Palm", "2107", "2 Bedroom", "1"),
        ("Palm", "2108", "2 Bedroom", "1"),
        ("Palm", "2201/2", "1 Bedroom", "2"),
        ("Palm", "2202", "1 Bedroom", "2"),
        ("Palm", "2203", "Studio room", "2"),
        ("Palm", "2205", "2 Bedroom", "2"),
        ("Palm", "2210", "2 Bedroom", "2"),
        ("Palm", "2301/1", "1 Bedroom", "3"),
        ("Palm", "2301/2", "1 Bedroom", "3"),
        ("Palm", "2302", "1 Bedroom", "3"),
        ("Palm", "2304", "2 Bedroom", "3"),
        ("Palm", "2305", "2 Bedroom", "3"),
        ("Palm", "2310", "2 Bedroom", "3"),
        ("Palm", "2601/1", "2 Bedroom", "6"),
        ("Palm", "2601/2", "Studio room", "6"),
    ]

    ark_rooms = [
        ("The Ark", "205", "2 Bedroom", "2"),
        ("The Ark", "209", "2 Bedroom", "2"),
        ("The Ark", "301", "CONTINUOUS", "3"),
        ("The Ark", "302", "CONTINUOUS", "3"),
        ("The Ark", "303", "CONTINUOUS", "3"),
        ("The Ark", "304", "CONTINUOUS", "3"),
        ("The Ark", "305", "CONTINUOUS", "3"),
        ("The Ark", "306", "CONTINUOUS", "3"),
        ("The Ark", "309", "2 Bedroom", "3"),
        ("The Ark", "311", "CONTINUOUS", "3"),
        ("The Ark", "312", "CONTINUOUS", "3"),
        ("The Ark", "313", "CONTINUOUS", "3"),
        ("The Ark", "314", "CONTINUOUS", "3"),
        ("The Ark", "315", "CONTINUOUS", "3"),
        ("The Ark", "316", "CONTINUOUS", "3"),
        ("The Ark", "401", "CONTINUOUS", "4"),
        ("The Ark", "402", "CONTINUOUS", "4"),
        ("The Ark", "403", "CONTINUOUS", "4"),
        ("The Ark", "404", "CONTINUOUS", "4"),
        ("The Ark", "405", "2 Bedroom", "4"),
        ("The Ark", "407", "2 Bedroom", "4"),
        ("The Ark", "408", "2 Bedroom", "4"),
        ("The Ark", "410", "2 Bedroom", "4"),
        ("The Ark", "503", "CONTINUOUS", "5"),
        ("The Ark", "504", "CONTINUOUS", "5"),
        ("The Ark", "505", "2 Bedroom", "5"),
        ("The Ark", "506", "2 Bedroom", "5"),
        ("The Ark", "601", "2 Bedroom", "6"),
        ("The Ark", "610", "1 Bedroom", "6"),
    ]

    # เพิ่มห้องใหม่ และอัปเดตประเภท/ชั้นของห้องที่มีอยู่แล้ว
    # เพื่อให้ข้อมูลในฐานข้อมูลตรงกับรายการห้องที่กำหนดไว้
    # ลบห้องที่ยกเลิกออกจากฐานข้อมูลเดิมด้วย
    c.execute("DELETE FROM rooms WHERE building = ? AND unit_no = ?", ("Palm", "2308"))

    for row in palm_rooms + ark_rooms:
        try:
            c.execute(
                "INSERT OR IGNORE INTO rooms (building, unit_no, room_type, floor) VALUES (?, ?, ?, ?)",
                row,
            )
            c.execute(
                "UPDATE rooms SET room_type = ?, floor = ? WHERE building = ? AND unit_no = ?",
                (row[2], row[3], row[0], row[1]),
            )
        except sqlite3.Error:
            pass

    conn.commit()
    conn.close()


def get_next_booking_no():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT booking_no FROM bookings WHERE booking_no LIKE ? ORDER BY booking_no DESC",
        (f"{prefix}-%",),
    )
    res = c.fetchone()
    conn.close()
    seq = int(res[0].split("-")[-1]) + 1 if res else 1
    return f"{prefix}-{seq:03d}"


def get_next_receipt_no():
    prefix = f"RE-{datetime.now().strftime('%y%m')}-"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT receipt_no FROM checkouts WHERE receipt_no LIKE ? ORDER BY receipt_no DESC",
        (f"{prefix}%",),
    )
    res = c.fetchone()
    conn.close()
    seq = int(res[0].split("-")[-1]) + 1 if res else 1
    return f"{prefix}{seq:03d}"


def get_next_refund_no():
    prefix = f"RF-{datetime.now().strftime('%y%m')}-"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT refund_no FROM checkouts WHERE refund_no LIKE ? ORDER BY refund_no DESC",
        (f"{prefix}%",),
    )
    res = c.fetchone()
    conn.close()
    seq = int(res[0].split("-")[-1]) + 1 if res else 1
    return f"{prefix}{seq:03d}"


def get_next_deposit_receipt_no():
    prefix = f"DP-{datetime.now().strftime('%y%m')}-"
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(
        "SELECT doc_no FROM deposit_transactions WHERE doc_no LIKE ? ORDER BY doc_no DESC",
        (f"{prefix}%",),
    ).fetchone()
    conn.close()
    seq = int(row[0].split("-")[-1]) + 1 if row else 1
    return f"{prefix}{seq:03d}"


def get_next_deposit_refund_no():
    prefix = f"DR-{datetime.now().strftime('%y%m')}-"
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(
        "SELECT doc_no FROM deposit_transactions WHERE doc_no LIKE ? ORDER BY doc_no DESC",
        (f"{prefix}%",),
    ).fetchone()
    conn.close()
    seq = int(row[0].split("-")[-1]) + 1 if row else 1
    return f"{prefix}{seq:03d}"


def generate_deposit_document_html(data, doc_type):
    title = "ใบรับเงินประกัน" if doc_type == "receive" else "ใบคืนเงินประกัน"
    amount = float(data.get("amount", 0) or 0)
    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>{title}</title>
    <style>
      @page {{ size:A4; margin:18mm; }}
      body {{ font-family:Arial,sans-serif; background:#fff; color:#222; }}
      .page {{ max-width:720px; margin:20px auto; padding:36px; border:2px solid #17365D; }}
      h1 {{ text-align:center; color:#17365D; margin-bottom:8px; }}
      .sub {{ text-align:center; color:#666; margin-bottom:28px; }}
      table {{ width:100%; border-collapse:collapse; margin-top:18px; }}
      td {{ padding:11px 8px; border-bottom:1px solid #ddd; }}
      td:first-child {{ width:38%; font-weight:bold; }}
      .amount {{ font-size:24px; font-weight:bold; color:#17365D; text-align:right; }}
      .sign {{ margin-top:80px; display:flex; justify-content:space-between; text-align:center; }}
      .print {{ text-align:center; margin:20px 0; }}
      .print button {{ padding:9px 20px; font-size:15px; cursor:pointer; }}
      @media print {{ .print {{ display:none; }} .page {{ border:0; margin:0; }} }}
    </style></head><body>
      <div class="print"><button onclick="window.print()">🖨️ พิมพ์เอกสาร</button></div>
      <div class="page">
        <h1>{title}</h1>
        <div class="sub">เอกสารสำหรับรายการเงินประกันห้องพัก</div>
        <table>
          <tr><td>เลขที่เอกสาร</td><td>{data.get('doc_no','')}</td></tr>
          <tr><td>วันที่</td><td>{data.get('transaction_date','')}</td></tr>
          <tr><td>เลขที่จอง</td><td>{data.get('booking_no','')}</td></tr>
          <tr><td>ตึก / ห้อง</td><td>{data.get('building','')} / {data.get('unit_no','')}</td></tr>
          <tr><td>ชื่อลูกค้า</td><td>{data.get('customer_name','')}</td></tr>
          <tr><td>รายการ</td><td>{title}</td></tr>
          <tr><td>จำนวนเงิน</td><td class="amount">{amount:,.2f} บาท</td></tr>
          <tr><td>หมายเหตุ</td><td>{data.get('note','') or '-'}</td></tr>
        </table>
        <div class="sign">
          <div>ลงชื่อผู้จ่ายเงิน<br><br>....................................</div>
          <div>ลงชื่อผู้รับเงิน<br><br>....................................</div>
        </div>
      </div>
    </body></html>
    """


def image_bytes(uploaded_file):
    if uploaded_file is None:
        return None
    return uploaded_file.getvalue()


def image_data_uri(image_bytes_value, mime_type="image/jpeg"):
    if not image_bytes_value:
        return ""
    b64 = base64.b64encode(image_bytes_value).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def meter_photo_html(label, photo_bytes_value, mime_type="image/jpeg"):
    if not photo_bytes_value:
        return (f"<div style='width:48%;display:inline-block;vertical-align:top;margin:1%;'>"
                f"<b>{label}</b><div style='border:1px dashed #bbb;padding:25px;text-align:center;color:#888;'>ไม่มีรูปแนบ</div></div>")
    src = image_data_uri(photo_bytes_value, mime_type)
    return (f"<div style='width:48%;display:inline-block;vertical-align:top;margin:1%;text-align:center;'>"
            f"<b>{label}</b><br><img src='{src}' style='max-width:100%;max-height:280px;border:1px solid #ccc;margin-top:6px;'></div>")


def generate_receipt_html(data, doc_type):
    today = datetime.now().strftime("%d/%m/%Y")
    unit = data.get("unit_no", "")
    building = data.get("building", "")
    customer_name = data.get("customer_name", "")
    deposit = float(data.get("deposit", 0) or 0)
    booking_no = data.get("booking_no", "")

    w_before = float(data.get("water_meter_before", 0) or 0)
    w_after = float(data.get("water_meter_after", 0) or 0)
    w_rate = float(data.get("water_rate", 0) or 0)
    w_total = max(0, w_after - w_before) * w_rate

    e_before = float(data.get("elec_meter_before", 0) or 0)
    e_after = float(data.get("elec_meter_after", 0) or 0)
    e_rate = float(data.get("elec_rate", 0) or 0)
    e_total = max(0, e_after - e_before) * e_rate

    cleaning_fee = float(data.get("cleaning_fee", 0) or 0)
    damage_fee = float(data.get("damage_fee", 0) or 0)
    other_fee = float(data.get("other_fee", 0) or 0)
    total_all = w_total + e_total + cleaning_fee + damage_fee + other_fee
    refund = deposit - total_all

    damage_rows = data.get("damage_rows", [])

    damage_detail_html = ""
    if damage_rows:
        damage_detail_html += """
        <tr style="background:#f3f4f6;font-weight:bold;">
            <td style="padding:8px;border-bottom:1px solid #ddd;">รายการของเสียหาย/สูญหาย/สกปรก</td>
            <td style="padding:8px;text-align:right;border-bottom:1px solid #ddd;">จำนวนเงิน</td>
        </tr>
        """
        for row in damage_rows:
            condition_label = row.get("condition_type", "")
            qty = float(row.get("quantity", 1) or 1)
            amount = float(row.get("amount", 0) or 0)
            damage_detail_html += f"""
            <tr>
                <td style="padding:7px;border-bottom:1px solid #eee;">
                    {row.get('item_name','')}<br>
                    <span style="font-size:12px;color:#666;">
                        {condition_label} × {qty:g}
                    </span>
                </td>
                <td style="padding:7px;text-align:right;border-bottom:1px solid #eee;">
                    {amount:,.2f} บาท
                </td>
            </tr>
            """

    if doc_type == "receipt":
        title = "ใบเสร็จรับเงิน"
        doc_no = data.get("receipt_no", "")
        rows = f"""
        <tr><td style="padding:10px;border-bottom:1px solid #ddd;">ค่าน้ำ ({w_before:.1f} - {w_after:.1f}) x {w_rate:.2f}</td><td style="text-align:right;padding:10px;border-bottom:1px solid #ddd;">{w_total:.2f} บาท</td></tr>
        <tr><td style="padding:10px;border-bottom:1px solid #ddd;">ค่าไฟ ({e_before:.1f} - {e_after:.1f}) x {e_rate:.2f}</td><td style="text-align:right;padding:10px;border-bottom:1px solid #ddd;">{e_total:.2f} บาท</td></tr>
        <tr><td style="padding:10px;border-bottom:1px solid #ddd;">ค่าทำความสะอาด</td><td style="text-align:right;padding:10px;border-bottom:1px solid #ddd;">{cleaning_fee:.2f} บาท</td></tr>
        {damage_detail_html}
        <tr><td style="padding:10px;border-bottom:1px solid #ddd;">ค่าของเสียหาย/สูญหาย/สกปรก รวม</td><td style="text-align:right;padding:10px;border-bottom:1px solid #ddd;">{damage_fee:.2f} บาท</td></tr>
        <tr><td style="padding:10px;border-bottom:1px solid #ddd;">ค่าอื่นๆ</td><td style="text-align:right;padding:10px;border-bottom:1px solid #ddd;">{other_fee:.2f} บาท</td></tr>
        <tr style="font-weight:bold;font-size:1.1em;"><td style="padding:12px 8px;border-top:2px solid #333;">รวมค่าใช้จ่าย</td><td style="text-align:right;padding:12px 8px;border-top:2px solid #333;">{total_all:.2f} บาท</td></tr>
        <tr><td style="padding:10px;border-bottom:1px solid #ddd;">เงินมัดจำที่รับไว้</td><td style="text-align:right;padding:10px;border-bottom:1px solid #ddd;">{deposit:.2f} บาท</td></tr>
        <tr><td style="padding:10px;border-bottom:1px solid #ddd;">หักเงินมัดจำ</td><td style="text-align:right;padding:10px;border-bottom:1px solid #ddd;">-{min(deposit, total_all):.2f} บาท</td></tr>
        <tr style="font-weight:bold;font-size:1.1em;"><td style="padding:12px 8px;border-top:2px solid #333;">ยอดชำระสุทธิ</td><td style="text-align:right;padding:12px 8px;border-top:2px solid #333;">{max(0, total_all - deposit):.2f} บาท</td></tr>
        {f'<tr style="font-weight:bold;color:#c00000;"><td style="padding:10px;">คืนเงินมัดจำ</td><td style="text-align:right;padding:10px;">{max(0, deposit-total_all):.2f} บาท</td></tr>' if deposit > total_all else ''}
        """
        sign_line = '<p style="text-align:right;margin-top:40px;">ลงชื่อผู้รับเงิน ..............................</p>'
    else:
        # ใบคืนเงินมัดจำ: แสดงเฉพาะ "ยอดที่คืนเงินมัดจำ" ตามที่ผู้ใช้ต้องการ
        # รายละเอียดค่าน้ำ/ค่าไฟ/ค่าทำความสะอาด/ของเสียหายยังคงเก็บในระบบ
        # และใช้คำนวณยอด refund แต่ไม่แสดงในเอกสารฉบับนี้
        title = "ใบคืนเงินมัดจำ"
        doc_no = data.get("refund_no", "")
        refund_amount = max(0, refund)
        rows = f"""
        <tr style="font-weight:bold;font-size:1.15em;">
            <td style="padding:16px 10px;border-top:2px solid #333;border-bottom:2px solid #333;">ยอดคืนเงินมัดจำ</td>
            <td style="text-align:right;padding:16px 10px;border-top:2px solid #333;border-bottom:2px solid #333;">{refund_amount:,.2f} บาท</td>
        </tr>
        """
        sign_line = """<p style="text-align:right;margin-top:55px;">ลงชื่อผู้จ่ายเงิน ..............................</p>
<p style="text-align:right;">ลงชื่อผู้รับเงิน ..............................</p>"""

    water_before_photo = data.get("water_meter_before_photo")
    water_after_photo = data.get("water_meter_after_photo")
    elec_before_photo = data.get("elec_meter_before_photo")
    elec_after_photo = data.get("elec_meter_after_photo")
    meter_photos_html = f"""
    <div style="margin-top:20px;border-top:1px solid #ccc;padding-top:15px;">
        <h3 style="margin-bottom:10px;">หลักฐานรูปมิเตอร์</h3>
        {meter_photo_html("มิเตอร์น้ำ - ก่อนเข้าพัก", water_before_photo)}
        {meter_photo_html("มิเตอร์น้ำ - หลังเข้าพัก", water_after_photo)}
        {meter_photo_html("มิเตอร์ไฟ - ก่อนเข้าพัก", elec_before_photo)}
        {meter_photo_html("มิเตอร์ไฟ - หลังเข้าพัก", elec_after_photo)}
    </div>
    """ if doc_type == "receipt" else ""

    html = f"""
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>{title}</title>
    <style>body{{font-family:sans-serif;background:#fff;}}</style></head>
    <body>
    <div style="border:2px solid #333;padding:30px;max-width:700px;margin:0 auto;background:#fff;">
        <h2 style="text-align:center;margin:0 0 20px 0;">{title}</h2>
        <p style="text-align:right;"><strong>เลขที่จอง:</strong> {booking_no}</p>
        <p style="text-align:right;"><strong>เลขที่เอกสาร:</strong> {doc_no}</p>
        <p style="text-align:right;"><strong>วันที่:</strong> {today}</p>
        <hr style="border:1px solid #ccc;margin:15px 0;">
        <p><strong>ชื่อลูกค้า:</strong> {customer_name}</p>
        <p><strong>ตึก/ห้อง:</strong> {building} / {unit}</p>
        <p><strong>วันที่เข้า:</strong> {data.get('check_in','')} &nbsp;&nbsp; <strong>วันที่คืน:</strong> {data.get('check_out','')}</p>
        <hr style="border:1px solid #ccc;margin:15px 0;">
        <table style="width:100%;border-collapse:collapse;">{rows}</table>
        <hr style="border:1px solid #ccc;margin:20px 0;">
        {meter_photos_html}
        <hr style="border:1px solid #ccc;margin:20px 0;">
        {sign_line}
    </div></body></html>
    """
    return html, doc_no

def get_download_link(html_str, filename):
    b64 = base64.b64encode(html_str.encode("utf-8")).decode()
    return f'<a href="data:text/html;charset=utf-8;base64,{b64}" download="{filename}.html">ดาวน์โหลดเอกสาร</a>'


# ==========================================================
# START APP
# ==========================================================
init_db()

menu = st.sidebar.selectbox(
    "เมนูหลัก",
    [
        "ปฏิทินห้องเช่า",
        "บันทึกจองห้อง",
        "รับเงินประกัน/พิมพ์เอกสาร",
        "คืนเงินประกัน/พิมพ์เอกสาร",
        "คืนห้อง/ออกใบเสร็จ",
        "พิมพ์เอกสาร",
        "รายการจองทั้งหมด",
    ],
)


# ==========================================================
# 1) CALENDAR - NEW DESIGN
# ==========================================================
if menu == "ปฏิทินห้องเช่า":

    st.markdown(
        """
        <style>
        .calendar-title{background:#17365D;color:white;padding:8px 15px;font-size:22px;font-weight:bold;margin-bottom:8px}
        .calendar-wrapper{width:100%;overflow-x:auto;border:1px solid #cbd5e1;background:white}
        .calendar-table{border-collapse:collapse;width:max-content;min-width:100%;table-layout:fixed;font-size:11px}
        .calendar-table th,.calendar-table td{border:1px solid #cbd5e1;padding:0;text-align:center;height:27px}
        .calendar-table th{background:#17365D;color:white;font-weight:bold}
        .calendar-table .room-col{width:75px;min-width:75px;background:#eaf0f7;color:#17365D;font-weight:bold;text-align:left;padding-left:8px}
        .calendar-table .type-col{width:95px;min-width:95px;background:#eaf0f7;color:#17365D;text-align:left;padding-left:8px}
        .calendar-table .date-col{width:31px;min-width:31px}
        .calendar-table .weekend{background:#dfe5ee !important}
        .calendar-table .empty{background:white}
        .calendar-table .booking{font-size:9px;font-weight:bold;color:#17456b;white-space:nowrap;overflow:hidden}
        .calendar-table .today{box-shadow:inset 0 0 0 2px #ff9800}
        .summary-box{border:1px solid #d5dce5;background:#edf2f8;text-align:center;padding:7px 4px;min-height:62px}
        .summary-label{font-size:12px;color:#234;font-weight:bold}
        .summary-value{font-size:22px;font-weight:bold;color:#17365D;margin-top:4px}
        .daily-summary{border-collapse:collapse;width:max-content;min-width:100%;font-size:10px}
        .daily-summary th,.daily-summary td{border:1px solid #cbd5e1;min-width:31px;width:31px;height:22px;text-align:center}
        .daily-summary .label{min-width:170px;width:170px;text-align:left;padding-left:8px;background:#eaf0f7;font-weight:bold;color:#17365D}
        .legend-box{display:flex;flex-wrap:wrap;gap:0;margin-top:8px}
        .legend-item{min-width:150px;padding:7px 12px;border:1px solid white;text-align:center;font-size:11px;font-weight:bold}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="calendar-title">ระบบจองห้องพัก • ปฏิทินภาพรวม</div>',
        unsafe_allow_html=True,
    )

    conn = sqlite3.connect(DB_FILE)
    rooms = pd.read_sql(
        "SELECT building, unit_no, room_type, floor FROM rooms ORDER BY building, CAST(floor AS INTEGER), unit_no",
        conn,
    )
    bookings = pd.read_sql("SELECT * FROM bookings ORDER BY check_in", conn)
    conn.close()

    col1, col2, col3 = st.columns(3)

    with col1:
        building_options = ["ทุกตึก"] + sorted(rooms["building"].dropna().unique().tolist())
        selected_building = st.selectbox(
            "เลือกตึก",
            building_options,
            key="calendar_building"
        )

    with col2:
        today = datetime.today()

        current_be_year = today.year + 543
        year_options = list(range(2560, 2600))

        selected_be_year = st.selectbox(
            "เลือกปี",
            year_options,
            index=year_options.index(current_be_year),
            key="calendar_year",
        )

    with col3:
        thai_months = [
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
            "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
            "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
        ]

        selected_month_number = st.selectbox(
            "เลือกเดือน",
            range(1, 13),
            index=today.month - 1,
            format_func=lambda x: thai_months[x - 1],
            key="calendar_month",
        )

    selected_year = selected_be_year - 543
    selected_month = f"{selected_year:04d}-{selected_month_number:02d}"

    if selected_building != "ทุกตึก":
        rooms_show = rooms[rooms["building"] == selected_building].copy()
    else:
        rooms_show = rooms.copy()

    month_start = pd.to_datetime(selected_month + "-01")
    month_end = month_start + pd.offsets.MonthEnd(1)
    all_days = pd.date_range(month_start, month_end, freq="D")

    if not bookings.empty:
        bookings["check_in"] = pd.to_datetime(bookings["check_in"])
        bookings["check_out"] = pd.to_datetime(bookings["check_out"])
        if selected_building != "ทุกตึก":
            bookings_show = bookings[bookings["building"] == selected_building].copy()
        else:
            bookings_show = bookings.copy()
    else:
        bookings_show = pd.DataFrame(
            columns=["booking_no", "building", "unit_no", "customer_name", "check_in", "check_out", "rent_amount", "status"]
        )

    if not bookings_show.empty:
        month_bookings = bookings_show[
            (bookings_show["check_in"] <= month_end)
            & (bookings_show["check_out"] >= month_start)
        ].copy()
    else:
        month_bookings = bookings_show.copy()

    total_rooms = len(rooms_show)
    booking_count = len(month_bookings)

    today_ts = pd.Timestamp.today().normalize()
    active_today = 0
    if not bookings_show.empty:
        active_today = len(
            bookings_show[
                (bookings_show["check_in"] <= today_ts)
                & (bookings_show["check_out"] >= today_ts)
                & (bookings_show["status"] != "checked_out")
            ]
        )

    checked_out_count = 0 if bookings_show.empty else len(bookings_show[bookings_show["status"] == "checked_out"])
    booked_rooms = 0 if month_bookings.empty else month_bookings["unit_no"].nunique()
    available_rooms = max(0, total_rooms - active_today)

    occupied_days = 0
    for _, b in month_bookings.iterrows():
        s = max(b["check_in"], month_start)
        e = min(b["check_out"], month_end)
        if e >= s:
            occupied_days += (e - s).days + 1

    total_room_days = total_rooms * len(all_days)
    occupancy = occupied_days / total_room_days * 100 if total_room_days else 0

    total_revenue = 0
    if not month_bookings.empty and "rent_amount" in month_bookings.columns:
        total_revenue = pd.to_numeric(month_bookings["rent_amount"], errors="coerce").fillna(0).sum()

    summary_data = [
        ("ห้องทั้งหมด", total_rooms),
        ("จองแล้ว", booked_rooms),
        ("เข้าพักอยู่", active_today),
        ("คืนห้องแล้ว", checked_out_count),
        ("อัตราการเข้าพัก", f"{occupancy:.0f}%"),
        ("ห้องว่าง", available_rooms),
        ("ยอดค่าเช่า (บาท)", f"{total_revenue:,.0f}"),
    ]

    summary_cols = st.columns(7)
    for col, (label, value) in zip(summary_cols, summary_data):
        with col:
            st.markdown(
                f'<div class="summary-box"><div class="summary-label">{label}</div><div class="summary-value">{value}</div></div>',
                unsafe_allow_html=True,
            )

    def get_booking_color(status):
        if status == "booked":
            return "#9DC3E6"
        if status == "checked_out":
            return "#A9D18E"
        if status in ("cancelled", "canceled"):
            return "#E00000"
        if status == "pending":
            return "#FFD966"
        return "#F4B183"

    thai_days = ["จ", "อ", "พ", "พฤ", "ศ", "ส", "อา"]

    html = """
    <div class="calendar-wrapper">
    <table class="calendar-table">
    <thead><tr>
    <th class="room-col">ห้อง</th>
    <th class="type-col">ประเภท</th>
    """

    for d in all_days:
        weekend = "weekend" if d.weekday() >= 5 else ""
        today_class = " today" if d.date() == datetime.today().date() else ""
        html += f'<th class="date-col {weekend}{today_class}"><div style="font-size:9px">{thai_days[d.weekday()]}</div><div style="font-size:11px">{d.day}</div></th>'

    html += "</tr></thead><tbody>"
    current_building = None

    for _, room in rooms_show.iterrows():
        building = room["building"]
        unit = room["unit_no"]
        room_type = room["room_type"]

        if building != current_building:
            current_building = building
            html += f'<tr><td colspan="{2 + len(all_days)}" style="background:#17365D;color:white;text-align:left;font-weight:bold;padding:5px 10px">{building}</td></tr>'

        html += f'<tr><td class="room-col">{unit}</td><td class="type-col">{room_type}</td>'

        room_bookings = bookings_show[
            (bookings_show["building"] == building)
            & (bookings_show["unit_no"] == unit)
        ]

        for d in all_days:
            weekend = d.weekday() >= 5
            bg = "#dfe5ee" if weekend else "#ffffff"
            cell_class = "weekend" if weekend else "empty"
            booking_text = ""
            booking_title = ""

            found = None
            for _, b in room_bookings.iterrows():
                if b["check_in"] <= d <= b["check_out"]:
                    found = b
                    break

            if found is not None:
                bg = get_booking_color(found.get("status", "booked"))
                cell_class = "booking"
                booking_no = str(found.get("booking_no", ""))
                customer = str(found.get("customer_name", ""))
                booking_title = f"{booking_no} - {customer}"
                if d.date() == found["check_in"].date():
                    booking_text = booking_no[-5:] if booking_no else ""

            html += f'<td class="{cell_class}" title="{booking_title}" style="background:{bg};border:1px solid #cbd5e1;height:27px">{booking_text}</td>'

        html += "</tr>"

    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)

    daily_html = '<div class="calendar-wrapper" style="margin-top:0"><table class="daily-summary">'

    daily_html += '<tr><td class="label">จำนวนห้องที่มีผู้เข้าพัก</td>'
    for d in all_days:
        count = 0
        if not bookings_show.empty:
            count = bookings_show[(bookings_show["check_in"] <= d) & (bookings_show["check_out"] >= d)]["unit_no"].nunique()
        daily_html += f"<td>{count}</td>"
    daily_html += "</tr>"

    daily_html += '<tr><td class="label">ห้องว่าง</td>'
    for d in all_days:
        occupied = 0
        if not bookings_show.empty:
            occupied = bookings_show[(bookings_show["check_in"] <= d) & (bookings_show["check_out"] >= d)]["unit_no"].nunique()
        daily_html += f"<td>{max(0, total_rooms - occupied)}</td>"
    daily_html += "</tr>"

    daily_html += '<tr><td class="label">อัตราการเข้าพัก</td>'
    for d in all_days:
        occupied = 0
        if not bookings_show.empty:
            occupied = bookings_show[(bookings_show["check_in"] <= d) & (bookings_show["check_out"] >= d)]["unit_no"].nunique()
        rate = occupied / total_rooms * 100 if total_rooms else 0
        daily_html += f"<td>{rate:.0f}%</td>"
    daily_html += "</tr></table></div>"

    st.markdown(daily_html, unsafe_allow_html=True)

    st.markdown(
        """
        <div style="margin-top:10px;font-weight:bold;color:#17365D">สัญลักษณ์</div>
        <div class="legend-box">
            <div class="legend-item" style="background:#9DC3E6">จองแล้ว</div>
            <div class="legend-item" style="background:#A9D18E">เข้าพัก/คืนแล้ว</div>
            <div class="legend-item" style="background:#FFD966">รอดำเนินการ</div>
            <div class="legend-item" style="background:#D9D9D9">ห้องว่าง</div>
            <div class="legend-item" style="background:#E00000;color:white">ยกเลิก</div>
            <div class="legend-item" style="background:#F4B183">อื่นๆ</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("รายการจองในเดือนนี้")

    if month_bookings.empty:
        st.info("ยังไม่มีรายการจองในเดือนที่เลือก")
    else:
        display = month_bookings.copy()
        display["check_in"] = display["check_in"].dt.strftime("%d/%m/%Y")
        display["check_out"] = display["check_out"].dt.strftime("%d/%m/%Y")
        display = display.rename(
            columns={
                "booking_no": "เลขที่จอง",
                "building": "ตึก",
                "unit_no": "ห้อง",
                "customer_name": "ชื่อลูกค้า",
                "check_in": "วันที่เข้า",
                "check_out": "วันที่คืน",
                "rent_amount": "ค่าเช่า",
                "status": "สถานะ",
            }
        )
        cols = ["เลขที่จอง", "ตึก", "ห้อง", "ชื่อลูกค้า", "วันที่เข้า", "วันที่คืน", "ค่าเช่า", "สถานะ"]
        cols = [c for c in cols if c in display.columns]
        st.dataframe(display[cols], use_container_width=True, hide_index=True)


# ==========================================================
# 2) BOOKING
# ==========================================================
if menu == "บันทึกจองห้อง":
    st.header("บันทึกจองห้อง")
    conn = sqlite3.connect(DB_FILE)
    rooms = pd.read_sql("SELECT building, unit_no FROM rooms ORDER BY building, unit_no", conn)
    conn.close()

    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            building_options = sorted(rooms["building"].dropna().unique().tolist())
            bld = st.selectbox(
                "เลือกตึก",
                building_options,
                key="booking_building",
            )

            # ดึงเฉพาะเลขห้องของตึกที่เลือก และใช้ key แยกตามตึก
            # เพื่อไม่ให้เลขห้องของตึกก่อนหน้าค้างมาแสดง
            units = (
                rooms.loc[rooms["building"] == bld, "unit_no"]
                .dropna()
                .astype(str)
                .sort_values()
                .tolist()
            )
            if not units:
                st.error(f"ไม่พบห้องของตึก {bld} ในฐานข้อมูล")
                st.stop()

            unit = st.selectbox(
                "เลือกห้อง",
                units,
                key=f"booking_room_{bld}",
            )
            cust_name = st.text_input("ชื่อลูกค้า")
            cust_type = st.selectbox("ประเภทลูกค้า", ["Walk in", "Agent"])
        with col2:
            phone = st.text_input("เบอร์โทร")
            check_in = st.date_input("วันที่เข้าพัก")
            check_out = st.date_input("วันที่คืนห้อง")
            rent = st.number_input("ค่าเช่าทั้งหมด", min_value=0.0, step=100.0)
            deposit = st.number_input("เงินมัดจำ", min_value=0.0, step=100.0)

        if st.form_submit_button("บันทึกการจอง"):
            if not cust_name:
                st.error("กรุณากรอกชื่อลูกค้า")
            elif check_in >= check_out:
                st.error("วันที่คืนต้องมาหลังวันที่เข้า")
            else:
                bk_no = get_next_booking_no()
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute(
                    """INSERT INTO bookings
                    (id, building, unit_no, customer_name, customer_type, phone, check_in, check_out, rent_amount, deposit, status, booking_no)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()), bld, unit, cust_name, cust_type, phone,
                        check_in, check_out, rent, deposit, "booked", bk_no,
                    ),
                )
                conn.commit()
                conn.close()
                st.success(f"บันทึกเรียบร้อย เลขที่จอง: {bk_no}")


# ==========================================================
# 3) RECEIVE DEPOSIT / PRINT DOCUMENT
# ==========================================================
elif menu == "รับเงินประกัน/พิมพ์เอกสาร":
    st.header("รับเงินประกัน / พิมพ์เอกสาร")
    conn = sqlite3.connect(DB_FILE)
    bk = pd.read_sql(
        "SELECT booking_no, building, unit_no, customer_name, phone, check_in, check_out, deposit FROM bookings ORDER BY check_in DESC",
        conn,
    )
    conn.close()

    if bk.empty:
        st.info("ยังไม่มีรายการจองสำหรับรับเงินประกัน")
    else:
        labels = (bk["booking_no"] + " - " + bk["building"] + " - " + bk["unit_no"] + " - " + bk["customer_name"]).tolist()
        selected = st.selectbox("เลือกรายการจอง", labels, key="deposit_receive_booking")
        booking_no = selected.split(" - ")[0]
        row = bk[bk["booking_no"] == booking_no].iloc[0]
        default_amount = float(row["deposit"] or 0)
        amount = st.number_input("จำนวนเงินประกันที่รับ", min_value=0.0, value=default_amount, step=100.0, key="deposit_receive_amount")
        trans_date = st.date_input("วันที่รับเงิน", value=datetime.today().date(), key="deposit_receive_date")
        note = st.text_input("หมายเหตุ", key="deposit_receive_note")

        conn = sqlite3.connect(DB_FILE)
        existing = pd.read_sql("SELECT * FROM deposit_transactions WHERE booking_no = ? AND transaction_type = 'receive' ORDER BY transaction_date DESC", conn, params=(booking_no,))
        conn.close()
        if not existing.empty:
            st.info(f"รายการรับเงินประกันนี้มีบันทึกแล้ว {len(existing)} รายการ ล่าสุด {existing.iloc[0]['doc_no']}")

        if st.button("💾 บันทึกรับเงินประกัน + พิมพ์เอกสาร", type="primary", key="save_receive_deposit"):
            if amount <= 0:
                st.error("กรุณาระบุจำนวนเงินประกันมากกว่า 0 บาท")
            else:
                doc_no = get_next_deposit_receipt_no()
                tx_id = str(uuid.uuid4())
                conn = sqlite3.connect(DB_FILE)
                conn.execute(
                    "INSERT INTO deposit_transactions (id, booking_no, transaction_type, amount, doc_no, transaction_date, note) VALUES (?, ?, 'receive', ?, ?, ?, ?)",
                    (tx_id, booking_no, amount, doc_no, trans_date.isoformat(), note.strip()),
                )
                conn.commit()
                conn.close()
                data = {**row.to_dict(), "amount": amount, "doc_no": doc_no, "transaction_date": trans_date.strftime("%d/%m/%Y"), "note": note}
                html = generate_deposit_document_html(data, "receive")
                st.success(f"บันทึกรับเงินประกันเรียบร้อย เลขที่เอกสาร {doc_no}")
                components.html(html, height=800, scrolling=True)


# ==========================================================
# 4) REFUND DEPOSIT / PRINT DOCUMENT
# ==========================================================
elif menu == "คืนเงินประกัน/พิมพ์เอกสาร":
    st.header("คืนเงินประกัน / พิมพ์เอกสาร")
    conn = sqlite3.connect(DB_FILE)
    bk = pd.read_sql(
        "SELECT booking_no, building, unit_no, customer_name, phone, check_in, check_out, deposit FROM bookings ORDER BY check_in DESC",
        conn,
    )
    conn.close()

    if bk.empty:
        st.info("ยังไม่มีรายการจองสำหรับคืนเงินประกัน")
    else:
        labels = (bk["booking_no"] + " - " + bk["building"] + " - " + bk["unit_no"] + " - " + bk["customer_name"]).tolist()
        selected = st.selectbox("เลือกรายการจอง", labels, key="deposit_refund_booking")
        booking_no = selected.split(" - ")[0]
        row = bk[bk["booking_no"] == booking_no].iloc[0]
        deposit_amount = float(row["deposit"] or 0)

        conn = sqlite3.connect(DB_FILE)
        received = pd.read_sql("SELECT COALESCE(SUM(amount),0) AS total FROM deposit_transactions WHERE booking_no = ? AND transaction_type = 'receive'", conn, params=(booking_no,))
        refunded = pd.read_sql("SELECT COALESCE(SUM(amount),0) AS total FROM deposit_transactions WHERE booking_no = ? AND transaction_type = 'refund'", conn, params=(booking_no,))
        conn.close()
        received_amount = float(received.iloc[0]["total"] or 0)
        refunded_amount = float(refunded.iloc[0]["total"] or 0)
        available_refund = max(0, received_amount - refunded_amount) if received_amount > 0 else deposit_amount

        st.info(f"เงินประกันตามการจอง: {deposit_amount:,.2f} บาท | รับจริงแล้ว: {received_amount:,.2f} บาท | คืนไปแล้ว: {refunded_amount:,.2f} บาท | คงเหลือคืนได้: {available_refund:,.2f} บาท")
        amount = st.number_input("จำนวนเงินประกันที่คืน", min_value=0.0, value=available_refund, step=100.0, key="deposit_refund_amount")
        trans_date = st.date_input("วันที่คืนเงิน", value=datetime.today().date(), key="deposit_refund_date")
        note = st.text_input("หมายเหตุ", key="deposit_refund_note")

        if st.button("💾 บันทึกคืนเงินประกัน + พิมพ์เอกสาร", type="primary", key="save_refund_deposit"):
            if amount <= 0:
                st.error("ไม่มียอดเงินประกันให้คืน หรือกรุณาระบุจำนวนเงินมากกว่า 0 บาท")
            elif amount > available_refund:
                st.error(f"จำนวนเงินคืนเกินยอดที่สามารถคืนได้ {available_refund:,.2f} บาท")
            else:
                doc_no = get_next_deposit_refund_no()
                tx_id = str(uuid.uuid4())
                conn = sqlite3.connect(DB_FILE)
                conn.execute(
                    "INSERT INTO deposit_transactions (id, booking_no, transaction_type, amount, doc_no, transaction_date, note) VALUES (?, ?, 'refund', ?, ?, ?, ?)",
                    (tx_id, booking_no, amount, doc_no, trans_date.isoformat(), note.strip()),
                )
                conn.commit()
                conn.close()
                data = {**row.to_dict(), "amount": amount, "doc_no": doc_no, "transaction_date": trans_date.strftime("%d/%m/%Y"), "note": note}
                html = generate_deposit_document_html(data, "refund")
                st.success(f"บันทึกคืนเงินประกันเรียบร้อย เลขที่เอกสาร {doc_no}")
                components.html(html, height=800, scrolling=True)


# ==========================================================
# 5) CHECKOUT / RECEIPT
# ==========================================================
elif menu == "คืนห้อง/ออกใบเสร็จ":
    st.header("คืนห้องและออกใบเสร็จ")

    conn = sqlite3.connect(DB_FILE)
    bk_list = pd.read_sql(
        """SELECT booking_no, building, unit_no, customer_name, check_in, check_out, deposit
           FROM bookings WHERE status = 'booked' ORDER BY check_in DESC""",
        conn,
    )
    checked_out_list = pd.read_sql(
        """SELECT booking_no, building, unit_no, customer_name, check_in, check_out, deposit
           FROM bookings WHERE status = 'checked_out' ORDER BY check_in DESC""",
        conn,
    )
    damage_master = pd.read_sql(
        """SELECT item_no, item_name, damage_price, dirty_price
           FROM damage_items WHERE active = 1 ORDER BY item_no""",
        conn,
    )
    conn.close()

    if bk_list.empty:
        st.info("ไม่มีรายการที่รอคืนห้อง")

    # ------------------------------------------------------
    # รายการที่เคยคืนแล้ว: เปิดกลับมาเพื่อทำรายการคืนใหม่
    # โดยไม่ลบประวัติ checkout เดิม
    # ------------------------------------------------------
    if not checked_out_list.empty:
        with st.expander("🔄 รายการที่เคยคืนห้องแล้ว / ต้องการเปิดกลับมาคืนใหม่"):
            st.caption(
                "ใช้กรณีรายการจองหายจากหน้าคืนห้อง แต่ต้องการทำรายการใหม่ "
                "ระบบจะเปลี่ยนสถานะการจองกลับเป็น 'รอคืนห้อง' และเก็บประวัติการคืนเดิมไว้"
            )

            reopen_labels = (
                checked_out_list["booking_no"]
                + " - "
                + checked_out_list["building"]
                + " - "
                + checked_out_list["unit_no"]
                + " - "
                + checked_out_list["customer_name"]
            ).tolist()

            reopen_sel = st.selectbox(
                "เลือกรายการที่ต้องการเปิดกลับมาคืนห้อง",
                reopen_labels,
                key="reopen_checkout_booking",
            )

            reopen_booking_no = reopen_sel.split(" - ")[0]

            if st.button(
                "🔄 เปิดกลับมาเป็นรายการรอคืนห้อง",
                key="reopen_checkout_btn",
                type="secondary",
            ):
                conn_reopen = sqlite3.connect(DB_FILE)
                conn_reopen.execute(
                    "UPDATE bookings SET status = 'booked' WHERE booking_no = ?",
                    (reopen_booking_no,),
                )
                conn_reopen.commit()
                conn_reopen.close()
                st.success(
                    f"เปิดรายการ {reopen_booking_no} กลับมาแล้ว "
                    "ประวัติการคืนห้องเดิมยังคงอยู่ในระบบ"
                )
                st.rerun()

    # ------------------------------------------------------
    # แก้ไข / ลบรายการคืนห้องที่บันทึกแล้ว
    # ------------------------------------------------------
    if not checked_out_list.empty:
        st.markdown("---")
        st.subheader("✏️ แก้ไข / 🗑️ ลบรายการคืนห้องที่บันทึกแล้ว")
        st.caption("ใช้กรณีบันทึกคืนห้องไปแล้ว แต่ต้องการแก้ข้อมูล หรือบันทึกผิดและต้องการลบรายการ")

        saved_labels = (
            checked_out_list["booking_no"] + " - " +
            checked_out_list["building"] + " - " +
            checked_out_list["unit_no"] + " - " +
            checked_out_list["customer_name"]
        ).tolist()
        saved_sel = st.selectbox(
            "เลือกรายการคืนห้องที่ต้องการจัดการ",
            saved_labels,
            key="saved_checkout_manage",
        )
        saved_booking_no = saved_sel.split(" - ")[0]

        conn_manage = sqlite3.connect(DB_FILE)
        saved_df = pd.read_sql(
            "SELECT * FROM checkouts WHERE booking_no = ?",
            conn_manage,
            params=(saved_booking_no,),
        )
        saved_damage_df = pd.read_sql(
            "SELECT item_no, item_name, condition_type, quantity, unit_price, amount "
            "FROM checkout_damages WHERE booking_no = ? ORDER BY id",
            conn_manage,
            params=(saved_booking_no,),
        )
        conn_manage.close()

        if not saved_df.empty:
            saved_row = saved_df.iloc[0]
            manage_c1, manage_c2 = st.columns(2)
            with manage_c1:
                edit_clicked = st.button("✏️ แก้ไขรายการนี้", key=f"edit_checkout_{saved_booking_no}", use_container_width=True)
            with manage_c2:
                delete_clicked = st.button("🗑️ ลบรายการนี้", key=f"delete_checkout_{saved_booking_no}", use_container_width=True)

            if delete_clicked:
                st.session_state[f"confirm_delete_checkout_{saved_booking_no}"] = True

            if st.session_state.get(f"confirm_delete_checkout_{saved_booking_no}", False):
                st.warning(
                    f"ยืนยันการลบรายการคืนห้อง {saved_booking_no} หรือไม่? "
                    "รายการคืนห้องและรายการของเสียหายที่บันทึกไว้จะถูกลบ แต่ข้อมูลการจองจะกลับมาเป็น 'รอคืนห้อง'"
                )
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("ยืนยันลบ", key=f"confirm_del_{saved_booking_no}", type="primary", use_container_width=True):
                        conn_del = sqlite3.connect(DB_FILE)
                        conn_del.execute("DELETE FROM checkout_damages WHERE checkout_id = ?", (saved_row["id"],))
                        conn_del.execute("DELETE FROM checkouts WHERE id = ?", (saved_row["id"],))
                        conn_del.execute("UPDATE bookings SET status = 'booked' WHERE booking_no = ?", (saved_booking_no,))
                        conn_del.commit()
                        conn_del.close()
                        st.session_state.pop(f"confirm_delete_checkout_{saved_booking_no}", None)
                        st.success(f"ลบรายการคืนห้อง {saved_booking_no} แล้ว และนำรายการกลับไปอยู่ใน 'รอคืนห้อง'")
                        st.rerun()
                with dc2:
                    if st.button("ยกเลิก", key=f"cancel_del_{saved_booking_no}", use_container_width=True):
                        st.session_state.pop(f"confirm_delete_checkout_{saved_booking_no}", None)
                        st.rerun()

            if edit_clicked:
                st.session_state["editing_checkout_booking_no"] = saved_booking_no
                st.rerun()

            editing_no = st.session_state.get("editing_checkout_booking_no")
            if editing_no == saved_booking_no:
                st.markdown("### ✏️ แก้ไขรายละเอียดการคืนห้อง")

                edit_booking_row = bk_list[bk_list["booking_no"] == saved_booking_no]
                if edit_booking_row.empty:
                    edit_booking_row = checked_out_list[checked_out_list["booking_no"] == saved_booking_no]
                edit_bk = edit_booking_row.iloc[0]

                existing_damage_labels = []
                existing_damage_map = {}
                for _, dr in saved_damage_df.iterrows():
                    label = f"{int(dr['item_no']):02d} - {dr['item_name']}"
                    existing_damage_labels.append(label)
                    existing_damage_map[int(dr["item_no"])] = dr.to_dict()

                edit_damage_options = {
                    f"{int(row.item_no):02d} - {row.item_name}": int(row.item_no)
                    for _, row in damage_master.iterrows()
                }
                edit_selected = st.multiselect(
                    "รายการของเสียหาย / สูญหาย / สกปรก",
                    options=list(edit_damage_options.keys()),
                    default=[x for x in existing_damage_labels if x in edit_damage_options],
                    key=f"edit_damage_items_{saved_booking_no}",
                )

                edit_damage_rows = []
                edit_damage_total = 0.0
                for label in edit_selected:
                    item_no = edit_damage_options[label]
                    item = damage_master[damage_master["item_no"] == item_no].iloc[0]
                    old = existing_damage_map.get(item_no, {})
                    ec1, ec2, ec3, ec4 = st.columns([3.2, 1.5, 1.5, 1.5])
                    with ec1:
                        st.markdown(f"**{item['item_name']}**")
                    old_condition = old.get("condition_type", "Damage & Lost")
                    with ec2:
                        condition = st.selectbox(
                            "สภาพ",
                            ["Damage & Lost", "Dirty"],
                            index=0 if old_condition == "Damage & Lost" else 1,
                            key=f"edit_condition_{saved_booking_no}_{item_no}",
                        )
                    default_price = item["damage_price"] if condition == "Damage & Lost" else item["dirty_price"]
                    old_qty = float(old.get("quantity", 1) or 1)
                    old_price = old.get("unit_price", None)
                    if old_price is None or pd.isna(old_price):
                        old_price = 0.0 if pd.isna(default_price) else float(default_price)
                    with ec3:
                        qty = st.number_input(
                            "จำนวน", min_value=0.1, value=old_qty, step=1.0,
                            key=f"edit_qty_{saved_booking_no}_{item_no}"
                        )
                    with ec4:
                        unit_price = st.number_input(
                            "ราคา/หน่วย", min_value=0.0, value=float(old_price), step=50.0,
                            key=f"edit_price_{saved_booking_no}_{item_no}"
                        )
                    amount = float(qty) * float(unit_price)
                    edit_damage_total += amount
                    edit_damage_rows.append({
                        "item_no": int(item_no), "item_name": item["item_name"],
                        "condition_type": condition, "quantity": float(qty),
                        "unit_price": float(unit_price), "amount": amount,
                    })

                st.markdown(f"**รวมค่าของเสียหาย: {edit_damage_total:,.2f} บาท**")

                with st.form(f"edit_checkout_form_{saved_booking_no}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        ew1 = st.number_input("เลขมิเตอร์น้ำ ก่อน", min_value=0.0, value=float(saved_row["water_meter_before"] or 0), step=1.0)
                        ew2 = st.number_input("เลขมิเตอร์น้ำ หลัง", min_value=0.0, value=float(saved_row["water_meter_after"] or 0), step=1.0)
                        ewr = st.number_input("ค่าน้ำ/หน่วย", min_value=0.0, value=float(saved_row["water_rate"] or 0), step=1.0)
                        ee1 = st.number_input("เลขมิเตอร์ไฟ ก่อน", min_value=0.0, value=float(saved_row["elec_meter_before"] or 0), step=1.0)
                        ee2 = st.number_input("เลขมิเตอร์ไฟ หลัง", min_value=0.0, value=float(saved_row["elec_meter_after"] or 0), step=1.0)
                        eer = st.number_input("ค่าไฟ/หน่วย", min_value=0.0, value=float(saved_row["elec_rate"] or 0), step=1.0)
                    with ec2:
                        ecf = st.number_input("ค่าทำความสะอาด", min_value=0.0, value=float(saved_row["cleaning_fee"] or 0), step=50.0)
                        eof = st.number_input("ค่าอื่นๆ", min_value=0.0, value=float(saved_row["other_fee"] or 0), step=100.0)

                    st.markdown("#### เปลี่ยนรูปมิเตอร์ (ถ้าไม่เลือก ระบบจะใช้รูปเดิม)")
                    ep1, ep2 = st.columns(2)
                    with ep1:
                        ewbf = st.file_uploader("มิเตอร์น้ำ - ก่อน", type=["jpg","jpeg","png","webp"], key=f"edit_wbf_{saved_booking_no}")
                        ewaf = st.file_uploader("มิเตอร์น้ำ - หลัง", type=["jpg","jpeg","png","webp"], key=f"edit_waf_{saved_booking_no}")
                    with ep2:
                        eebf = st.file_uploader("มิเตอร์ไฟ - ก่อน", type=["jpg","jpeg","png","webp"], key=f"edit_ebf_{saved_booking_no}")
                        eeaf = st.file_uploader("มิเตอร์ไฟ - หลัง", type=["jpg","jpeg","png","webp"], key=f"edit_eaf_{saved_booking_no}")

                    save_edit = st.form_submit_button("💾 บันทึกการแก้ไข", type="primary")

                if save_edit:
                    new_wbf = image_bytes(ewbf) if ewbf else saved_row["water_meter_before_photo"]
                    new_waf = image_bytes(ewaf) if ewaf else saved_row["water_meter_after_photo"]
                    new_ebf = image_bytes(eebf) if eebf else saved_row["elec_meter_before_photo"]
                    new_eaf = image_bytes(eeaf) if eeaf else saved_row["elec_meter_after_photo"]
                    conn_up = sqlite3.connect(DB_FILE)
                    conn_up.execute("""UPDATE checkouts SET
                        water_meter_before=?, water_meter_after=?, water_rate=?,
                        elec_meter_before=?, elec_meter_after=?, elec_rate=?,
                        cleaning_fee=?, damage_fee=?, other_fee=?,
                        water_meter_before_photo=?, water_meter_after_photo=?,
                        elec_meter_before_photo=?, elec_meter_after_photo=?
                        WHERE id=?""", (
                        ew1, ew2, ewr, ee1, ee2, eer, ecf, edit_damage_total, eof,
                        new_wbf, new_waf, new_ebf, new_eaf, saved_row["id"]
                    ))
                    conn_up.execute("DELETE FROM checkout_damages WHERE checkout_id = ?", (saved_row["id"],))
                    for row in edit_damage_rows:
                        conn_up.execute("""INSERT INTO checkout_damages
                            (checkout_id, booking_no, item_no, item_name, condition_type, quantity, unit_price, amount)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
                            saved_row["id"], saved_booking_no, row["item_no"], row["item_name"],
                            row["condition_type"], row["quantity"], row["unit_price"], row["amount"]
                        ))
                    conn_up.commit()
                    conn_up.close()
                    st.session_state.pop("editing_checkout_booking_no", None)
                    st.success(f"แก้ไขรายการ {saved_booking_no} เรียบร้อยแล้ว ใบเสร็จเดิม {saved_row['receipt_no']} และใบคืนมัดจำเดิม {saved_row['refund_no']} ยังคงเดิม")
                    st.rerun()

    if not bk_list.empty:
        sel = st.selectbox(
            "เลือกรายการจอง",
            bk_list["booking_no"] + " - " + bk_list["building"] + " - " + bk_list["unit_no"] + " - " + bk_list["customer_name"],
        )
        sel_bk = bk_list[bk_list["booking_no"] == sel.split(" - ")[0]].iloc[0]

        st.markdown(
            f"""
            <div style="background:#eef5fb;border-left:5px solid #17365D;
                        padding:10px 14px;margin:8px 0 14px 0;">
                <b>{sel_bk['building']} - ห้อง {sel_bk['unit_no']}</b>
                &nbsp; | &nbsp; ลูกค้า: <b>{sel_bk['customer_name']}</b>
                &nbsp; | &nbsp; มัดจำ: <b>{float(sel_bk['deposit'] or 0):,.2f} บาท</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------
        # รายการของเสียหาย/สูญหาย/สกปรก
        # แยกจากประเภทห้องโดยสิ้นเชิง
        # ------------------------------------------------------
        st.subheader("รายการของเสียหาย / สูญหาย / สกปรก")
        st.caption(
            "รายการนี้เป็นรายการกลาง ใช้ได้กับทุกประเภทห้อง "
            "และเลือกเฉพาะรายการที่ต้องการหักเงินลูกค้า"
        )

        damage_options = {
            f"{int(row.item_no):02d} - {row.item_name}": int(row.item_no)
            for _, row in damage_master.iterrows()
        }

        selected_damage_labels = st.multiselect(
            "เลือกรายการที่ต้องหักเงินลูกค้า",
            options=list(damage_options.keys()),
            key=f"damage_items_{sel_bk['booking_no']}",
        )

        damage_rows = []
        damage_total = 0.0

        for idx, label in enumerate(selected_damage_labels):
            item_no = damage_options[label]
            item = damage_master[damage_master["item_no"] == item_no].iloc[0]

            c1, c2, c3, c4 = st.columns([3.2, 1.5, 1.5, 1.5])

            with c1:
                st.markdown(f"**{item['item_name']}**")

            with c2:
                condition = st.selectbox(
                    "สภาพ",
                    ["Damage & Lost", "Dirty"],
                    key=f"damage_condition_{sel_bk['booking_no']}_{item_no}",
                )

            default_price = (
                item["damage_price"]
                if condition == "Damage & Lost"
                else item["dirty_price"]
            )

            with c3:
                qty = st.number_input(
                    "จำนวน",
                    min_value=0.1,
                    value=1.0,
                    step=1.0,
                    key=f"damage_qty_{sel_bk['booking_no']}_{item_no}",
                )

            with c4:
                if pd.isna(default_price) or default_price is None:
                    unit_price = st.number_input(
                        "ราคา/หน่วย",
                        min_value=0.0,
                        value=0.0,
                        step=100.0,
                        key=f"damage_price_{sel_bk['booking_no']}_{item_no}",
                        help="รายการในเอกสารระบุ Actual Cost ให้กรอกราคาจริง",
                    )
                else:
                    unit_price = st.number_input(
                        "ราคา/หน่วย",
                        min_value=0.0,
                        value=float(default_price),
                        step=50.0,
                        key=f"damage_price_{sel_bk['booking_no']}_{item_no}",
                    )

            amount = float(qty) * float(unit_price)
            damage_total += amount

            damage_rows.append({
                "item_no": int(item_no),
                "item_name": item["item_name"],
                "condition_type": condition,
                "quantity": float(qty),
                "unit_price": float(unit_price),
                "amount": amount,
            })

        st.markdown(
            f"""
            <div style="background:#fff4d6;border:1px solid #f0c36d;
                        padding:10px 14px;margin:8px 0 16px 0;">
                <b>รวมค่าของเสียหาย / สูญหาย / สกปรก: 
                {damage_total:,.2f} บาท</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("checkout_form"):
            st.subheader("มิเตอร์และค่าใช้จ่ายอื่น")

            col1, col2 = st.columns(2)

            with col1:
                w1 = st.number_input("เลขมิเตอร์น้ำ ก่อน", min_value=0.0, step=1.0)
                w2 = st.number_input("เลขมิเตอร์น้ำ หลัง", min_value=0.0, step=1.0)
                wr = st.number_input("ค่าน้ำ/หน่วย", min_value=0.0, step=1.0, value=20.0)
                e1 = st.number_input("เลขมิเตอร์ไฟ ก่อน", min_value=0.0, step=1.0)
                e2 = st.number_input("เลขมิเตอร์ไฟ หลัง", min_value=0.0, step=1.0)
                er = st.number_input("ค่าไฟ/หน่วย", min_value=0.0, step=1.0, value=6.0)

            st.markdown("### รูปมิเตอร์สำหรับตรวจสอบย้อนหลัง")
            st.caption("แนบรูปมิเตอร์ก่อนและหลังการเข้าพัก เพื่อให้ผู้บริหาร/บัญชีตรวจสอบย้อนหลังได้")
            photo_c1, photo_c2 = st.columns(2)
            with photo_c1:
                water_before_photo_file = st.file_uploader(
                    "📷 มิเตอร์น้ำ - ก่อนเข้าพัก",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"water_before_photo_{sel_bk['booking_no']}"
                )
                water_after_photo_file = st.file_uploader(
                    "📷 มิเตอร์น้ำ - หลังเข้าพัก",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"water_after_photo_{sel_bk['booking_no']}"
                )
            with photo_c2:
                elec_before_photo_file = st.file_uploader(
                    "📷 มิเตอร์ไฟ - ก่อนเข้าพัก",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"elec_before_photo_{sel_bk['booking_no']}"
                )
                elec_after_photo_file = st.file_uploader(
                    "📷 มิเตอร์ไฟ - หลังเข้าพัก",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"elec_after_photo_{sel_bk['booking_no']}"
                )

            with col2:
                cf = st.number_input("ค่าทำความสะอาด", min_value=0.0, step=50.0)
                of = st.number_input("ค่าอื่นๆ", min_value=0.0, step=100.0)

            st.markdown(
                f"### ค่าของเสียหายที่หักลูกค้า: **{damage_total:,.2f} บาท**"
            )

            submitted = st.form_submit_button(
                "บันทึกคืนห้องและออกใบเสร็จ"
            )

        if submitted:
            booking_no = sel_bk["booking_no"]
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()

            # ป้องกันการบันทึกคืนห้องซ้ำ: booking_no ใน checkouts เป็น UNIQUE
            c.execute(
                """SELECT id, receipt_no, refund_no,
                          water_meter_before, water_meter_after, water_rate,
                          elec_meter_before, elec_meter_after, elec_rate,
                          cleaning_fee, damage_fee, other_fee,
                          water_meter_before_photo, water_meter_after_photo,
                          elec_meter_before_photo, elec_meter_after_photo
                   FROM checkouts WHERE booking_no = ?""",
                (booking_no,),
            )
            existing = c.fetchone()

            if existing:
                # มีรายการเดิมแล้ว: ใช้ข้อมูลเดิม ไม่ INSERT ซ้ำ
                (checkout_id, rec_no, ref_no, old_w1, old_w2, old_wr,
                 old_e1, old_e2, old_er, old_cf, old_df, old_of,
                 old_wbf, old_waf, old_ebf, old_eaf) = existing
                w1, w2, wr = old_w1, old_w2, old_wr
                e1, e2, er = old_e1, old_e2, old_er
                cf, damage_total, of = old_cf, old_df, old_of

                # ดึงรายการของเสียหายเดิมกลับมาแสดงในเอกสาร
                old_damage_df = pd.read_sql(
                    """SELECT item_no, item_name, condition_type, quantity, unit_price, amount
                       FROM checkout_damages WHERE checkout_id = ? ORDER BY id""",
                    conn,
                    params=(checkout_id,),
                )
                damage_rows = old_damage_df.to_dict("records") if not old_damage_df.empty else []

                c.execute(
                    "UPDATE bookings SET status = 'checked_out' WHERE booking_no = ?",
                    (booking_no,),
                )
                conn.commit()
                conn.close()
                st.warning(
                    f"รายการ {booking_no} เคยบันทึกคืนห้องแล้ว ระบบจะไม่สร้างรายการซ้ำ "
                    f"และใช้เอกสารเดิม: ใบเสร็จ {rec_no} / ใบคืนมัดจำ {ref_no}"
                )

                water_before_photo_data = old_wbf
                water_after_photo_data = old_waf
                elec_before_photo_data = old_ebf
                elec_after_photo_data = old_eaf
            else:
                rec_no = get_next_receipt_no()
                ref_no = get_next_refund_no()
                checkout_id = str(uuid.uuid4())
                water_before_photo_data = image_bytes(water_before_photo_file)
                water_after_photo_data = image_bytes(water_after_photo_file)
                elec_before_photo_data = image_bytes(elec_before_photo_file)
                elec_after_photo_data = image_bytes(elec_after_photo_file)

                try:
                    c.execute(
                        """INSERT INTO checkouts
                        (id, booking_no, water_meter_before, water_meter_after, water_rate,
                         elec_meter_before, elec_meter_after, elec_rate,
                         cleaning_fee, damage_fee, other_fee, receipt_no, refund_no,
                         water_meter_before_photo, water_meter_after_photo,
                         elec_meter_before_photo, elec_meter_after_photo)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            checkout_id, booking_no,
                            w1, w2, wr, e1, e2, er,
                            cf, damage_total, of, rec_no, ref_no,
                            water_before_photo_data, water_after_photo_data,
                            elec_before_photo_data, elec_after_photo_data,
                        ),
                    )

                    for row in damage_rows:
                        c.execute(
                            """INSERT INTO checkout_damages
                            (checkout_id, booking_no, item_no, item_name,
                             condition_type, quantity, unit_price, amount)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                checkout_id, booking_no, row["item_no"],
                                row["item_name"], row["condition_type"],
                                row["quantity"], row["unit_price"], row["amount"],
                            ),
                        )

                    c.execute(
                        "UPDATE bookings SET status = 'checked_out' WHERE booking_no = ?",
                        (booking_no,),
                    )
                    conn.commit()
                    conn.close()

                    st.success(
                        f"บันทึกเรียบร้อย ใบเสร็จ: {rec_no} | "
                        f"ใบคืนมัดจำ: {ref_no} | "
                        f"หักค่าของเสียหาย: {damage_total:,.2f} บาท"
                    )
                except sqlite3.IntegrityError as exc:
                    conn.rollback()
                    conn.close()
                    if "checkouts.booking_no" in str(exc):
                        st.error(
                            "รายการนี้ถูกบันทึกคืนห้องไปแล้ว ระบบไม่สร้างรายการซ้ำค่ะ "
                            "กรุณาใช้เอกสารเดิมจากเมนูพิมพ์เอกสาร"
                        )
                    else:
                        st.error(f"ไม่สามารถบันทึกได้: {exc}")
                    st.stop()

            data = {
                "booking_no": booking_no,
                "building": sel_bk["building"],
                "unit_no": sel_bk["unit_no"],
                "customer_name": sel_bk["customer_name"],
                "check_in": pd.to_datetime(sel_bk["check_in"]).strftime("%d/%m/%Y"),
                "check_out": pd.to_datetime(sel_bk["check_out"]).strftime("%d/%m/%Y"),
                "deposit": sel_bk["deposit"],
                "water_meter_before": w1,
                "water_meter_after": w2,
                "water_rate": wr,
                "elec_meter_before": e1,
                "elec_meter_after": e2,
                "elec_rate": er,
                "cleaning_fee": cf,
                "damage_fee": damage_total,
                "other_fee": of,
                "receipt_no": rec_no,
                "refund_no": ref_no,
                "damage_rows": damage_rows,
                "water_meter_before_photo": water_before_photo_data,
                "water_meter_after_photo": water_after_photo_data,
                "elec_meter_before_photo": elec_before_photo_data,
                "elec_meter_after_photo": elec_after_photo_data,
            }

            st.subheader("ใบเสร็จรับเงิน")
            hr, _ = generate_receipt_html(data, "receipt")
            components.html(hr, height=760, scrolling=True)
            st.markdown(
                get_download_link(hr, f"ใบเสร็จ_{rec_no}"),
                unsafe_allow_html=True,
            )

            st.subheader("ใบคืนเงินมัดจำ")
            hf, _ = generate_receipt_html(data, "refund")
            components.html(hf, height=700, scrolling=True)
            st.markdown(
                get_download_link(hf, f"ใบคืนมัดจำ_{ref_no}"),
                unsafe_allow_html=True,
            )

            st.subheader("หลักฐานรูปมิเตอร์สำหรับตรวจสอบย้อนหลัง")
            photo_cols = st.columns(4)
            photo_list = [
                ("มิเตอร์น้ำ ก่อน", water_before_photo_data),
                ("มิเตอร์น้ำ หลัง", water_after_photo_data),
                ("มิเตอร์ไฟ ก่อน", elec_before_photo_data),
                ("มิเตอร์ไฟ หลัง", elec_after_photo_data),
            ]
            for col, (label, photo_data) in zip(photo_cols, photo_list):
                with col:
                    if photo_data:
                        st.image(photo_data, caption=label, use_container_width=True)
                    else:
                        st.caption(f"{label}: ไม่มีรูปแนบ")


# ==========================================================
# 4) PRINT DOCUMENTS
# ==========================================================
elif menu == "พิมพ์เอกสาร":
    st.header("พิมพ์เอกสาร")
    doc_type = st.radio("เลือกประเภท", ["ใบยืนยันการจอง", "ใบเสร็จ/คืนมัดจำ"])

    if doc_type == "ใบยืนยันการจอง":
        search_by = st.radio("ค้นหาด้วย", ["เลขที่จอง", "รายการล่าสุด"])
        bk_data = None
        conn = sqlite3.connect(DB_FILE)

        if search_by == "เลขที่จอง":
            inp = st.text_input("กรอกเลขที่จอง")
            if inp:
                df = pd.read_sql("SELECT * FROM bookings WHERE booking_no = ?", conn, params=(inp.strip(),))
                if not df.empty:
                    bk_data = df.iloc[0]
                else:
                    st.warning("ไม่พบ")
        else:
            recent = pd.read_sql(
                "SELECT booking_no, building, unit_no, customer_name FROM bookings ORDER BY check_in DESC LIMIT 10",
                conn,
            )
            if not recent.empty:
                sel = st.selectbox("เลือกรายการ", recent["booking_no"] + " - " + recent["unit_no"] + " - " + recent["customer_name"])
                bk_no = sel.split(" - ")[0]
                df = pd.read_sql("SELECT * FROM bookings WHERE booking_no = ?", conn, params=(bk_no,))
                bk_data = df.iloc[0]
            else:
                st.info("ยังไม่มีรายการ")
        conn.close()

        if bk_data is not None:
            st.subheader("ใบยืนยันการจอง")
            today_str = datetime.now().strftime("%d/%m/%Y")
            building_name = str(bk_data["building"]).strip().upper()
            if building_name == "PALM":
                display_building = "PALM"
            elif building_name == "THE ARK":
                display_building = "THE ARK"
            else:
                display_building = building_name

            bk_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>ใบยืนยันการจอง {bk_data['booking_no']}</title>
                <style>
                    @page {{ size: A4; margin: 18mm; }}
                    body {{ margin:0; background:#f4f1e9; font-family:Arial, sans-serif; color:#263238; }}
                    .page {{ max-width:760px; margin:25px auto; background:#fffdf8; border:1px solid #c9b98f; padding:42px; box-sizing:border-box; }}
                    .brand {{ text-align:center; color:#17365d; font-size:30px; font-weight:700; letter-spacing:3px; margin-bottom:6px; }}
                    .subtitle {{ text-align:center; font-size:20px; font-weight:700; margin-bottom:24px; color:#444; }}
                    .goldline {{ border-top:3px solid #c9a227; margin:10px 0 24px; }}
                    .meta {{ display:flex; justify-content:space-between; font-size:13px; margin-bottom:18px; }}
                    .section {{ background:#17365d; color:white; padding:8px 12px; font-weight:700; margin-top:18px; }}
                    table {{ width:100%; border-collapse:collapse; margin-top:0; }}
                    td {{ padding:9px 10px; border-bottom:1px solid #e5dfd0; }}
                    td:first-child {{ width:38%; color:#555; font-weight:600; }}
                    .amount {{ font-size:18px; font-weight:700; color:#17365d; }}
                    .sign {{ margin-top:55px; display:flex; justify-content:space-between; gap:50px; text-align:center; }}
                    .sign div {{ width:45%; }}
                    .small {{ font-size:11px; color:#777; margin-top:25px; text-align:center; }}
                </style>
            </head>
            <body>
                <div class="page">
                    <div class="brand">{display_building}</div>
                    <div class="subtitle">ใบยืนยันการจองห้องพัก</div>
                    <div class="goldline"></div>
                    <div class="meta">
                        <span><strong>เลขที่จอง:</strong> {bk_data['booking_no']}</span>
                        <span><strong>วันที่พิมพ์:</strong> {today_str}</span>
                    </div>

                    <div class="section">ข้อมูลลูกค้า</div>
                    <table>
                        <tr><td>ชื่อลูกค้า</td><td>{bk_data['customer_name']}</td></tr>
                        <tr><td>เบอร์ติดต่อ</td><td>{bk_data['phone'] or '-'}</td></tr>
                        <tr><td>ประเภทลูกค้า</td><td>{bk_data['customer_type'] or '-'}</td></tr>
                    </table>

                    <div class="section">รายละเอียดการจอง</div>
                    <table>
                        <tr><td>ตึก</td><td>{display_building}</td></tr>
                        <tr><td>ห้อง</td><td>{bk_data['unit_no']}</td></tr>
                        <tr><td>วันที่เข้าพัก</td><td>{pd.to_datetime(bk_data['check_in']).strftime('%d/%m/%Y')}</td></tr>
                        <tr><td>วันที่คืนห้อง</td><td>{pd.to_datetime(bk_data['check_out']).strftime('%d/%m/%Y')}</td></tr>
                        <tr><td>สถานะ</td><td>จองเรียบร้อย</td></tr>
                    </table>

                    <div class="section">ค่าใช้จ่าย</div>
                    <table>
                        <tr><td>ค่าเช่าทั้งหมด</td><td class="amount">{float(bk_data['rent_amount'] or 0):,.2f} บาท</td></tr>
                        <tr><td>เงินมัดจำ</td><td class="amount">{float(bk_data['deposit'] or 0):,.2f} บาท</td></tr>
                    </table>

                    <div class="sign">
                        <div>ลงชื่อผู้จอง<br><br>........................................</div>
                        <div>ลงชื่อผู้รับจอง<br><br>........................................</div>
                    </div>
                    <div class="small">เอกสารฉบับนี้จัดทำจากข้อมูลการจองในระบบ</div>
                </div>
            </body>
            </html>
            """
            # ลบ indentation หน้า HTML เพื่อไม่ให้ Streamlit ตีความเป็น code block
            bk_html = textwrap.dedent(bk_html).strip()
            components.html(bk_html, height=950, scrolling=True)
            st.markdown(get_download_link(bk_html, f"ใบจอง_{bk_data['booking_no']}"), unsafe_allow_html=True)

    else:
        search_by = st.radio("ค้นหาด้วย", ["เลขที่เอกสาร", "รายการล่าสุด"])
        chk_data = None
        conn = sqlite3.connect(DB_FILE)

        if search_by == "เลขที่เอกสาร":
            inp = st.text_input("กรอกเลขที่ใบเสร็จหรือใบคืน")
            if inp:
                df = pd.read_sql(
                    """SELECT c.*, b.customer_name, b.building, b.unit_no, b.check_in, b.check_out, b.deposit
                       FROM checkouts c LEFT JOIN bookings b ON c.booking_no = b.booking_no
                       WHERE c.receipt_no = ? OR c.refund_no = ?""",
                    conn,
                    params=(inp.strip(), inp.strip()),
                )
                if not df.empty:
                    chk_data = df.iloc[0]
                else:
                    st.warning("ไม่พบ")
        else:
            recent = pd.read_sql(
                """SELECT c.receipt_no, c.refund_no, b.building, b.unit_no, b.customer_name
                   FROM checkouts c LEFT JOIN bookings b ON c.booking_no = b.booking_no
                   ORDER BY c.rowid DESC LIMIT 10""",
                conn,
            )
            if not recent.empty:
                sel = st.selectbox("เลือกรายการ", recent["receipt_no"] + " - " + recent["unit_no"] + " - " + recent["customer_name"])
                rec_no = sel.split(" - ")[0]
                df = pd.read_sql(
                    """SELECT c.*, b.customer_name, b.building, b.unit_no, b.check_in, b.check_out, b.deposit
                       FROM checkouts c LEFT JOIN bookings b ON c.booking_no = b.booking_no
                       WHERE c.receipt_no = ?""",
                    conn,
                    params=(rec_no,),
                )
                if not df.empty:
                    chk_data = df.iloc[0]
            else:
                st.info("ยังไม่มีรายการคืนห้อง")
        conn.close()

        if chk_data is not None:
            conn2 = sqlite3.connect(DB_FILE)
            damage_df = pd.read_sql(
                """SELECT item_no, item_name, condition_type, quantity, unit_price, amount
                   FROM checkout_damages WHERE checkout_id = ? ORDER BY id""",
                conn2,
                params=(chk_data["id"],),
            )
            conn2.close()

            damage_rows = damage_df.to_dict("records") if not damage_df.empty else []
            show_sel = st.radio("แสดง", ["ใบเสร็จ", "ใบคืนมัดจำ", "ทั้งคู่"])
            d = {
                "booking_no": chk_data["booking_no"],
                "building": chk_data["building"],
                "unit_no": chk_data["unit_no"],
                "customer_name": chk_data["customer_name"],
                "check_in": pd.to_datetime(chk_data["check_in"]).strftime("%d/%m/%Y"),
                "check_out": pd.to_datetime(chk_data["check_out"]).strftime("%d/%m/%Y"),
                "deposit": chk_data["deposit"],
                "water_meter_before": chk_data["water_meter_before"],
                "water_meter_after": chk_data["water_meter_after"],
                "water_rate": chk_data["water_rate"],
                "elec_meter_before": chk_data["elec_meter_before"],
                "elec_meter_after": chk_data["elec_meter_after"],
                "elec_rate": chk_data["elec_rate"],
                "cleaning_fee": chk_data["cleaning_fee"],
                "damage_fee": chk_data["damage_fee"],
                "other_fee": chk_data["other_fee"],
                "receipt_no": chk_data["receipt_no"],
                "refund_no": chk_data["refund_no"],
                "damage_rows": damage_rows,
                "water_meter_before_photo": chk_data.get("water_meter_before_photo"),
                "water_meter_after_photo": chk_data.get("water_meter_after_photo"),
                "elec_meter_before_photo": chk_data.get("elec_meter_before_photo"),
                "elec_meter_after_photo": chk_data.get("elec_meter_after_photo"),
            }

            if show_sel in ["ใบเสร็จ", "ทั้งคู่"]:
                st.subheader("ใบเสร็จรับเงิน")
                hr, _ = generate_receipt_html(d, "receipt")
                components.html(hr, height=760, scrolling=True)
                st.markdown(get_download_link(hr, f"ใบเสร็จ_{d['receipt_no']}"), unsafe_allow_html=True)

            if show_sel in ["ใบคืนมัดจำ", "ทั้งคู่"]:
                st.subheader("ใบคืนเงินมัดจำ")
                hf, _ = generate_receipt_html(d, "refund")
                components.html(hf, height=700, scrolling=True)
                st.markdown(get_download_link(hf, f"ใบคืนมัดจำ_{d['refund_no']}"), unsafe_allow_html=True)


# ==========================================================
# 5) ALL BOOKINGS
# ==========================================================
elif menu == "รายการจองทั้งหมด":
    st.header("รายการจองทั้งหมด")

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(
        """SELECT b.booking_no AS "เลขที่จอง", b.building AS "ตึก", b.unit_no AS "ห้อง",
                  b.customer_name AS "ชื่อลูกค้า", b.phone AS "เบอร์โทร",
                  b.check_in AS "วันที่เข้า", b.check_out AS "วันที่คืน",
                  b.rent_amount AS "ค่าเช่า", b.deposit AS "มัดจำ", b.status AS "สถานะ",
                  COALESCE(c.receipt_no, '') AS "เลขที่ใบเสร็จรับเงิน",
                  COALESCE(c.refund_no, '') AS "เลขที่ใบคืนมัดจำ"
           FROM bookings b
           LEFT JOIN checkouts c ON c.booking_no = b.booking_no
           ORDER BY b.check_in DESC""",
        conn,
    )
    booking_rows = pd.read_sql(
        """SELECT b.*,
                  COALESCE(c.receipt_no, '') AS receipt_no,
                  COALESCE(c.refund_no, '') AS refund_no
           FROM bookings b
           LEFT JOIN checkouts c ON c.booking_no = b.booking_no
           ORDER BY b.check_in DESC""",
        conn,
    )
    rooms = pd.read_sql(
        "SELECT building, unit_no FROM rooms ORDER BY building, unit_no", conn
    )
    conn.close()

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("✏️ แก้ไข / 🗑️ ลบรายการจอง")

    if booking_rows.empty:
        st.info("ยังไม่มีรายการจองให้แก้ไขหรือลบ")
    else:
        booking_labels = [
            f"{r['booking_no']} - {r['building']} - {r['unit_no']} - {r['customer_name']}"
            for _, r in booking_rows.iterrows()
        ]
        selected_label = st.selectbox("เลือกรายการจอง", booking_labels, key="booking_manage_select")
        selected_no = selected_label.split(" - ", 1)[0]
        selected = booking_rows[booking_rows["booking_no"] == selected_no].iloc[0]

        action = st.radio(
            "เลือกการทำรายการ",
            ["✏️ แก้ไขรายการจอง", "🗑️ ลบรายการจอง"],
            horizontal=True,
            key="booking_manage_action",
        )

        if action == "✏️ แก้ไขรายการจอง":
            building_options = rooms["building"].drop_duplicates().tolist()
            current_building = str(selected["building"])
            if current_building not in building_options:
                building_options.append(current_building)

            edit_bld = st.selectbox(
                "ตึก",
                building_options,
                index=building_options.index(current_building),
                key="edit_booking_building",
            )
            unit_options = rooms[rooms["building"] == edit_bld]["unit_no"].tolist()
            current_unit = str(selected["unit_no"])
            if current_unit not in unit_options:
                unit_options.append(current_unit)
            edit_unit = st.selectbox(
                "ห้อง",
                unit_options,
                index=unit_options.index(current_unit),
                key="edit_booking_unit",
            )

            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("ชื่อลูกค้า", value=str(selected["customer_name"] or ""), key="edit_booking_name")
                edit_type_options = ["Walk in", "Agent"]
                current_type = str(selected["customer_type"] or "Walk in")
                if current_type not in edit_type_options:
                    edit_type_options.append(current_type)
                edit_type = st.selectbox(
                    "ประเภทลูกค้า", edit_type_options,
                    index=edit_type_options.index(current_type),
                    key="edit_booking_type"
                )
                edit_phone = st.text_input("เบอร์โทร", value=str(selected["phone"] or ""), key="edit_booking_phone")

            with col2:
                edit_check_in = st.date_input(
                    "วันที่เข้าพัก",
                    value=pd.to_datetime(selected["check_in"]).date(),
                    key="edit_booking_checkin",
                )
                edit_check_out = st.date_input(
                    "วันที่คืนห้อง",
                    value=pd.to_datetime(selected["check_out"]).date(),
                    key="edit_booking_checkout",
                )
                edit_rent = st.number_input(
                    "ค่าเช่าทั้งหมด", min_value=0.0, step=100.0,
                    value=float(selected["rent_amount"] or 0), key="edit_booking_rent"
                )
                edit_deposit = st.number_input(
                    "เงินมัดจำ", min_value=0.0, step=100.0,
                    value=float(selected["deposit"] or 0), key="edit_booking_deposit"
                )

            st.caption(f"เลขที่จอง: {selected_no} (เลขที่จองจะไม่เปลี่ยน) | สถานะ: {selected['status']}")

            if st.button("💾 บันทึกการแก้ไขรายการจอง", type="primary", key="save_booking_edit"):
                if not edit_name.strip():
                    st.error("กรุณากรอกชื่อลูกค้า")
                elif edit_check_in >= edit_check_out:
                    st.error("วันที่คืนต้องมาหลังวันที่เข้า")
                else:
                    conn = sqlite3.connect(DB_FILE)
                    try:
                        c = conn.cursor()
                        c.execute(
                            """UPDATE bookings
                               SET building = ?, unit_no = ?, customer_name = ?, customer_type = ?,
                                   phone = ?, check_in = ?, check_out = ?, rent_amount = ?, deposit = ?
                               WHERE booking_no = ?""",
                            (
                                edit_bld, edit_unit, edit_name.strip(), edit_type, edit_phone.strip(),
                                edit_check_in.isoformat(), edit_check_out.isoformat(),
                                edit_rent, edit_deposit, selected_no,
                            ),
                        )
                        conn.commit()
                        st.success(f"แก้ไขรายการจอง {selected_no} เรียบร้อยแล้วค่ะ")
                        st.rerun()
                    except sqlite3.Error as exc:
                        conn.rollback()
                        st.error(f"ไม่สามารถแก้ไขรายการจองได้: {exc}")
                    finally:
                        conn.close()

        else:
            has_checkout = bool(selected["receipt_no"] or selected["refund_no"] or str(selected["status"]) == "checked_out")
            if has_checkout:
                st.warning(
                    f"รายการ {selected_no} มีรายการคืนห้อง/เอกสารที่ผูกอยู่แล้ว "
                    "การลบจะลบข้อมูลคืนห้อง ใบเสร็จ ใบคืนมัดจำ และรายการของเสียหายที่ผูกกับการจองนี้ด้วย"
                )
            else:
                st.info("รายการนี้ยังไม่มีการคืนห้อง การลบจะลบเฉพาะรายการจองนี้")

            confirm_delete = st.checkbox(
                "ฉันยืนยันว่าต้องการลบรายการจองนี้",
                key="confirm_delete_booking",
            )

            if st.button("🗑️ ลบรายการจอง", type="secondary", key="delete_booking"):
                if not confirm_delete:
                    st.error("กรุณาติ๊กยืนยันก่อนลบรายการจอง")
                else:
                    conn = sqlite3.connect(DB_FILE)
                    try:
                        c = conn.cursor()
                        checkout_ids = [
                            row[0] for row in c.execute(
                                "SELECT id FROM checkouts WHERE booking_no = ?", (selected_no,)
                            ).fetchall()
                        ]
                        for checkout_id in checkout_ids:
                            c.execute("DELETE FROM checkout_damages WHERE checkout_id = ?", (checkout_id,))
                        c.execute("DELETE FROM checkouts WHERE booking_no = ?", (selected_no,))
                        c.execute("DELETE FROM bookings WHERE booking_no = ?", (selected_no,))
                        conn.commit()
                        st.success(f"ลบรายการจอง {selected_no} เรียบร้อยแล้วค่ะ")
                        st.rerun()
                    except sqlite3.Error as exc:
                        conn.rollback()
                        st.error(f"ไม่สามารถลบรายการจองได้: {exc}")
                    finally:
                        conn.close()