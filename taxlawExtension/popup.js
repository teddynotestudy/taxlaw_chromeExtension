// 판례 파일 가져오는 함수 수정
async function fetchCaseFiles(caseNumber) {
    try {
        // 로컬 웹서버에서 HTML 파일 가져오기
        const response = await fetch(`http://localhost:3000/data/${caseNumber}.html`);
        
        if (!response.ok) {
            throw new Error('파일을 찾을 수 없습니다.');
        }

        const htmlContent = await response.text();
        return { html: htmlContent };
    } catch (error) {
        console.error('로컬 서버 조회 오류:', error);
        return null;
    }
}

async function summarizeContent(content) {
    try {
        const response = await fetch('http://localhost:3000/summarize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: content
            })
        });

        const data = await response.json();
        if (data.error) {
            console.error('요약 API 오류:', data.error);
            return null;
        }
        return data.summary;
    } catch (error) {
        console.error('요약 API 호출 오류:', error);
        return null;
    }
}

// 마크다운 컨버터 초기화
const converter = new showdown.Converter({
    headerLevelStart: 2,  // h1 대신 h2부터 시작
    simplifiedAutoLink: true,
    strikethrough: true,
    tables: true,
    tasklists: true,
    simpleLineBreaks: true
});

// 텍스트 타이핑 효과 함수
function typeWriter(element, text, speed = 20) {
    let i = 0;
    element.innerHTML = ''; // 기존 내용 초기화
    
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// HTML 요소를 순차적으로 표시하는 함수
function streamElements(container, htmlContent, speed = 50) {
    // HTML 파싱을 위한 임시 컨테이너 생성
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlContent;
    
    // 현재 작업중인 요소를 추적하기 위한 변수
    let currentElement = container;
    container.innerHTML = ''; // 컨테이너 초기화
    
    // 모든 텍스트 노드와 요소를 순회하면서 표시
    function* traverseNodes(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            // 텍스트 노드는 단어 단위로 분할
            const words = node.textContent.split(/(\s+)/);
            for (const word of words) {
                if (word.length > 0) {  // 빈 문자열 건너뛰기
                    yield { type: 'text', content: word };
                }
            }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            // 요소 시작 태그
            yield { type: 'startTag', node: node };
            
            // 자식 노드들을 순회
            for (const child of node.childNodes) {
                yield* traverseNodes(child);
            }
            
            // 요소 종료 태그
            yield { type: 'endTag', node: node };
        }
    }

    const iterator = traverseNodes(tempDiv);
    let isProcessing = true;
    
    function processNext() {
        if (!isProcessing) return;
        
        const next = iterator.next();
        if (!next.done) {
            const item = next.value;
            
            try {
                if (item.type === 'text') {
                    const span = document.createElement('span');
                    span.textContent = item.content;
                    currentElement.appendChild(span);
                } else if (item.type === 'startTag') {
                    const elem = document.createElement(item.node.tagName);
                    // 속성 복사
                    for (const attr of item.node.attributes) {
                        elem.setAttribute(attr.name, attr.value);
                    }
                    currentElement.appendChild(elem);
                    currentElement = elem;  // 새로 생성된 요소로 이동
                } else if (item.type === 'endTag') {
                    currentElement = currentElement.parentElement;  // 부모 요소로 이동
                }
                
                setTimeout(processNext, speed);
            } catch (error) {
                console.error('스트리밍 처리 중 오류:', error);
                isProcessing = false;
            }
        }
    }
    
    processNext();
}

// 메타데이터 가져오는 함수 추가
async function fetchMetadata(caseNumber) {
    try {
        const response = await fetch(`http://localhost:3000/data/${caseNumber}/metadata`);
        
        if (!response.ok) {
            throw new Error('메타데이터를 찾을 수 없습니다.');
        }

        return await response.json();
    } catch (error) {
        console.error('메타데이터 조회 오류:', error);
        return null;
    }
}

async function updateCapturedText() {
    const textElement = document.getElementById('capturedText');
    const summaryElement = document.getElementById('summary');
    const titleElement = document.getElementById('documentTitle');
    const urlElement = document.getElementById('documentUrl');

    chrome.storage.local.get(['capturedText'], async function(result) {
        if (result.capturedText) {
            const caseNumber = result.capturedText;
            textElement.textContent = caseNumber;
            
            // 메타데이터 가져오기
            const metadata = await fetchMetadata(caseNumber);
            if (metadata) {
                titleElement.textContent = metadata.문서명;
                document.getElementById('taxType').textContent = metadata.세목;
                document.getElementById('result').textContent = metadata.판결결과;
                if (metadata.url) {
                    document.getElementById('documentUrl').innerHTML = 
                        `<a href="${metadata.url}" target="_blank">판례 원문 보기</a>`;
                }
            }
            
            const caseFiles = await fetchCaseFiles(caseNumber);
            
            if (caseFiles && caseFiles.html) {
                const summary = await summarizeContent(caseFiles.html);
                if (summary) {
                    // showdown을 사용하여 마크다운을 HTML로 변환
                    const htmlContent = converter.makeHtml(summary);
                    
                    // 요약 컨테이너 초기화
                    summaryElement.innerHTML = `
                        <h3>판례 요약</h3>
                        <div class="markdown-content"></div>
                    `;
                    
                    // 스트리밍 효과로 내용 표시
                    const contentElement = summaryElement.querySelector('.markdown-content');
                    streamElements(contentElement, htmlContent, 30);
                }
            } else {
                textElement.textContent = '관련 파일을 찾을 수 없습니다.';
            }
        } else {
            textElement.textContent = '캡처된 판례번호가 없습니다.';
        }
    });
}

// HTML 안전하게 표시하기 위한 함수 수정
function sanitizeHTML(html) {
    // DOMParser를 사용하여 HTML 문자열을 파싱
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // 스크립트 태그 제거 (보안)
    const scripts = doc.getElementsByTagName('script');
    while(scripts[0]) {
        scripts[0].parentNode.removeChild(scripts[0]);
    }

    // body 내용 반환
    return doc.body.innerHTML;
}

// 초기 로드 시 텍스트 업데이트
document.addEventListener('DOMContentLoaded', updateCapturedText);

// storage 변경 감지
chrome.storage.onChanged.addListener(function(changes, namespace) {
    if (namespace === 'local' && changes.capturedText) {
        updateCapturedText();
    }
});
