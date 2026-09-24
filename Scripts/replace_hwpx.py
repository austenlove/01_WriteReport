import json
import zipfile
from pathlib import Path


def replace_hwpx(template_path, output_path, replacements):

    template_path = Path(template_path)
    output_path = Path(output_path)

    # UiPath에서 넘어온 JSON String을 Dictionary로 변환
    if isinstance(replacements, str):
        replacements = json.loads(replacements)


    with zipfile.ZipFile(template_path, "r") as zin:
        with zipfile.ZipFile(output_path, "w") as zout:

            for item in zin.infolist():

                data = zin.read(item.filename)

                if item.filename.endswith(".xml"):

                    text = data.decode("utf-8")

                    for old, new in replacements.items():
                        text = text.replace(old, str(new))

                    data = text.encode("utf-8")

                zout.writestr(item, data)


    return "success"




if __name__ == "__main__":

    template_path = r"C:\Users\dhkim\OneDrive\문서\UiPath\전북군산교육청\Data\Temp\개최계획서_양식.hwpx"
    output_path = r"C:\Users\dhkim\OneDrive\문서\UiPath\전북군산교육청\Data\Temp\개최계획서_양식_test.hwpx"

    replacements = {
        "{{학교명}}": "옥산초등학교",
        "{{접수번호}}": "옥산초등학교 2026-01",
        "{{사안유형}}": "언어폭력",
        "{{피해대가해}}": "1대1"
    }

    replace_hwpx(
        template_path,
        output_path,
        replacements
    )

    print(f"완료: {output_path}")
