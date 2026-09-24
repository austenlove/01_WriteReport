import re
import zipfile
from pathlib import Path
from lxml import etree
import json
import requests

# ============================================
# HWPX 텍스트 추출
# ============================================
def extract_hwpx_text(file_path):
    texts = []

    with zipfile.ZipFile(file_path, "r") as z:
        xml_files = [
            name for name in z.namelist()
            if name.startswith("Contents/") and name.endswith(".xml")
        ]

        for xml_file in xml_files:
            xml_data = z.read(xml_file)

            try:
                root = etree.fromstring(xml_data)
            except Exception:
                continue

            for elem in root.iter():
                if elem.tag.endswith("}t") or elem.tag == "t":
                    if elem.text:
                        texts.append(elem.text)

    return "\n".join(texts)



    


    