import re
import shutil
import zipfile
from pathlib import Path
from lxml import etree
from schift_ko_pii import detect


# ============================================
# 1. 정규식 (전화번호)
# ============================================
PHONE_PATTERN = re.compile(
    r'(?<!\d)'
    r'(?:'
        r'01[016789]-?\d{3,4}-?\d{4}'
        r'|02-?\d{3,4}-?\d{4}'
        r'|0[3-6][1-5]-?\d{3,4}-?\d{4}'
    r')'
    r'(?:\s*,\s*\d{4})*'
    r'(?!\d)'
)


# ============================================
# 2. 인명 사전
# ============================================
FAMILY_DICT_PATH = Path(r"C:\Users\dhkim\OneDrive\문서\UiPath\01_WriteReport\Data\family_dict.txt")

def load_family_dictionary(path):
    with open(path, "r", encoding="utf-8") as file:
        schools = {
            line.strip()
            for line in file
            if line.strip()
        }

    return sorted(schools, key=len, reverse=True)



def replace_family(text, family_dictionary):
    for school in family_dictionary:

        if school not in text:
            continue

        masked = "O" * len(school)

        text = text.replace(
            school,
            masked
        )

        print(
            f"학교 마스킹: {school} → {masked}"
        )

    return text



def anonymize_text(text, family_dictionary):

    original_text = text

    # ----------------------------------------
    # 1. 인명 마스킹
    # ----------------------------------------
    entities = detect(
        text,
        postprocess=False
    )

    person_entities = [
        entity
        for entity in entities
        if entity["label"] == "private_person"
    ]

    # 뒤에서부터 치환
    for entity in reversed(person_entities):

        start = entity["start"]
        end = entity["end"]

        original_name = entity["text"]

        # 원문 글자 수만큼 O 생성
        masked = "O" * len(original_name)

        print(
            f"인명 마스킹: {original_name} → {masked}"
        )

        text = (text[:start] + masked + text[end:]
        )


    # ----------------------------------------
    # 2. 학교명 마스킹
    # ----------------------------------------
    text = replace_school(text,family_dictionary)


    # ----------------------------------------
    # 3. 전화번호 마스킹
    # ----------------------------------------
    def replace_phone(match):

        original_phone = match.group(0)

        # 숫자만 O로 변경
        # 하이픈, 쉼표, 공백은 그대로 유지
        masked_phone = re.sub(r'\d', 'O', original_phone)

        print(f"전화번호 마스킹: "f"{original_phone} → {masked_phone}")

        return masked_phone

    text = PHONE_PATTERN.sub(replace_phone, text)

    # ----------------------------------------
    # 변경 내용 출력
    # ----------------------------------------
    if original_text != text:

        print(f"텍스트 변경: "f"[{original_text}] → [{text}]"
        )

    return text



def anonymize_hwpx(input_path, output_path):

    input_path = Path(input_path)
    output_path = Path(output_path)

    print("HWPX 마스킹 시작")

    # ----------------------------------------
    # 입력 파일 확인
    # ----------------------------------------
    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")

    print(f"입력 파일: {input_path}")
    print(f"출력 파일: {output_path}")


    # ----------------------------------------
    # 학교 사전 확인
    # ----------------------------------------
    if not FAMILY_DICT_PATH.exists():
        raise FileNotFoundError(f"가족 사전 파일을 찾을 수 없습니다: "f"{FAMILY_DICT_PATH}")

    # ----------------------------------------
    # 학교 사전 로드
    # ----------------------------------------
    family_dictionary = load_family_dictionary(FAMILY_DICT_PATH)

    print(f"학교 사전 로드 완료: "f"{len(family_dictionary)}개")


    # ----------------------------------------
    # 임시 폴더
    # ----------------------------------------
    temp_dir = (
        output_path.parent
        / f"{input_path.stem}_temp"
    )

    if temp_dir.exists():

        print(
            f"기존 임시 폴더 삭제: {temp_dir}"
        )

        shutil.rmtree(temp_dir)

    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"임시 폴더 생성: {temp_dir}"
    )

    # ----------------------------------------
    # HWPX 압축 해제
    # ----------------------------------------

    print("HWPX 압축 해제 중...")

    with zipfile.ZipFile(
        input_path,
        "r"
    ) as zip_file:

        zip_file.extractall(
            temp_dir
        )

    print("HWPX 압축 해제 완료")

    # ----------------------------------------
    # XML 파일 검색
    # ----------------------------------------

    xml_files = list(
        temp_dir.rglob("*.xml")
    )

    print(
        f"XML 파일 개수: {len(xml_files)}"
    )

    total_changed = 0

    # ----------------------------------------
    # XML 처리
    # ----------------------------------------

    for xml_file in xml_files:

        print()
        print(
            f"XML 처리: {xml_file.name}"
        )

        try:

            tree = etree.parse(
                str(xml_file)
            )

            changed = False

            for element in tree.iter():

                if not element.text:
                    continue

                original_text = element.text

                replaced_text = anonymize_text(
                    original_text,
                    family_dictionary
                )

                if original_text != replaced_text:

                    element.text = replaced_text

                    changed = True

            # ----------------------------------------
            # XML 저장
            # ----------------------------------------

            if changed:

                tree.write(
                    str(xml_file),
                    encoding="UTF-8",
                    xml_declaration=True
                )

                total_changed += 1

                print(
                    f"XML 저장 완료: {xml_file.name}"
                )

            else:

                print(
                    "변경 내용 없음"
                )

        except Exception as error:

            print(
                f"XML 처리 실패: {xml_file}"
            )

            print(
                f"에러 타입: {type(error).__name__}"
            )

            print(
                f"에러 내용: {error}"
            )

    # ----------------------------------------
    # HWPX 재압축
    # ----------------------------------------

    print()
    print("HWPX 재압축 시작")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with zipfile.ZipFile(
        output_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zip_file:

        for file in temp_dir.rglob("*"):

            if not file.is_file():
                continue

            arcname = file.relative_to(temp_dir)

            zip_file.write(file,arcname)

    print("HWPX 재압축 완료")

    # ----------------------------------------
    # 임시 폴더 삭제
    # ----------------------------------------
    if temp_dir.exists():

        shutil.rmtree(
            temp_dir
        )

        print(
            "임시 폴더 삭제 완료"
        )

    # ----------------------------------------
    # 완료
    # ----------------------------------------
    print("HWPX 마스킹 완료")

    print(f"변경된 XML: {total_changed}개")

    print(f"결과 파일: {output_path}")

    return "success"


# ============================================
# 실행
# ============================================
if __name__ == "__main__":
    input_file = Path(r"C:\Data\회의록 비식별화\9-1. 제96차 학교폭력대책심의회 회의록.hwpx")
    output_file = Path(r"C:\Data\회의록 비식별화\Output\9-1. 제96차 학교폭력대책심의회 회의록.hwpx")

    anonymize_hwpx(input_file, output_file)