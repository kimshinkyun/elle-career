# 올인원_처리.py 의 has() 함수 버그 수정 패치
import re

with open('올인원_처리.py', 'r', encoding='utf-8') as f:
    code = f.read()

# has() 함수 전체를 새 버전으로 교체
pattern = r'def has\(col\):.*?return s != ""'
new_has = '''def has(col):
    if col is None:
        return pd.Series([False] * len(df))
    result = df[col].str.strip() != ""
    if col == c_email1:
        for extra in [c_email2, find_col(df, ["이메일3"])]:
            if extra:
                result = result | (df[extra].str.strip() != "")
    if col == c_fax1 and c_fax2:
        result = result | (df[c_fax2].str.strip() != "")
    return result'''

new_code = re.sub(pattern, new_has, code, flags=re.DOTALL)

if new_code != code:
    with open('올인원_처리.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    print("패치 완료! 이제 python 올인원_처리.py 를 실행하세요.")
else:
    print("이미 수정되어 있습니다. 직접 실행하세요:")
    print("  python 올인원_처리.py")
