import json
import zipfile
from pathlib import Path
from lxml import etree

def _remove_linesegarray(data, replacements):
    """
    XML bytes에서 replacements가 적용된 문단의 linesegarray 제거
    텍스트 변경 후 한글이 문단의 줄배치를 다시 계산하도록 처리
    """
    parser = etree.XMLParser(remove_blank_text=False)

    root = etree.fromstring(data, parser)

    # 모든 문단
    paragraphs = root.xpath('.//*[local-name()="p"]')

    for paragraph in paragraphs:
        # 문단 내부 모든 텍스트
        text_nodes = paragraph.xpath('.//*[local-name()="t"]')

        paragraph_text = "".join(node.text or "" for node in text_nodes)

        # 치환값이 있는 문단인지 확인
        changed = False

        for old, new in replacements.items():
            new = str(new)

            if new and new in paragraph_text:
                changed = True
                break

        if not changed:
            continue

        # 기존 줄 배치 정보 제거
        line_seg_arrays = paragraph.xpath('./*[local-name()="linesegarray"]')

        for line_seg_array in line_seg_arrays:
            paragraph.remove(line_seg_array)


    # 반드시 bytes 반환
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)




def replace_hwpx(template_path, output_path, replacements):

    template_path = Path(template_path)
    output_path = Path(output_path)

    # JSON String을 Dictionary로 변환
    if isinstance(replacements, str):
        replacements = json.loads(replacements)


    with zipfile.ZipFile(template_path, "r") as zin:

        with zipfile.ZipFile(output_path, "w") as zout:

            for item in zin.infolist():
                data = zin.read(item.filename)

                # placeholder 치환
                if item.filename.endswith(".xml"):
                    
                    try:
                        text = data.decode("utf-8")

                        for old, new in replacements.items():
                            text = text.replace(old, str(new))

                        data = text.encode("utf-8")

                        # 치환된 문단의 linesegarray 제거
                        data = _remove_linesegarray(data, replacements)
                    
                    except (UnicodeDecodeError, etree.XMLSyntaxError):
                        # XML 아닌 특수 XML은 기존 데이터 그대로 유지
                        pass
                
                zout.writestr(item, data)


    return "success"




if __name__ == "__main__":

    template_path = r"C:\Data\Temp\개최계획서_양식.hwpx"
    output_path = r"C:\Data\Temp\개최계획서_양식_test.hwpx"

    replacements = {
        "{{학교명}}": "옥산초등학교",
        "{{접수번호}}": "옥산초등학교 2026-01",
        "{{사안유형}}": "언어폭력",
        "{{피해대가해}}": "1대1",
        "{{가해추정일람표}}": "아러아ㅣ럳니ㅏ러다러다ㅓㄹ아러ㄴ아러ㅏ인러ㅓㅓㅓㅓㅓㅓㅓㄹ나ㅣㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓㅓ아러덜다럳러다ㅓ라러아;펊 ㅓㅓㅏㅓㄹ아ㅓㄴㄹㅇ니ㅏ얼아러아니러ㅏㅇ러이러아러아ㅣㄹ"
    }

    replace_hwpx(
        template_path,
        output_path,
        replacements
    )

    print(f"완료: {output_path}")
