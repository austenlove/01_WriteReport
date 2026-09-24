import re
import json
import zipfile
from pathlib import Path
from lxml import etree
from schift_ko_pii import detect


# ============================================
# 1. 정규식 (전화번호)
# ============================================
SCHOOL_PATTERN = re.compile(
    r'[가-힣0-9A-Za-z·ㆍ\-]{1,30}'
    r'(?:초등학교|중학교|고등학교)'
    r'(?![가-힣])'
)

PHONE_PATTERN = re.compile(
    r'(?<!\d)'
    r'(?:01[016789]-?\d{3,4}-?\d{4}'
    r'|02-?\d{3,4}-?\d{4}'
    r'|0[3-6][1-5]-?\d{3,4}-?\d{4})'
    r'(?!\d)'
)



# ============================================
# 2. 매핑 관리
# ============================================
class MappingManager:

    def __init__(self):
        self.mapping = {}
        self.person_count = 0
        self.school_count = 0
        self.tel_count = 0

    # 인명 매핑
    def add_person(self, original):
        for key, value in self.mapping.items():
            if (value["type"] == "PERSON" and value["original"] == original):
                print(f"기존 인명 매핑 사용: {original} → {key}")
                return key

        self.person_count += 1
        masked = f"PERSON_{self.person_count:03d}"

        self.mapping[masked] = {
            "type" : "PERSON",
            "original" : original
        }

        print(f"---- 인명 탐지: {original} → {masked}")
        return masked


    # 학교명 매핑
    def add_school(self, original): 
        for key, value in self.mapping.items():
            if (value["type"] == "SCHOOL" and value["original"] == original):
                print(f"기존 학교명 매핑 사용: {original} → {key}")
                return key

        self.school_count += 1
        masked = f"SCHOOL_{self.school_count:03d}"

        self.mapping[masked] = { 
            "type": "SCHOOL",
            "original": original
        }

        print(f"---- 학교명 탐지: {original} → {masked}")
        return masked

        
    # 전화번호 매핑
    def add_tel(self, original): 
        for key, value in self.mapping.items():
            if ( value["type"] == "TEL" and value["original"] == original ):
                return key

        self.tel_count += 1
        masked = f"TEL_{self.tel_count:03d}"

        self.mapping[masked] = { 
            "type": "TEL",
            "original": original
        }

        print(f"---- 전화번호 탐지: {original} → {masked}")
        return masked


    # JSON 변환
    def save(self, path):
        with open(path, "w", encoding="utf-8") as f: 
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)
            print(f"매핑 JSON 저장 완료: {path}")




# ============================================================
# # 3. 텍스트 비식별화
# ============================================================ 
def anonymize_text(text, manager):

    original_text = text

    # 인명 NER 
    entities = detect(text, postprocess=False)

    person_entities = [
        entity
        for entity in entities
        if entity["label"] == "private_person"
    ]

    for entity in reversed(person_entities):
        start = entity["start"]
        end = entity["end"]
        actual_text = text[start:end]
        original_name = entity["text"]
        print( f"NER 인명: [{original_name}] " f"위치: {start}~{end} " f"실제문자열: [{actual_text}]" )

        masked = manager.add_person(original_name)
        text = (text[:start] + masked + text[end:])
        print( f"NER 치환: " f"[{original_name}] → [{masked}]" )


    # 학교명
    def replace_school(match):
        original_school = match.group(0).strip()

        if not original_school:
            return match.group(0)
        
        masked = manager.add_school(original_school)
        return masked
    text = SCHOOL_PATTERN.sub(replace_school, text)


    # 전화번호
    def replace_phone(match):
        original_phone = match.group(0)
        return manager.add_tel(original_phone)
    text = PHONE_PATTERN.sub(replace_phone, text)


    # 텍스트가 변경된 경우 로그 출력
    '''
    if original_text != text:
        print( f"=====> 텍스트 변경: " f"'{original_text}' → '{text}'" )
    '''
    return text




# ============================================================
# # 4. HWPX 처리
# ============================================================ 
def anonymize_hwpx(input_path, output_path, mapping_path):

    input_path = Path(input_path)
    output_path = Path(output_path)
    mapping_path = Path(mapping_path)

    print("HWPX 비식별화 시작")

    manager = MappingManager()


    # 임시 폴더 생성
    temp_dir = output_path.parent / f"{input_path.stem}_temp"
    print(f"임시폴더 생성 완료: {temp_dir}")

    # hwpx 압축 해제
    with zipfile.ZipFile(input_path, "r") as zip_file:
        zip_file.extractall(temp_dir)
    print("HWPX 압축 해제 완료")

    # XML 파일 검색
    xml_files = list(temp_dir.rglob("*.xml"))
    print(f"XML 파일 개수: {len(xml_files)}")



    # ***XML 파일 처리*** 
    for xml_file in xml_files:

        print(f"- XML 처리: {xml_file.name}")

        try:
            tree = etree.parse(str(xml_file))
            changed = False

            for element in tree.iter():

                if not element.text:
                    continue

                if element.text == "":
                    continue

                original_text = element.text

                replaced_text = anonymize_text(original_text, manager)

                # 변경된 경우 텍스트 교체
                if original_text != replaced_text:
                    element.text = replaced_text
                    changed = True

            # 변경된 XML 저장
            if changed:
                print(F"XML 변경여부 : {changed}")
                tree.write(str(xml_file), encoding="UTF-8", xml_declaration=True)
                print("XML 저장 완료")

        except Exception as error:
            print(f"XML 처리 실패: {xml_file}")
            print(error)


    # HWPX 재압축
    print("HWPX 재압축 시작")
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:

        for file in temp_dir.rglob("*"):

            if not file.is_file():
                continue
            
            arcname = file.relative_to(temp_dir)
            zip_file.write(file, arcname)

    print("HWPX 재압축 종료")


    # 매핑 json 저장
    manager.save(mapping_path)

    print("HWPX 비식별화 종료")
    print(f"결과 문서: {output_path}")
    print(f"매핑 파일: {mapping_path}")

    return "success"
    



if __name__ == "__main__":
    input_file = Path("C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/Input/조치결정통보서_sample.hwpx")
    output_file = Path("C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/Output/조치결정통보서_sample.hwpx")
    mapping_file = Path("C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/Output/조치결정통보서_sample_mapping.json")

    anonymize_hwpx(input_file, output_file, mapping_file)
