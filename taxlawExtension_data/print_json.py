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
    """
    HTML 콘텐츠를 마크다운 형식으로 변환하는 함수

    Args:
        html_content (str): 변환할 HTML 문자열
        doc_type (str, optional): 문서 유형 ('판례', '심판례', 기타). 기본값은 None.

    Returns:
        str: 변환된 마크다운 문자열
    """
    soup = BeautifulSoup(html_content, "html.parser")
    content_div = soup.find("div", id="cntnWrap_html")

    #! 문서 구조 분석
    doc_structure = analyze_document_structure(html_content)

    # 전체 또는 주요 내용이 테이블에 있는 경우 처리
    if doc_structure in ["table_only", "dominant_table"]:
        # 가장 큰 table 찾기
        tables = content_div.find_all("table", class_="sebeop_t")
        main_table = None
        max_content_length = 0

        for table in tables:
            content_length = len(table.get_text(strip=True))
            if content_length > max_content_length:
                max_content_length = content_length
                main_table = table

        if main_table:
            # table 내부의 모든 내용을 순서대로 추출
            new_html = "<div>"
            for element in main_table.descendants:
                if element.name == "td":  # td 태그를 만나면 내용 유지
                    new_html += str(element.decode_contents())
            new_html += "</div>"

            # 새로운 soup 생성
            new_content = BeautifulSoup(new_html, "html.parser")

        if doc_structure == "table_only":
            # 기존 content_div를 새로운 내용으로 교체
            content_div.clear()
            content_div.extend(new_content.div.contents)

        else:  # dominant_table인 경우
            # main_table을 새로운 내용으로 교체
            main_table.clear()
            main_table.extend(new_content.div.contents)

        soup = BeautifulSoup(str(content_div), "html.parser")

    # 테이블 제목 및 단위 탐지 패턴 정의
    table_title_pattern1 = re.compile(r"^[\(]*\s*표\s*\d*[\)]")
    table_title_pattern2 = re.compile(r"^[<]*\s*표\s*\d*[>]")
    unit_pattern = re.compile(r"\(단위\s*:.*?\)")

    if doc_type in ["판례", "심판"]:
        # 판례/심판례는 기존 방식대로 처리
        markdown = []

        for element in soup.find_all(["p", "table"]):
            if element.parent.name == "td":  # table cell 내부의 <p>는 제외
                continue

            if element.name == "table":
                # 테이블 제목과 단위 추출
                table_title = None
                table_unit = None
                current = element

                # 이전 <p> 태그에서 테이블 제목과 단위 탐지
                while current.previous_sibling:
                    current = current.previous_sibling
                    # 다른 테이블을 만나면 검색 중단
                    if current.name == "table":
                        break
                    # <p> 고 텍스트가 있는 경우만 검사
                    if current.name == "p":
                        text = current.get_text().strip()
                        if "단위" in text:
                            table_unit = text
                        elif table_title_pattern1.search(
                            text
                        ) or table_title_pattern2.search(text):
                            table_title = text
                            break

                # 제목과 단위를 결합
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
                ):  # 테이블 제목 제외
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
    if not rows:  # 테이블이 비어있는 경우
        return ""

    table_data = []  # 데이터 저장
    rowspan_tracker = {}  # rowspan을 추적

    for row_idx, row in enumerate(rows):
        cols = row.find_all(["td", "th"])
        if not cols:  # 빈 행은 건너뛰기
            continue

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

        if row_data:  # 데이터가 있는 행만 추가
            table_data.append(row_data)

    # 테이블 데이터가 비어있는 경우
    if not table_data:
        return ""

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


#! 문서 유형 분류
def is_all_content_in_table(content_div):
    """
    Checks if all meaningful content is contained within a single main table.

    Args:
        content_div (BeautifulSoup object): 문서 컨텐츠를 담고 있는 div element.

    Returns:
        bool: 모든 내용이 하나의 table 안에 있으면 True, 아니면 False
    """
    # Locate the first main table with the "sebeop_t" class
    main_table = None
    for element in content_div.find_all(
        "table", recursive=True
    ):  # 모든 하위 table 검색
        if element.get("class") and "sebeop_t" in element.get("class"):
            main_table = element
            break

    if not main_table:
        return False

    # table 외부에 의미있는 내용이 있는지 확인
    meaningful_content_outside = False
    for element in content_div.find_all("p", recursive=True):  # 모든 하위 p 태그 검색
        # table 내부의 p 태그는 제외
        if not element.find_parent("table", class_="sebeop_t"):
            text = element.get_text(strip=True)
            # 의미있는 텍스트가 있다면
            if text and text != "\xa0":  # \xa0는 &nbsp;
                meaningful_content_outside = True
                break

    # table 외부에 의미있는 내용이 없으면 True
    return not meaningful_content_outside


def analyze_document_structure(html_content):
    """
    문서의 구조를 분석하여 문서 유형을 판단

    Args:
        html_content (str): HTML content as a string.

    Returns:
        str: 문서 유형
            - "table_only": 모든 내용이 하나의 table에 있는 경우
            - "dominant_table": 하나의 큰 표가 문서의 주요 부분을 차지하는 특수한 경우
            - "normal": 일반적인 형태의 경우
    """
    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")
    content_div = soup.find("div", id="cntnWrap_html")

    if not content_div:
        return "normal"

    # 모든 내용이 하나의 table 안에 있는지 확인
    if is_all_content_in_table(content_div):
        return "table_only"

    # table_only가 아닌 경우, table 내용 비율로 판단
    tables = content_div.find_all("table", class_="sebeop_t")
    if tables:
        max_content_length = max(len(table.get_text(strip=True)) for table in tables)
        total_content_length = len(content_div.get_text(strip=True))
        table_ratio = max_content_length / total_content_length

        if table_ratio > 0.5:  # table이 전체 내용의 50% 이상
            return "dominant_table"

    return "normal"


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
