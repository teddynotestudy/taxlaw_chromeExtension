from playwright.sync_api import sync_playwright
from playwright.sync_api import expect
import json
from urllib.parse import urlencode
import time
import os
import pandas as pd
from print_json import html_to_markdown  # print_json.py의 변환 함수 import



def split_text(text):
    parts = text.split(',')
    if len(parts) == 2:
        return parts[0].replace("(","").strip(), parts[1].replace(")","").strip()
    
    return text, ''
def scrape_precedent_doc(new_page, download_dir):
    """판례 문서 크롤링"""
    # 프린트 버튼 클릭
    #new_page.wait_for_selector('//*[@id="bizCommonBtnStorPrintBtn"]', state='visible')
    #new_page.click('//*[@id="bizCommonBtnStorPrintBtn"]')

    # 데이터 수집
    
    metadata = collect_precedent_metadata(new_page)

    #컨텐츠에는 상세내용 하위의 내용만 html로 저장 후 md파일로 변환
    content = collect_precedent_content(new_page, download_dir)
    
    # 판례용 마크다운 생성
    markdown_content = generate_markdown(metadata, content, "판례")
    
    # 마크다운 파일 저장
    save_markdown(markdown_content, metadata['doc_num'], download_dir)
    
    # PDF 다운로드
    #pdf_path = download_pdf(new_page, download_dir)
    
    result = {
        **metadata,
        **content,
        "markdown_path": f"{download_dir}/{metadata['doc_num']}.md",
        
    }
    
    return result

def scrape_interpretation_doc(new_page, download_dir):
    """해석례 문서 크롤링"""
    try:
        print("메타데이터 수집 시작...")
        metadata = collect_interpretation_metadata(new_page)
        print("메타데이터 수집 완료")
        
        print("컨텐츠 수집 시작...")
        content = collect_interpretation_content(new_page, download_dir)
        print("컨텐츠 수집 완료")
        
        print("마크다운 생성 시작...")
        markdown_content = generate_markdown(metadata, content, "해석례")
        print("마크다운 생성 완료")
        
        print("마크다운 파일 저장 시작...")
        save_markdown(markdown_content, metadata['doc_num'], download_dir)
        print("마크다운 파일 저장 완료")
        
        result = {
            **metadata,
            **content,
            "markdown_path": f"{download_dir}/{metadata['doc_num']}.md",
        }
        
        return result
        
    except Exception as e:
        print("\n=== 해석례 크롤링 상세 오류 ===")
        print(f"오류 발생 위치: {e.__traceback__.tb_frame.f_code.co_name}")
        print(f"오류 발생 라인: {e.__traceback__.tb_lineno}")
        print(f"오류 메시지: {str(e)}")
        
        # 오류 발생 시점의 콜스택 출력
        import traceback
        print("\n=== 오류 발생 콜스택 ===")
        traceback.print_exc()
        
        raise e

def collect_precedent_metadata(new_page):
    """판례 메타데이터 수집"""
    metadata = {
        "url": new_page.url,
        "doc_num": "",
        "produce_date": "",
        "related_date": "",
        "court_sim": "",
        "progress": "",
        "tax_type": "",
        "doc_title": "",
        "doc_type": "",
        "doc_result": "",
        "summary": { #요지
            "content": ""
        },
        "related_keywords": [],
        "related_laws": [],
        "similar_docs": [],
        "tag_cloud": []  # 태그 클라우드 항목 추가
    }
    
    # 각 메타데이터 항목 개별 수집
    try:
        metadata["doc_num"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[1]/strong').inner_text()
    except Exception as e:
        print(f"문서번호 수집 실패: {str(e)}")

    try:
        metadata["produce_date"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[4]/span').inner_text()
    except Exception as e:
        print(f"생산일자 수집 실패: {str(e)}")

    try:
        metadata["related_date"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[2]/span').inner_text()
    except Exception as e:
        print(f"관련일자 수집 실패: {str(e)}")

    try:
        metadata["court_sim"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[3]/span').inner_text()
    except Exception as e:
        print(f"법원심급 수집 실패: {str(e)}")

    try:
        metadata["progress"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[5]/span').inner_text()
    except Exception as e:
        print(f"진행상태 수집 실패: {str(e)}")

    try:
        metadata["tax_type"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/div/ul/li').get_attribute('title')
    except Exception as e:
        print(f"세목 수집 실패: {str(e)}")

    try:
        metadata["doc_title"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/div/strong').inner_text()
    except Exception as e:
        print(f"문서제목 수집 실패: {str(e)}")

    try:
        metadata["doc_type"] = new_page.locator('//*[@id="scrnNm"]').inner_text()
    except Exception as e:
        print(f"문서유형 수집 실패: {str(e)}")

    try:
        metadata["doc_result"] = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/div/em').inner_text()
    except Exception as e:
        print(f"판결결과 수집 실패: {str(e)}")

    # 관련 주제어와 관련 법령 수집
    
    try:
        base_xpath = '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[2]'
        rel_groups = new_page.locator(f'{base_xpath}/div[contains(@class, "rel_group")]').all()
        print(f"발견된 rel_group 개수: {len(rel_groups)}")
        
        if len(rel_groups) > 0:
            for group in rel_groups:
                try:
                    group_type = group.locator('span').inner_text().strip()
                    print(f"처리 중인 그룹 타입: {group_type}")
                    
                    links = group.locator('div > a').all()
                    content_list = [link.inner_text().strip() for link in links if link.inner_text().strip()]
                    
                    if '관련 주제어' in group_type:
                        print(f"관련 주제어 목록: {content_list}")
                        metadata["related_keywords"] = content_list
                    elif '관련 법령' in group_type:
                        print(f"관련 법령 목록: {content_list}")
                        metadata["related_laws"] = content_list
                        
                except Exception as e:
                    print(f"그룹 처리 중 오류 발생: {str(e)}")
                    continue
        else:
            # 대체 경로 시도
            try:
                alt_base_xpath = '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[2]'
                alt_rel_groups = new_page.locator(f'{alt_base_xpath}/div[contains(@class, "rel_group")]').all()
                print(f"대체 경로에서 발견된 rel_group 개수: {len(alt_rel_groups)}")
                
                for group in alt_rel_groups:
                    try:
                        group_type = group.locator('span').inner_text().strip()
                        print(f"처리 중인 그룹 타입: {group_type}")
                        
                        links = group.locator('div > a').all()
                        content_list = [link.inner_text().strip() for link in links if link.inner_text().strip()]
                        
                        if '관련 주제어' in group_type:
                            print(f"관련 주제어 목록: {content_list}")
                            metadata["related_keywords"] = content_list
                        elif '관련 법령' in group_type:
                            print(f"관련 법령 목록: {content_list}")
                            metadata["related_laws"] = content_list
                            
                    except Exception as e:
                        print(f"대체 그룹 처리 중 오류 발생: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"대체 경로 처리 중 오류 발생: {str(e)}")
                
    except Exception as e:
        print(f"관련 주제어/법령 수집 중 오류: {str(e)}")
    
    ###############################################################

    # 유사문서 수집
    try:
        similar_docs = []
        ul_element = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[3]/div[1]/div/ul')
        li_elements = ul_element.locator('li').all()
        
        for li in li_elements:
            try:
                similar_docs.append({
                    "title": li.locator('xpath=.//a/div[1]/p[1]').inner_text(),
                    "doc_num": split_text(li.locator('xpath=.//a/div[1]/p[2]').inner_text())[0],
                    "date": split_text(li.locator('xpath=.//a/div[1]/p[2]').inner_text())[1]
                })
            except Exception as e:
                print(f"유사문서 추출 중 오류: {str(e)}")
        
        metadata["similar_docs"] = similar_docs
        
    except Exception as e:
        print(f"유사문서 수집 중 오류: {str(e)}")
    
    ###############################################################


    # summary수집 추가
    summary_content_paths = [
        '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[3]/div/div[2]/div[1]/p',
        '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[3]/div/div[2]/div[1]/p',
        '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[2]/div/div[2]/div[1]/p'
    ]
    

    # 여러 경로 시도하여 데이터 수집
    def try_multiple_paths(paths):
        for path in paths:
            try:
                element = new_page.locator(path)
                if element.is_visible():
                    return element.inner_text()
            except Exception as e:
                continue
        return ""

    # summary와 result_content 데이터 수집
    metadata["summary"]["content"] = try_multiple_paths(summary_content_paths)
    
    # 태그 클라우드 수집 추가
    try:
        # 태그 클라우드 가능한 경로들
        tag_cloud_paths = [
            '//*[@id="dcmDetailBox"]/div/div/div[2]/div[2]/div[2]/span',
            '//*[@id="dcmDetailBox"]/div/div/div[3]/div[2]/div[2]/span',
            
        ]
        
        
        tag_cloud_elements = []
        for path in tag_cloud_paths:
            try:
                elements = new_page.locator(path).all()
                if elements:
                    tag_cloud_elements = elements
                    print(f"태그 클라우드 발견된 경로: {path}")
                    break
            except Exception as e:
                print(f"태그 클라우드 찾기 실패경로: {path}")
                print(f"오류 메시지: {str(e)}")
                continue
        
        if tag_cloud_elements:
            metadata["tag_cloud"] = [tag.inner_text().replace('#', '').strip() 
                                   for tag in tag_cloud_elements 
                                   if tag.inner_text().strip()]
            print(f"수집된 태그 클라우드: {metadata['tag_cloud']}")
        else:
            print("태그 클라우드를 찾을 수 없습니다.")
            metadata["tag_cloud"] = []
            
    except Exception as e:
        print(f"태그 클라우드 수집 중 오류: {str(e)}")
        metadata["tag_cloud"] = []

    return metadata

def save_html_content(element, doc_number, download_dir):
    """HTML 내용 저장"""
    try:
        html_content = element.evaluate('el => el.outerHTML')
        html_path = os.path.join(download_dir, f"{doc_number}.html")
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{}</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; }}
    </style>
</head>
<body>
{}
</body>
</html>""".format(doc_number, html_content))
        
        return html_path
        
    except Exception as e:
        print(f"HTML 저장 중 오류 발생: {str(e)}")
        return None

def collect_precedent_content(new_page, download_dir):
    """판례 본문 내용 수집"""
    # HTML 내용 저장
    content_element = new_page.locator('//*[@id="cntnWrap_html"]')
    doc_number = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[1]/strong').inner_text()
    html_path = save_html_content(content_element, doc_number, download_dir)

    # HTML을 마크다운으로 변환
    if html_path:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        content_markdown = html_to_markdown(html_content, doc_type='판례')
    else:
        content_markdown = ""

    return {
        "details": {
            "title": "상세내용",
            "content": content_markdown
        },
        "html_path": html_path
    }

def collect_interpretation_metadata(new_page):
    """해석례 메타데이터 수집"""
    try:
        metadata = {
            "url": new_page.url,
            "doc_num": "",
            "produce_date": "",
            "related_date": "",
            "tax_type": "",
            "doc_title": "",
            "doc_type": "",
            "doc_result": "",
            "summary": {"content": ""},
            "related_keywords": [],
            "related_laws": [],
            "similar_docs": [],
            "tag_cloud": []
        }
        
        print("\n=== 메타데이터 수집 시작 ===")

        # 여러 경로 시도하여 데이터 수집
        def try_multiple_paths(paths, get_attribute=None):
            for path in paths:
                try:
                    element = new_page.locator(path)
                    if element.is_visible():
                        if get_attribute:
                            return element.get_attribute(get_attribute)
                        return element.inner_text()
                except Exception as e:
                    print(f"경로 시도 실패: {path}")
                    print(f"오류 메시지: {str(e)}")
                    continue
            return ""

        # 관련 주제어와 법령 수집을 위한 함수
        def collect_related_items(base_paths):
            for base_path in base_paths:
                try:
                    rel_groups = new_page.locator(f'{base_path}/div[contains(@class, "rel_group")]').all()
                    print(f"발견된 rel_group 개수 ({base_path}): {len(rel_groups)}")
                    
                    if len(rel_groups) > 0:
                        for group in rel_groups:
                            try:
                                group_type = group.locator('span').inner_text().strip()
                                print(f"처리 중인 그룹 타입: {group_type}")
                                
                                links = group.locator('div > a').all()
                                content_list = [link.inner_text().strip() for link in links if link.inner_text().strip()]
                                
                                if '관련 주제어' in group_type:
                                    print(f"관련 주제어 목록: {content_list}")
                                    metadata["related_keywords"] = content_list
                                    return True
                                elif '관련 법령' in group_type:
                                    print(f"관련 법령 목록: {content_list}")
                                    metadata["related_laws"] = content_list
                                    return True
                            except Exception as e:
                                print(f"그룹 처리 중 오류 발생: {str(e)}")
                                continue
                except Exception as e:
                    print(f"base_path 처리 중 오류: {str(e)}")
                    continue
            return False

        # 각 필드별 xpath 목록 정의
        paths = {
            "doc_num": [
                '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[1]/ul/li[1]/strong',
                '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[1]/strong'
            ],
            "produce_date": [
                '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[1]/ul/li[3]/span',
                '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[3]/span'
            ],
            "related_date": [
                '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[1]/ul/li[2]/span',
                '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/ul/li[2]/span'
            ],
            "tax_type": [
                '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[1]/div/ul/li',
                '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/div/ul/li'
            ],
            "doc_title": [
                '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[1]/div/strong',
                '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/div/strong'
            ],
            "doc_result": [
                '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[1]/div/em',
                '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[1]/div/em'
            ]
        }

        # 기본 메타데이터 수집
        for field, field_paths in paths.items():
            try:
                if field == "tax_type":
                    value = try_multiple_paths(field_paths, get_attribute='title')
                else:
                    value = try_multiple_paths(field_paths)
                
                if value:
                    metadata[field] = value
                    print(f"{field} 수집 성공: {value}")
                else:
                    print(f"{field} 수집 실패")
            except Exception as e:
                print(f"{field} 수집 중 오류: {str(e)}")

        # 문서 유형은 단일 경로
        try:
            metadata["doc_type"] = new_page.locator('//*[@id="scrnNm"]').inner_text()
            print("문서유형 수집 성공")
        except Exception as e:
            print(f"문서유형 수집 실패: {str(e)}")

        # 관련 주제어와 법령 수집 (여러 base_path 시도)
        related_base_paths = [
            '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[2]',
            '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[2]'
        ]
        collect_related_items(related_base_paths)

        # 요지(summary) 수집
        summary_paths = [
            '//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[3]/div/div[2]/div[1]/p',
            '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[3]/div/div[2]/div[1]/p',
            '//*[@id="dcmDetailBox"]/div/div/div[2]/div/div/div[2]/div/div[2]/div[1]/p'
        ]
        metadata["summary"]["content"] = try_multiple_paths(summary_paths)

        print("=== 메타데이터 수집 완료 ===\n")
        return metadata
        
    except Exception as e:
        print("\n=== 메타데이터 수집 상세 오류 ===")
        print(f"오류 발생 위치: {e.__traceback__.tb_frame.f_code.co_name}")
        print(f"오류 발생 라인: {e.__traceback__.tb_lineno}")
        print(f"오류 메시지: {str(e)}")
        raise e

def collect_interpretation_content(new_page, download_dir):
    """해석례 본문 내용 수집"""
    try:
        print("\n=== 컨텐츠 수집 시작 ===")
        
        # HTML 내용 저장
        print("HTML 내용 저장 시작...")
        content_element = new_page.locator('//*[@id="cntnWrap_html"]')
        doc_number = new_page.locator('//*[@id="dcmDetailBox"]/div/div/div[1]/div/div/div[1]/ul/li[1]/strong').inner_text()
        html_path = save_html_content(content_element, doc_number, download_dir)
        print("HTML 내용 저장 완료")
        
        # HTML을 마크다운으로 변환
        if html_path:
            print("마크다운 변환 시작...")
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            content_markdown = html_to_markdown(html_content, doc_type='해석례')
            print("마크다운 변환 완료")
        else:
            raise Exception("HTML 저장 실패")
            
        print("=== 컨텐츠 수집 완료 ===\n")
        
        return {
            "details": {
                "title": "상세내용",
                "content": content_markdown
            },
            "html_path": html_path
        }
        
    except Exception as e:
        print("\n=== 컨텐츠 수집 상세 오류 ===")
        print(f"오류 발생 위치: {e.__traceback__.tb_frame.f_code.co_name}")
        print(f"오류 발생 라인: {e.__traceback__.tb_lineno}")
        print(f"오류 메시지: {str(e)}")
        raise e

def generate_markdown(metadata, content, doc_type):
    """문서 유형에 따른 마크다운 형식 생성"""
    if doc_type in ['판례', '심판']:
        return generate_precedent_markdown(metadata, content)
    else:
        return generate_interpretation_markdown(metadata, content)

def generate_precedent_markdown(metadata, content):
    """판례/심판용 마크다운 형식"""
    md = f"""

# Metadata

## 기본정보
- 문서번호: {metadata['doc_num']}
- 세목: {metadata['tax_type']}
- 문서명: {metadata['doc_title']}
- 문서유형: {metadata['doc_type']}
- 생산일자: {metadata['produce_date']}
- 귀속연도: {metadata['related_date']}
- 법원유형: {metadata['court_sim']}
- 진행상황: {metadata['progress']}
- 판결결과: {metadata['doc_result']}
- URL: {metadata['url']}

## 관련 주제어
{chr(10).join([f'- {keyword}' for keyword in metadata['related_keywords']]) if metadata['related_keywords'] else '(없음)'}

## 관련 법령
{chr(10).join([f'- {law}' for law in metadata['related_laws']]) if metadata['related_laws'] else '(없음)'}

## 유사문서
{chr(10).join([f'- [{doc["title"]}] {doc["doc_num"]} ({doc["date"]})' for doc in metadata['similar_docs']]) if metadata['similar_docs'] else '(없음)'}

## 태그 클라우드
{chr(10).join([f'- {tag}' for tag in metadata['tag_cloud']]) if metadata['tag_cloud'] else '(없음)'}

## 요지
{metadata['summary']['content'] if metadata['summary']['content'] else '(없음)'}


# content
{content['details']['content']}
"""
    return md

def generate_interpretation_markdown(metadata, content):
    """해석례용 마크다운 형식"""
    md = f"""

# Metadata

## 기본정보
- 문서번호: {metadata['doc_num']}
- 세목: {metadata['tax_type']}
- 문서명: {metadata['doc_title']}
- 문서유형: {metadata['doc_type']}
- 생산일자: {metadata['produce_date']}
- 귀속연도: {metadata['related_date']}
- 판결결과: {metadata['doc_result']}
- URL: {metadata['url']}

## 관련 주제어
{chr(10).join([f'- {keyword}' for keyword in metadata['related_keywords']]) if metadata['related_keywords'] else '(없음)'}

## 관련 법령
{chr(10).join([f'- {law}' for law in metadata['related_laws']]) if metadata['related_laws'] else '(없음)'}

## 유사문서
{chr(10).join([f'- [{doc["title"]}] {doc["doc_num"]} ({doc["date"]})' for doc in metadata['similar_docs']]) if metadata['similar_docs'] else '(없음)'}

## 태그 클라우드
{chr(10).join([f'- {tag}' for tag in metadata['tag_cloud']]) if metadata['tag_cloud'] else '(없음)'}

## 요지
{metadata['summary']['content'] if metadata['summary']['content'] else '(없음)'}

# Content
{content['details']['content']}
"""
    return md

def save_markdown(content, filename, directory):
    """마크다운 파일 저장"""
    filepath = os.path.join(directory, f"{filename}.md")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath

def download_pdf(new_page, download_dir):
    """PDF 다운로드"""
    new_page.wait_for_selector('//*[@id="STOR_PRINT_WRAPPER"]', state='visible')
    download_button = new_page.locator('//*[@id="STOR_PRINT_WRAPPER"]/div[2]/button[2]')

    with new_page.expect_download(timeout=30000) as download_info:
        download_button.click()
        download = download_info.value
        download_path = os.path.join(download_dir, download.suggested_filename)
        download.save_as(download_path)
        return download_path

def get_doc_numbers(li_elements):
    """현재 페이지의 모든 문서 번호를 추출"""
    doc_numbers = []
    for li in li_elements:
        try:
            # 수정된 CSS 선택자로 문서 번호 요소 찾기
            doc_number_element = li.query_selector('div.board_box > div.substance_wrap > ul > li:first-child')
            
            if doc_number_element:
                doc_number = doc_number_element.inner_text().strip()
                print(f"추출된 문서 번호: {doc_number}")
                doc_numbers.append(doc_number)
            else:
                print("문서 번호 요소를 찾을 수 없습니다.")
                print(f"현재 li의 HTML 구조: {li.inner_html()}")
        except Exception as e:
            print(f"문서 번호 추출 중 오류: {str(e)}")
    return doc_numbers

def search_keyword(page, keyword):
    """키워드 검색 수행"""
    try:
        # 검색창이 나타날 때까지 대기
        page.wait_for_selector('//*[@id="subTopTotalSchInput"]', state="visible")
        
        # 검색창에 키워드 입력
        search_input = page.locator('//*[@id="subTopTotalSchInput"]')
        search_input.fill(keyword)
        
        # 검색 버튼 클릭 (Enter 키 입력으로 대체 가능)
        search_input.press('Enter')
        
        # 검색 결과 로딩 대기
        page.wait_for_load_state('networkidle')
        
        time.sleep(2)  # 추가 대기 시간
        
        # 해석례/판례 버튼 클릭
        interpretation_button = page.locator('//*[@id="pointerDiv"]/a[3]')
        interpretation_button.click()
        
        
        # 결과 로딩 대기
        page.wait_for_selector('//*[@id="collectionDiv"]/div[4]/ul', state="visible")
        time.sleep(2)  # 추가 대기 시간
        
        print(f"'{keyword}' 검색 완료")
        return True
        
    except Exception as e:
        print(f"검색 중 오류 발생: {str(e)}")
        return False

def save_failed_docs_to_excel(failed_docs, filename="failed_documents.xlsx"):
    """수집 실패한 문서 정보를 엑셀 파일로 저장"""
    df = pd.DataFrame(failed_docs, columns=['doc_number', 'error_message', 'timestamp'])
    df.to_excel(filename, index=False)
    print(f"수집 실패 문서 목록이 {filename}에 저장되었습니다.")

def crawl_with_playwright():
    json_filename = "scraped_documents.json"
    failed_docs_filename = "failed_documents.json"
    
    # 성공한 문서 목록 로드
    scraped_docs = load_from_json(json_filename)
    
    # 실패한 문서 목록 로드
    failed_docs = {}
    if os.path.exists(failed_docs_filename):
        print(f"실패 문서 목록 파일 발견: {failed_docs_filename}")
        failed_docs = load_from_json(failed_docs_filename)
        print(f"재시도할 실패 문서 수: {len(failed_docs)}")
        
        # 실패 문서만 재시도할지 확인
        retry_only_failed = input("실패한 문서만 재시도하시겠습니까? (y/n): ").lower() == 'y'
        if retry_only_failed:
            print("실패한 문서만 재시도합니다.")
    else:
        print("실패 문서 목록 파일이 없습니다. 전체 문서를 크롤링합니다.")
        retry_only_failed = False

    processed_doc_numbers = set()

    with sync_playwright() as p:
        download_dir = os.path.join(os.getcwd(), "D:\\PythonProject\\llm\\crawling\\data")
        os.makedirs(download_dir, exist_ok=True)

        # Chrome(Chromium) 브라우저 실행 설정
        browser = p.chromium.launch(
            headless=False,
            channel='chrome'
        )
        context = browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # 초기 페이지 접속 및 메뉴 선택
        page.goto("https://taxlaw.nts.go.kr/index.do")
        
        # 지정된 메뉴 클릭
        page.click("//*[@id='header']/nav/div/ul/li[4]/div")
        page.wait_for_selector("//*[@id='siteMap1']", state="visible")
        
        # 서브메뉴 클릭
        page.click("//*[@id='siteMap1']")
        
        try:
            # 해석례/판례 선택
            interpretation_xpath = '//*[@id="siteMapArea"]/li[2]/ul/li[1]/ul/li[1]'
            # 판례 메뉴의 XPath
            precedent_xpath = '//*[@id="siteMapArea"]/li[3]/ul/li[1]/ul/li[1]'
            
            selected_xpath = interpretation_xpath
            doc_type = "판례"
            
            page.wait_for_selector(selected_xpath, state="visible")
            menu_text = page.locator(selected_xpath).inner_text()
            
            if "판례" in menu_text:
                doc_type = "판례"
            
            page.click(selected_xpath)
            print(f"선택된 문서 유형: {doc_type}")
            
            # 키워드 검색 수행
            use_search = True  # 검색 사용 여부
            if use_search:
                search_keyword(page, "부당행위계산부인 인건비")
                # 검색 결과 목록 선택자
                list_selector = '//*[@id="collectionDiv"]/div[4]/ul/li'
                more_button_selector = '//*[@id="collectionDiv"]/div[4]/div/button'
            else:
                # 일반 목록 선택자
                list_selector = '#bdltCtl > li'
                more_button_selector = '#boardMain > div'
            
            # 문서 목록 처리
            while True:
                try:
                    # 문서 목록이 로드될 때까지 대기
                    page.wait_for_selector('//*[@id="collectionDiv"]/div[4]/ul/li', state='visible', timeout=5000)
                    list_elements = page.query_selector_all('//*[@id="collectionDiv"]/div[4]/ul/li')
                    print(f"현재 페이지의 문서 개수: {len(list_elements)}")
                    
                    for idx, element in enumerate(list_elements, 1):
                        try:
                            # 문서 번호와 URL 추출
                            doc_number_xpath = f'//*[@id="collectionDiv"]/div[4]/ul/li[{idx}]/div[1]/div[1]/ul/li[1]/strong'
                            doc_number = page.locator(doc_number_xpath).inner_text()
                            
                            # 실패 문서만 재시도하는 경우, 실패 목록에 없는 문서는 건너뛰기
                            if retry_only_failed and doc_number not in failed_docs:
                                continue
                                
                            # 이미 성공한 문서는 건너뛰기
                            if doc_number in scraped_docs:
                                continue
                                
                            try:
                                # 문서 유형 확인 (xpath 사용)
                                doc_type_xpath = f'//*[@id="collectionDiv"]/div[4]/ul/li[{idx}]/div[1]/div[1]/a/ul/li[1]'
                                doc_type_element = page.locator(doc_type_xpath)
                                
                                if doc_type_element.is_visible():
                                    current_doc_type = doc_type_element.inner_text()
                                    print(f"문서 유형: {current_doc_type}")
                                    
                                    # 판례나 심판인 경우에만 판례 크롤링 사용
                                    use_precedent = any(type_str in current_doc_type for type_str in ['판례', '심판'])
                                else:
                                    use_precedent = False
                                    print("문서 유형을 찾을 수 없습니다.")
                                
                                # 문서 새 페이지 열기
                                with context.expect_page() as new_page_info:
                                    # 제목 클릭을 위한 xpath
                                    title_xpath = f'//*[@id="collectionDiv"]/div[4]/ul/li[{idx}]/div[1]/div[1]/a'
                                    page.locator(title_xpath).click()
                                
                                new_page = new_page_info.value
                                new_page.wait_for_load_state('networkidle')
                                
                                # 문서 크롤링 시도
                                try:
                                    if use_precedent:
                                        print(f"판례/심판 문서 크롤링 시작: {doc_number}")
                                        doc_info = scrape_precedent_doc(new_page, download_dir)
                                    else:
                                        print(f"해석례 문서 크롤링 시작: {doc_number}")
                                        try:
                                            doc_info = scrape_interpretation_doc(new_page, download_dir)
                                        except Exception as e:
                                            print(f"해석례 크롤링 중 오류 발생:")
                                            print(f"- 문서번호: {doc_number}")
                                            print(f"- 오류 위치: {e.__traceback__.tb_frame.f_code.co_name}")
                                            print(f"- 오류 라인: {e.__traceback__.tb_lineno}")
                                            print(f"- 오류 메시지: {str(e)}")
                                            raise e
                                        
                                    if doc_info:
                                        scraped_docs[doc_number] = doc_info
                                        processed_doc_numbers.add(doc_number)
                                        save_to_json(scraped_docs, json_filename)
                                        
                                        # 성공한 경우 실패 목록에서 제거
                                        if doc_number in failed_docs:
                                            del failed_docs[doc_number]
                                            save_to_json(failed_docs, failed_docs_filename)
                                    else:
                                        raise Exception("문서 정보 수집 실패")
                                    
                                except Exception as e:
                                    failed_docs[doc_number] = {
                                        'doc_number': doc_number,
                                        'url': doc_url,
                                        'error_message': str(e),
                                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                                    }
                                    save_to_json(failed_docs, failed_docs_filename)
                                    print(f"문서 처리 실패 정보 저장: {doc_number}")
                                    continue
                                
                            except Exception as e:
                                print(f"문서 처리 중 오류 발생: {str(e)}")
                                continue
                            
                            new_page.close()
                            time.sleep(1)
                            
                        except Exception as e:
                            print(f"문서 처리 중 오류 발생: {str(e)}")
                            continue
                    
                    # 더보기 버튼 처리
                    try:
                        # 더보기 버튼의 xpath 수정
                        more_button = page.locator('//*[@id="moreSrchBtn"]/button')
                        if not more_button.is_visible():
                            print("더 이상 더보기 버튼이 없습니다.")
                            break
                            
                        print("더보기 버튼 클릭...")
                        more_button.click()
                        
                        # 새로운 문서 로딩 대기
                        page.wait_for_load_state('networkidle')
                        time.sleep(2)  # 추가 대기 시간
                        
                        # 새로운 문서 목록 확인
                        new_elements = page.query_selector_all('//*[@id="collectionDiv"]/div[4]/ul/li')
                        if len(new_elements) <= len(list_elements):
                            print("새로운 문서가 로드되지 않았습니다.")
                            break
                        
                        print(f"새로운 문서 {len(new_elements) - len(list_elements)}개 로드됨")
                            
                    except Exception as e:
                        print(f"더보기 버튼 처리 중 오류 발생: {str(e)}")
                        break
                        
                except Exception as e:
                    print(f"더록 처리 중 오류 발생: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"처리 중 오류 발생: {str(e)}")
            
        finally:
            # 크롤링 종료 시 실패 문서 목록 저장
            if failed_docs:
                save_to_json(failed_docs, failed_docs_filename)
                print(f"실패한 문서 목록이 {failed_docs_filename}에 저장되었습니다.")
                
                # Excel 파일로도 저장
                failed_docs_df = pd.DataFrame.from_dict(failed_docs, orient='index')
                failed_docs_df.to_excel("failed_documents.xlsx", index=False)
                print("실패한 문서 목록이 failed_documents.xlsx에 저장되었습니다.")
            
        browser.close()
        
    return scraped_docs

def save_to_json(data, filename):
    """JSON 파일로 데이터 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_from_json(filename):
    """JSON 파일에서 데이터 로드"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {item['doc_num']: item for item in data if 'doc_num' in item}
            return data
    return {}

def main():
    scraped_docs_results = crawl_with_playwright()
    print(f"총 {len(scraped_docs_results)}개의 문서가 크롤링되었습니다.")

if __name__ == "__main__":
    main()