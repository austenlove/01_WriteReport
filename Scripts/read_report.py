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


    # print("\n".join(texts))

    return "\n".join(texts)



# ============================================
# QWEN 추출
# ============================================
def ask_qwen(text):
    prompt = f"""
    문서에서 다음 정보를 추출하여 JSON으로 출력하라.

    규칙:
    - 문서에 실제로 있는 내용만 사용한다.
    - 추측하거나 내용을 만들어내지 않는다.
    - 원문의 값을 그대로 사용한다.

    [추출 대상]
    - "사안 개요[신고내용]"과 "조사 요약 내용"을 참고한다.
    - 사건의 핵심 내용을 2~3문장으로 요약한다.
    - 문서에 없는 사실은 추가하지 않는다.
    - 6하 원칙에 맞추어 개두식으로 작성한다.
    - 쌍방 폭력에 해당할 경우 해당여부를 명시한다.

    문서:
    {text}
    """

    print("qwen 응답 요청 시작")

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen3:0.6b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0
            }
        }
    )

    print("qwen 응답 요청 종료")

    response.raise_for_status()

    return response.json()["response"]



if __name__ == "__main__":
    input_file = Path("C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/사안조사 보고서2026-02.hwpx")

    text = extract_hwpx_text(input_file)

    # print(ask_qwen(text))


    