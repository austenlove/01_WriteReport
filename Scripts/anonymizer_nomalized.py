import re
import json
import zipfile
from pathlib import Path
from lxml import etree
from schift_ko_pii import detect


# ============================================
# 1. 정규식
# ============================================
PHONE_PATTERN = re.compile(
    r'(?<!\d)'
    r'(?:01[016789]-?\d{3,4}-?\d{4}'
    r'|02-?\d{3,4}-?\d{4}'
    r'|0[3-6][1-5]-?\d{3,4}-?\d{4})'
    r'(?!\d)'
)


# ============================================
# 2. 학교 사전
# ============================================
SCHOOL_DICT_PATH = Path(
    "C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/school_dict.txt"
)


def load_school_dictionary(path):
    with open(path, "r", encoding="utf-8") as file:
        schools = {
            line.strip()
            for line in file
            if line.strip()
        }

    return sorted(
        schools,
        key=len,
        reverse=True
    )


# ============================================
# 3. 매핑 관리
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
            if (
                value["type"] == "PERSON"
                and value["original"] == original
            ):
                print(
                    f"기존 인명 매핑 사용: "
                    f"{original} → {key}"
                )
                return key

        self.person_count += 1
        masked = f"PERSON_{self.person_count:03d}"

        self.mapping[masked] = {
            "type": "PERSON",
            "original": original
        }

        print(
            f"---- 인명 탐지: "
            f"{original} → {masked}"
        )

        return masked

    # 학교명 매핑
    def add_school(self, original):
        for key, value in self.mapping.items():
            if (
                value["type"] == "SCHOOL"
                and value["original"] == original
            ):
                print(
                    f"기존 학교명 매핑 사용: "
                    f"{original} → {key}"
                )
                return key

        self.school_count += 1
        masked = f"SCHOOL_{self.school_count:03d}"

        self.mapping[masked] = {
            "type": "SCHOOL",
            "original": original
        }

        print(
            f"---- 학교명 탐지: "
            f"{original} → {masked}"
        )

        return masked

    # 전화번호 매핑
    def add_tel(self, original):
        for key, value in self.mapping.items():
            if (
                value["type"] == "TEL"
                and value["original"] == original
            ):
                return key

        self.tel_count += 1
        masked = f"TEL_{self.tel_count:03d}"

        self.mapping[masked] = {
            "type": "TEL",
            "original": original
        }

        print(
            f"---- 전화번호 탐지: "
            f"{original} → {masked}"
        )

        return masked

    # JSON 저장
    def save(self, path):
        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                self.mapping,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"매핑 JSON 저장 완료: {path}"
        )


# ============================================
# 4. 탐지용 텍스트 생성
# ============================================
def build_normalized_text(elements):
    normalized_text = ""
    position_map = []

    for element in elements:
        text = element.text or ""

        for char_index, char in enumerate(text):

            if char.isspace():
                continue

            position_map.append(
                (element, char_index)
            )

            normalized_text += char

    return normalized_text, position_map


# ============================================
# 5. 탐지 결과를 원본 XML 위치로 변환
# ============================================
def replace_entity(
    elements,
    position_map,
    start,
    end,
    masked
):
    target_positions = position_map[start:end]

    if not target_positions:
        return

    first_element = target_positions[0][0]

    first_index = target_positions[0][1]

    last_element = target_positions[-1][0]

    last_index = target_positions[-1][1]

    # 하나의 hp:t 안에 있는 경우
    if first_element is last_element:

        text = first_element.text or ""

        first_element.text = (
            text[:first_index]
            + masked
            + text[last_index + 1:]
        )

        return

    # 여러 hp:t에 걸쳐 있는 경우
    first_text = first_element.text or ""

    last_text = last_element.text or ""

    first_element.text = (
        first_text[:first_index]
        + masked
    )

    last_element.text = (
        last_text[last_index + 1:]
    )

    # 중간 element 제거
    started = False

    for element in elements:

        if element is first_element:
            started = True
            continue

        if element is last_element:
            break

        if started:
            element.text = ""


# ============================================
# 6. 학교명 탐지
# ============================================
def find_school_entities(
    text,
    school_dictionary
):
    entities = []

    for school in school_dictionary:

        start = 0

        while True:

            index = text.find(
                school,
                start
            )

            if index == -1:
                break

            entities.append({
                "start": index,
                "end": index + len(school),
                "text": school,
                "type": "SCHOOL"
            })

            start = index + len(school)

    return entities


# ============================================
# 7. 텍스트 비식별화
# ============================================
def anonymize_elements(
    elements,
    manager,
    school_dictionary
):
    normalized_text, position_map = (
        build_normalized_text(elements)
    )

    if not normalized_text:
        return False

    print(
        f"탐지용 텍스트: "
        f"[{normalized_text}]"
    )

    entities = []

    # ----------------------------------------
    # 인명 NER
    # ----------------------------------------
    ner_entities = detect(
        normalized_text,
        postprocess=False
    )

    for entity in ner_entities:

        if entity["label"] != "private_person":
            continue

        entities.append({
            "start": entity["start"],
            "end": entity["end"],
            "text": entity["text"],
            "type": "PERSON"
        })

    # ----------------------------------------
    # 학교명
    # ----------------------------------------
    school_entities = find_school_entities(
        normalized_text,
        school_dictionary
    )

    entities.extend(
        school_entities
    )

    # ----------------------------------------
    # 전화번호
    # ----------------------------------------
    for match in PHONE_PATTERN.finditer(
        normalized_text
    ):
        entities.append({
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0),
            "type": "TEL"
        })

    if not entities:
        return False

    # ----------------------------------------
    # 겹치는 entity 제거
    # ----------------------------------------
    entities.sort(
        key=lambda x: (
            x["start"],
            -(x["end"] - x["start"])
        )
    )

    filtered_entities = []

    last_end = -1

    for entity in entities:

        if entity["start"] < last_end:
            continue

        filtered_entities.append(
            entity
        )

        last_end = entity["end"]

    # 뒤에서부터 치환
    for entity in reversed(
        filtered_entities
    ):

        start = entity["start"]
        end = entity["end"]
        original = entity["text"]
        entity_type = entity["type"]

        if entity_type == "PERSON":

            masked = manager.add_person(
                original
            )

        elif entity_type == "SCHOOL":

            masked = manager.add_school(
                original
            )

        elif entity_type == "TEL":

            masked = manager.add_tel(
                original
            )

        else:
            continue

        print(
            f"치환: "
            f"[{original}] → [{masked}]"
        )

        replace_entity(
            elements,
            position_map,
            start,
            end,
            masked
        )

    return True


# ============================================
# 8. HWPX 처리
# ============================================
def anonymize_hwpx(
    input_path,
    output_path,
    mapping_path
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    mapping_path = Path(mapping_path)

    print("HWPX 비식별화 시작")

    manager = MappingManager()

    # 학교 사전 로드
    school_dictionary = (
        load_school_dictionary(
            SCHOOL_DICT_PATH
        )
    )

    print(
        f"학교명 사전 로드 완료: "
        f"{len(school_dictionary)}개"
    )

    # 임시 폴더 생성
    temp_dir = (
        output_path.parent
        / f"{input_path.stem}_temp"
    )

    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)

    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"임시폴더 생성 완료: "
        f"{temp_dir}"
    )

    # HWPX 압축 해제
    with zipfile.ZipFile(
        input_path,
        "r"
    ) as zip_file:
        zip_file.extractall(
            temp_dir
        )

    print("HWPX 압축 해제 완료")

    # XML 파일 검색
    xml_files = list(
        temp_dir.rglob("*.xml")
    )

    print(
        f"XML 파일 개수: "
        f"{len(xml_files)}"
    )

    # XML 처리
    for xml_file in xml_files:

        print(
            f"- XML 처리: "
            f"{xml_file.name}"
        )

        try:

            tree = etree.parse(
                str(xml_file)
            )

            changed = False

            # hp:p 단위 처리
            for paragraph in tree.iter():

                if not paragraph.tag.endswith(
                    "p"
                ):
                    continue

                text_elements = []

                for element in paragraph.iter():

                    if not element.tag.endswith(
                        "t"
                    ):
                        continue

                    if element.text is None:
                        continue

                    text_elements.append(
                        element
                    )

                if not text_elements:
                    continue

                paragraph_changed = (
                    anonymize_elements(
                        text_elements,
                        manager,
                        school_dictionary
                    )
                )

                if paragraph_changed:
                    changed = True

            # 변경된 XML 저장
            if changed:

                print(
                    f"XML 변경여부: "
                    f"{changed}"
                )

                tree.write(
                    str(xml_file),
                    encoding="UTF-8",
                    xml_declaration=True
                )

                print(
                    "XML 저장 완료"
                )

        except Exception as error:

            print(
                f"XML 처리 실패: "
                f"{xml_file}"
            )

            print(error)

    # HWPX 재압축
    print(
        "HWPX 재압축 시작"
    )

    with zipfile.ZipFile(
        output_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zip_file:

        for file in temp_dir.rglob("*"):

            if not file.is_file():
                continue

            arcname = file.relative_to(
                temp_dir
            )

            zip_file.write(
                file,
                arcname
            )

    print(
        "HWPX 재압축 종료"
    )

    # 매핑 JSON 저장
    manager.save(
        mapping_path
    )

    print(
        "HWPX 비식별화 종료"
    )

    print(
        f"결과 문서: "
        f"{output_path}"
    )

    print(
        f"매핑 파일: "
        f"{mapping_path}"
    )

    return "success"


# ============================================
# 9. 실행
# ============================================
if __name__ == "__main__":

    input_file = Path(
        "C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/Input/사안조사보고서_sample.hwpx"
    )

    output_file = Path(
        "C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/Output/사안조사보고서_sample.hwpx"
    )

    mapping_file = Path(
        "C:/Users/dhkim/OneDrive/문서/UiPath/전북군산교육청/Data/Output/사안조사보고서_sample.json"
    )

    anonymize_hwpx(
        input_file,
        output_file,
        mapping_file
    )

