"""Mini NPU Simulator: 외부 라이브러리 없이 구현한 MAC 기반 패턴 판별기.

Python 3.8 이상에서 실행: python main.py
"""

import json
import math
import re
import time
from pathlib import Path

EPSILON = 1e-9
REPEATS = 10
DATA_PATH = Path(__file__).with_name("data.json")
PATTERN_KEY = re.compile(r"size_(\d+)_(\d+)")


def normalize_label(label):
    """JSON의 여러 표기를 내부 표준 라벨 'Cross', 'X'로 변환한다."""
    if not isinstance(label, str):
        return None
    value = label.strip().lower()
    if value in ("+", "cross"):
        return "Cross"
    if value == "x":
        return "X"
    return None


def validate_matrix(matrix, size, name):
    """정사각형 배열의 크기와 숫자 타입을 확인해 float 배열을 반환한다."""
    if not isinstance(matrix, list) or len(matrix) != size:
        raise ValueError(f"{name}: 행 개수가 {size}개여야 합니다.")

    result = []
    for row_number, row in enumerate(matrix, start=1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError(
                f"{name}: {row_number}행의 열 개수가 {size}개여야 합니다."
            )
        converted = []
        for column_number, value in enumerate(row, start=1):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"{name}: {row_number}행 {column_number}열은 숫자여야 합니다."
                )
            try:
                number = float(value)
            except (OverflowError, ValueError):
                raise ValueError(f"{name}: 표현할 수 없는 숫자가 있습니다.") from None
            if not math.isfinite(number):
                raise ValueError(f"{name}: NaN/무한대 값은 허용하지 않습니다.")
            converted.append(number)
        result.append(converted)
    return result


def read_matrix(name, size=3):
    """콘솔에서 N줄의 숫자를 읽는다. 잘못된 행은 다시 입력받는다."""
    print(f"\n{name} ({size}줄 입력, 공백 구분)")
    matrix = []
    for index in range(size):
        while True:
            raw = input(f"  {index + 1}행> ").strip().split()
            if len(raw) != size:
                print(f"입력 형식 오류: 각 줄에 {size}개의 숫자를 공백으로 구분해 입력하세요.")
                continue
            try:
                row = [float(value) for value in raw]
            except ValueError:
                print("입력 형식 오류: 숫자만 입력하세요.")
                continue
            if not all(math.isfinite(value) for value in row):
                print("입력 형식 오류: NaN이나 무한대는 입력할 수 없습니다.")
                continue
            matrix.append(row)
            break
    return matrix


def mac(pattern, filter_matrix):
    """각 위치의 숫자를 곱해 모두 누적한다. 시간 복잡도 O(N²)."""
    total = 0.0
    for row_index in range(len(pattern)):
        for column_index in range(len(pattern[row_index])):
            total += pattern[row_index][column_index] * filter_matrix[row_index][column_index]
    if not math.isfinite(total):
        raise ValueError("MAC 연산 결과가 유한한 수가 아닙니다. 입력값의 크기를 줄이세요.")
    return total


def judge(score_a, score_b, label_a="A", label_b="B"):
    """점수 차이가 epsilon 미만이면 동점 처리한다."""
    if not math.isfinite(score_a) or not math.isfinite(score_b):
        raise ValueError("판정할 점수는 유한한 수여야 합니다.")
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return label_a if score_a > score_b else label_b


def measure_average(operation, repeats=REPEATS):
    """파일 I/O와 출력은 제외하고 연산만 반복 측정한다 (ms)."""
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다.")
    elapsed = 0
    for _ in range(repeats):
        start = time.perf_counter_ns()
        operation()
        elapsed += time.perf_counter_ns() - start
    return elapsed / repeats / 1_000_000


def generate_pattern(size, label):
    """N×N Cross/X 테스트 패턴을 자동 생성한다."""
    if isinstance(size, bool) or not isinstance(size, int) or size < 3 or size % 2 == 0:
        raise ValueError("패턴 생성 크기는 3 이상의 홀수여야 합니다.")
    label = normalize_label(label)
    if label is None:
        raise ValueError("패턴 라벨은 Cross 또는 X여야 합니다.")
    middle = size // 2
    result = [[0.0 for _ in range(size)] for _ in range(size)]
    for i in range(size):
        for j in range(size):
            if label == "Cross" and (i == middle or j == middle):
                result[i][j] = 1.0
            elif label == "X" and (i == j or i + j == size - 1):
                result[i][j] = 1.0
    return result


def print_matrix(name, matrix):
    """생성한 행렬을 수동 입력과 같은 공백 구분 형식으로 표시한다."""
    print(f"\n{name} ({len(matrix)}×{len(matrix)})")
    for row in matrix:
        print(" ".join(f"{value:g}" for value in row))


def run_generator_mode():
    while True:
        try:
            size = int(input("패턴 크기 N (3 이상의 홀수): ").strip())
            cross = generate_pattern(size, "Cross")
            x = generate_pattern(size, "X")
            break
        except ValueError:
            print("입력 형식 오류: 크기는 3 이상의 홀수 정수로 입력하세요.")
    print_matrix("Cross", cross)
    print_matrix("X", x)
    performance_report([size])


def performance_report(sizes):
    print(f"\n[성능 분석] MAC 1회 기준, 각 크기별 {REPEATS}회 평균")
    print(f"{'크기':<12}{'평균 시간(ms)':>16}{'연산 횟수(N²)':>18}")
    print("-" * 46)
    for size in sizes:
        pattern = generate_pattern(size, "Cross")
        filter_matrix = generate_pattern(size, "Cross")
        average = measure_average(lambda: mac(pattern, filter_matrix))
        print(f"{size}×{size:<9}{average:>16.6f}{size * size:>18}")
    print("※ 실행 환경에 따라 실제 측정 시간은 달라질 수 있습니다.")


def run_manual_mode():
    while True:
        source = input("입력 방식 (1: 직접 입력, 2: 3×3 자동 생성): ").strip()
        if source in ("1", "2"):
            break
        print("선택 오류: 1 또는 2를 입력하세요.")
    print("\n[1] 필터 입력")
    if source == "1":
        filter_a = read_matrix("필터 A")
        filter_b = read_matrix("필터 B")
    else:
        filter_a = generate_pattern(3, "Cross")
        filter_b = generate_pattern(3, "X")
        print_matrix("필터 A (Cross)", filter_a)
        print_matrix("필터 B (X)", filter_b)
    print("필터 A, B 저장 완료 (각 3×3)")

    print("\n[2] 패턴 입력")
    if source == "1":
        pattern = read_matrix("패턴")
    else:
        while True:
            label = normalize_label(input("생성할 패턴 (Cross/+ 또는 X): "))
            if label is not None:
                break
            print("입력 형식 오류: Cross/+ 또는 X를 입력하세요.")
        pattern = generate_pattern(3, label)
        print_matrix(f"패턴 ({label})", pattern)

    try:
        score_a = mac(pattern, filter_a)
        score_b = mac(pattern, filter_b)
        decision = judge(score_a, score_b)
    except ValueError as error:
        print(f"\n판정: 판정 불가 (UNDECIDED) | 연산 오류: {error}")
        return
    pair_time = measure_average(lambda: (mac(pattern, filter_a), mac(pattern, filter_b)))

    print("\n[3] MAC 결과")
    print(f"A 점수: {score_a:.16g}")
    print(f"B 점수: {score_b:.16g}")
    print(f"두 필터 연산 시간({REPEATS}회 평균): {pair_time:.6f} ms")
    print(f"판정: {'판정 불가 (UNDECIDED)' if decision == 'UNDECIDED' else decision}")
    if decision == "UNDECIDED":
        print(f"동점 근거: |A - B| < {EPSILON}")
    performance_report([3])


def get_filter_pair(filters, size):
    """filters['size_N']에서 cross/x를 찾아 각각 검증한다."""
    key = f"size_{size}"
    group = filters.get(key)
    if not isinstance(group, dict):
        raise ValueError(f"{key} 필터가 없거나 객체(dict)가 아닙니다.")

    normalized = {}
    for filter_name, values in group.items():
        label = normalize_label(filter_name)
        if label is None:
            continue
        if label in normalized:
            raise ValueError(f"{key}: {label} 필터 이름이 중복됩니다.")
        normalized[label] = validate_matrix(values, size, f"{key}.{filter_name}")
    if "Cross" not in normalized or "X" not in normalized:
        raise ValueError(f"{key}: cross, x 필터가 모두 필요합니다.")
    return normalized["Cross"], normalized["X"]


def analyze_case(case_key, case_data, filters):
    """하나의 JSON 테스트를 평가한다. 오류는 호출자가 FAIL로 기록한다."""
    match = PATTERN_KEY.fullmatch(case_key)
    if not match:
        raise ValueError("케이스 키는 size_N_idx 형태여야 합니다.")
    size = int(match.group(1))
    if size < 1:
        raise ValueError("필터 크기 N은 1 이상이어야 합니다.")
    if not isinstance(case_data, dict):
        raise ValueError("케이스 데이터가 객체(dict)가 아닙니다.")

    expected = normalize_label(case_data.get("expected"))
    if expected is None:
        raise ValueError("expected 라벨은 '+'/'cross' 또는 'x'여야 합니다.")
    pattern = validate_matrix(case_data.get("input"), size, f"{case_key}.input")
    cross_filter, x_filter = get_filter_pair(filters, size)
    cross_score = mac(pattern, cross_filter)
    x_score = mac(pattern, x_filter)
    decision = judge(cross_score, x_score, "Cross", "X")
    if decision == "UNDECIDED":
        reason = f"동점: 점수 차이 {abs(cross_score - x_score):.3g} < {EPSILON}"
    elif decision != expected:
        reason = f"판정({decision})과 기대값({expected}) 불일치"
    else:
        reason = ""
    return cross_score, x_score, decision, expected, reason


def run_json_mode():
    print(f"\n[1] JSON 로드: {DATA_PATH}")
    try:
        with DATA_PATH.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError:
        print("파일 오류: main.py와 같은 폴더에 data.json을 넣어주세요.")
        return
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"파일 오류: JSON을 읽을 수 없습니다. ({error})")
        return

    if not isinstance(document, dict):
        print("스키마 오류: JSON 최상위는 객체여야 합니다.")
        return
    filters = document.get("filters")
    patterns = document.get("patterns")
    if not isinstance(filters, dict):
        print("스키마 오류: 'filters'는 객체여야 합니다. 해당 케이스는 FAIL 처리합니다.")
        filters = {}
    if not isinstance(patterns, dict):
        print("스키마 오류: 'patterns'는 케이스 키를 가진 객체여야 합니다.")
        return

    for size in (5, 13, 25):
        try:
            get_filter_pair(filters, size)
            print(f"[OK] size_{size} 필터 로드 완료 (Cross, X)")
        except ValueError as error:
            print(f"! size_{size} 필터 확인 실패: {error}")

    print("\n[2] 패턴 분석 및 기대값 비교")
    passed = 0
    failures = []
    for case_key, case_data in patterns.items():
        print(f"\n--- {case_key} ---")
        try:
            if not isinstance(case_key, str):
                raise ValueError("케이스 키는 문자열이어야 합니다.")
            cross, x, decision, expected, reason = analyze_case(case_key, case_data, filters)
            print(f"Cross 점수: {cross:.16g}")
            print(f"X 점수:     {x:.16g}")
            result = "PASS" if not reason else "FAIL"
            print(f"판정: {decision} | expected: {expected} | {result}")
            if reason:
                print(f"사유: {reason}")
                failures.append((case_key, reason))
            else:
                passed += 1
        except (ValueError, TypeError, OverflowError) as error:
            reason = str(error)
            print("Cross 점수: 계산 불가")
            print("X 점수:     계산 불가")
            print(f"판정: UNDECIDED | FAIL (스키마/데이터/연산 오류: {reason})")
            failures.append((str(case_key), reason))

    performance_report([3, 5, 13, 25])
    print("\n[4] 결과 요약")
    print(f"총 테스트: {len(patterns)}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(failures)}개")
    if failures:
        print("\n실패 케이스:")
        for key, reason in failures:
            print(f"- {key}: {reason}")
    else:
        print("실패 케이스 없음 (라벨 정규화 및 epsilon 정책 적용)")


def main():
    print("=== Mini NPU Simulator ===")
    print("1. 사용자 입력 (3×3)")
    print("2. data.json 분석")
    print("3. 패턴 생성기 (N×N)")
    while True:
        choice = input("선택 (1/2/3): ").strip()
        if choice == "1":
            run_manual_mode()
            break
        if choice == "2":
            run_json_mode()
            break
        if choice == "3":
            run_generator_mode()
            break
        print("선택 오류: 1, 2 또는 3을 입력하세요.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 중단되어 프로그램을 종료합니다.")
