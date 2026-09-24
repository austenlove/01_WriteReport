from schift_ko_pii import detect

print("NER 테스트 시작")

texts = [ 
    "(김철수, 김영희) 신고된 행위를 한 사실이 전혀 없다고 부인함"
]

print("detect 시작")

for text in texts: 
    print()
    print("=" * 60)
    print(f"원문: {text}")

    # 결과 변수에 담기 : result
    results = detect(text, postprocess=False)

    if not results:
        print("탐지 결과 없음")
        continue

    for result in results: 
        print( 
            f"탐지: [{result['text']}] " 
            f"→ {result['label']} " 
            f"(score={result['score']:.3f}) " 
            f"({result['start']}~{result['end']})"
        )

print("detect 종료")