import re
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd


def parse_structure(content):
    """
    Parse the structured content using predefined markers (e.g., '1.', '가.', '1)', etc.)
    to create hierarchical Markdown.
    """
    # 최상위 레벨 항목들
    top_level_items = ["주 문", "청 구 취 지", "이 유"]

    # 날짜 형식을 제외하고 실제 헤더만 매칭하도록 정규표현식 수정
    levels = [
        r"^\d{1,2}\.(?!\d)",  # 1. , 2. 등은 매칭하되 1999., 2014. 등은 제외
        r"^\w\.",
        r"^\d+\)",
        r"^\w\)",
        r"^\(\d+\)",
    ]
    regexes = [re.compile(level) for level in levels]

    hierarchy = []
    markdown_lines = []
    current_paragraph = []
    current_header = None

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        stripped_line = lines[i].strip()
        if not stripped_line:
            if current_paragraph:
                if current_header:
                    markdown_lines.append(current_header)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []
                current_header = None
            i += 1
            continue

        # 최상위 레벨 항목 체크
        if stripped_line in top_level_items:
            if current_paragraph:
                if current_header:
                    markdown_lines.append(current_header)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []
                current_header = None
            markdown_lines.append("# " + stripped_line)
            i += 1
            continue

        match_level = None
        matched_part = None

        for idx, regex in enumerate(regexes):
            match = regex.match(stripped_line)
            if match:
                match_level = idx
                matched_part = match.group()
                break

        if match_level is not None:
            # 이전 문단 처리
            if current_paragraph:
                if current_header:
                    markdown_lines.append(current_header)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []

            while len(hierarchy) > match_level:
                hierarchy.pop()

            if len(hierarchy) <= match_level:
                hierarchy.append(matched_part)

            # 헤더 추가
            markdown_lines.append("#" * (match_level + 2) + " " + matched_part)

            # 남은 텍스트 처리
            remaining_text = stripped_line[len(matched_part) :].strip()
            if remaining_text:
                if remaining_text.endswith("."):
                    # 마침표로 끝나면 바로 출력
                    markdown_lines.append("    " + remaining_text)
                else:
                    # 마침표로 끝나지 않으면 current_paragraph에 추가
                    current_paragraph.append(remaining_text)
        else:
            # 일반 텍스트 처리
            if stripped_line.endswith("."):
                # 마침표로 끝나면 현재 문단 완성
                current_paragraph.append(stripped_line)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []
            else:
                current_paragraph.append(stripped_line)

        i += 1

    # 마지막 문단 처리
    if current_paragraph:
        markdown_lines.append("    " + " ".join(current_paragraph))

    return "\n\n".join(markdown_lines)


def html_to_markdown(html_content, doc_type=None):
    """HTML을 마크다운으로 변환

    Args:
        html_content (str): 변환할 HTML 문자열
        doc_type (str): 문서 유형 ('판례', '심판례' 또는 기타)
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 표 제목 패턴을 위한 정규표현식 추가
    table_title_pattern1 = re.compile(r"^[\(]*\s*표\s*\d*[\)]")
    table_title_pattern2 = re.compile(r"^[<]*\s*표\s*\d*[>]")
    unit_pattern = re.compile(r"\(단위\s*:.*?\)")

    if doc_type in ["판례", "심판"]:
        # 판례/심판례는 기존 방식대로 처리
        markdown = []

        for element in soup.find_all(["p", "table"]):
            if element.parent.name == "td":  # 테이블 셀 안의 p 태그는 건너뛰기
                continue

            if element.name == "table":
                # 테이블 관련 텍스트 수집
                table_title = None
                table_unit = None
                current = element

                # 이전 p 태그들 검사
                while current.previous_sibling:
                    current = current.previous_sibling
                    # 다른 테이블을 만나면 검색 중단
                    if current.name == "table":
                        break
                    # p 태그이고 텍스트가 있는 경우만 검사
                    if current.name == "p":
                        text = current.get_text().strip()
                        if "단위" in text:
                            table_unit = text
                        elif table_title_pattern1.search(
                            text
                        ) or table_title_pattern2.search(text):
                            table_title = text
                            break

                # 테이블 제목과 단위를 결합
                combined_title = ""
                if table_title:
                    combined_title = table_title
                if table_unit:
                    combined_title += f" {table_unit}" if combined_title else table_unit

                # 테이블을 마크다운으로 변환
                table_md = convert_table_to_markdown(element, combined_title)
                markdown.append(table_md)

            elif element.name == "p":
                text = element.get_text(strip=True)
                if (
                    text
                    and not (
                        table_title_pattern1.search(text)
                        or table_title_pattern2.search(text)
                    )
                    and not unit_pattern.search(text)
                ):  # 테이블 제목은 제외
                    markdown.append(text)

        # return parse_structure("\n".join(markdown))
        return "\n\n".join(markdown)
    else:
        # 해석례는 새로운 방식으로 처리
        markdown = []
        for element in soup.find_all(["p", "table"]):
            if element.name == "table":
                # 테이블 제목 찾기 (이전 p 태그에서 찾기)
                table_title = ""
                prev_element = element.find_previous_sibling("p")
                if prev_element:
                    title_text = prev_element.get_text().strip()
                    if table_title_pattern1.search(
                        title_text
                    ) or table_title_pattern2.search(title_text):
                        table_title = title_text

                # 테이블을 마크다운으로 변환
                table_md = convert_table_to_markdown(element, table_title)
                markdown.extend(table_md)
            elif element.name == "p":
                text = element.get_text(strip=True)
                if text and not (
                    table_title_pattern1.search(text)
                    or table_title_pattern2.search(text)
                ):  # 테이블 제목은 제외
                    markdown.append(text)

        return parse_interpretation_structure("\n".join(markdown))


def convert_table_to_markdown(table, title=""):
    """
    HTML 표를 마크다운 표로 변환

    Args:
        table (bs4.element.Tag): 변환할 HTML 표 요소
        title (str): 표의 제목
    """
    markdown = []

    # 테이블 제목이 있으면 추가
    if title:
        markdown.append(f"\n**{title}**\n")

    # 테이블 데이터 추출
    rows = table.find_all("tr")
    table_data = []  # 데이터 저장
    rowspan_tracker = {}  # rowspan을 추적

    for row_idx, row in enumerate(rows):
        cols = row.find_all(["td", "th"])
        row_data = []
        col_idx = 0  # 현재 열 인덱스

        for col in cols:
            while col_idx in rowspan_tracker and rowspan_tracker[col_idx] > 0:
                # 이전 rowspan으로 인한 빈 셀 채우기
                row_data.append("")
                rowspan_tracker[col_idx] -= 1
                col_idx += 1

            # 셀 데이터 추출
            cell_text = col.get_text(strip=True)
            colspan = int(col.get("colspan", 1))
            rowspan = int(col.get("rowspan", 1))

            # 셀 데이터 추가
            row_data.extend([cell_text] * colspan)

            # rowspan 추적 업데이트
            if rowspan > 1:
                for span_idx in range(colspan):
                    rowspan_tracker[col_idx + span_idx] = rowspan - 1

            col_idx += colspan

        # 남은 rowspan으로 인한 빈 열 처리
        while col_idx in rowspan_tracker and rowspan_tracker[col_idx] > 0:
            row_data.append("")
            rowspan_tracker[col_idx] -= 1
            col_idx += 1

        table_data.append(row_data)

    # 데이터프레임 생성 및 마크다운 변환
    max_cols = max(len(row) for row in table_data)
    for row in table_data:
        while len(row) < max_cols:
            row.append("")  # 빈 셀 채우기

    df = pd.DataFrame(table_data)

    # 첫 번째 행을 컬럼 제목으로 설정
    df.columns = df.iloc[0]  # 첫 번째 행을 컬럼으로
    df = df[1:]  # 첫 번째 행 제거 (데이터로 사용되었으므로)

    markdown = df.to_markdown(index=False, tablefmt="pipe")
    return markdown


def parse_interpretation_structure(content):
    """
    해석례용 구조 파싱 함수
    해석례는 '주문'과 '이유'를 최상위 레벨로 하고
    그 아래 '1.', 'ㄱ.', '(1)' 등의 형식을 사용
    """
    # 최상위 레벨 항목들
    top_level_items = ["주문", "이유"]

    # 해석례 구조의 레벨 정의
    levels = [
        r"^\d+\.",  # 1., 2. 등
        r"^[가-힣]\.",  # 가., 나. 등
        r"^\(\d+\)",  # (1), (2) 등
        r"^[a-z]\)",  # a), b) 등
        r"^[가-힣]\)",  # 가), 나) 등
        r"^\d+\)",  # 1), 2) 등
    ]
    regexes = [re.compile(level) for level in levels]

    hierarchy = []
    markdown_lines = []
    current_paragraph = []
    current_header = None

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        stripped_line = lines[i].strip()
        if not stripped_line:
            if current_paragraph:
                if current_header:
                    markdown_lines.append(current_header)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []
                current_header = None
            i += 1
            continue

        # 최상위 레벨 항목 체크
        if stripped_line in top_level_items:
            if current_paragraph:
                if current_header:
                    markdown_lines.append(current_header)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []
                current_header = None
            markdown_lines.append("# " + stripped_line)
            i += 1
            continue

        match_level = None
        matched_part = None

        for idx, regex in enumerate(regexes):
            match = regex.match(stripped_line)
            if match:
                match_level = idx
                matched_part = match.group()
                break

        if match_level is not None:
            # 이전 문단 처리
            if current_paragraph:
                if current_header:
                    markdown_lines.append(current_header)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []

            while len(hierarchy) > match_level:
                hierarchy.pop()

            if len(hierarchy) <= match_level:
                hierarchy.append(matched_part)

            # 헤더 레벨 조정 (각 레벨마다 '#' 하나씩만 추가)
            header_level = match_level + 2  # 최상위가 #이므로 그 다음은 ##부터 시작
            markdown_lines.append("#" * header_level + " " + matched_part)

            # 남은 텍스트 처리
            remaining_text = stripped_line[len(matched_part) :].strip()
            if remaining_text:
                if remaining_text.endswith("."):
                    markdown_lines.append("    " + remaining_text)
                else:
                    current_paragraph.append(remaining_text)
        else:
            # 일반 텍스트 처리
            if stripped_line.endswith("."):
                current_paragraph.append(stripped_line)
                markdown_lines.append("    " + " ".join(current_paragraph))
                current_paragraph = []
            else:
                current_paragraph.append(stripped_line)

        i += 1

    # 마지막 문단 처리
    if current_paragraph:
        markdown_lines.append("    " + " ".join(current_paragraph))

    return "\n\n".join(markdown_lines)


def main():
    input_path = Path("..\\data\\조심-2023-중-7590.html")
    output_path = input_path.with_suffix(".md")

    with open(input_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    markdown_content = html_to_markdown(html_content)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(markdown_content)

    print(f"Markdown file has been saved to {output_path}")


if __name__ == "__main__":
    main()
