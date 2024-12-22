let hoveredElement = null;
let lastCapturedText = null;
let isValidDocType = false;
let targetResponse = null;

// 유효한 문서 타입 목록
const validDocTypes = ['질의회신', '사전답변', '심판청구', '판례'];

// 마우스 오버 이벤트 리스너
document.addEventListener('mouseover', function(e) {
    const listItem = e.target.closest('div.board_box');
    if (listItem) {
        // 상위 ul 요소 찾기
        const parentUl = listItem.closest('ul[data-collection-ul]');
        if (!parentUl) return;

        // collection 타입 확인
        const collectionType = parentUl.getAttribute('data-collection-ul');
        
        // "question"(세법해석례)이나 "precedent"(판례결정례)인 경우에만 처리
        if (collectionType === 'question' || collectionType === 'precedent') {
            hoveredElement = listItem;
            
            // 판례번호 추출
            const caseNumberElement = listItem.querySelector('div.substance_wrap > ul > li:nth-child(1) > strong');
            if (caseNumberElement) {
                lastCapturedText = caseNumberElement.textContent.trim();
                console.log('발견된 판례번호:', lastCapturedText);
                // 시각적 피드백 추가
                hoveredElement.style.outline = '2px solid #4CAF50';
            }
        } else {
            // 다른 collection 타입인 경우 호버 효과 제거
            hoveredElement = null;
            lastCapturedText = null;
        }
    }
});

// 마우스 아웃 이벤트 리스너
document.addEventListener('mouseout', function(e) {
    const listItem = e.target.closest('div.board_box');
    if (listItem && hoveredElement === listItem) {
        const parentUl = listItem.closest('ul[data-collection-ul]');
        if (parentUl) {
            const collectionType = parentUl.getAttribute('data-collection-ul');
            if (collectionType === 'question' || collectionType === 'precedent') {
                hoveredElement.style.outline = '';
            }
        }
    }
});

// 판례번호 추출 함수
function extractCaseNumber(element) {
    if (!element) return null;
    const caseNumberElement = element.querySelector('.subs_detail li:first-child strong');
    if (caseNumberElement) {
        const text = caseNumberElement.textContent.trim();
        console.log('추출된 판례번호:', text);
        return text;
    }
    return null;
}

// 네트워크 요청 모니터링
(function() {
    // Fetch API 가로채기
    const originalFetch = window.fetch;
    window.fetch = async function(input, init) {
        const url = typeof input === 'string' ? input : input.url;
        
        // nlogger 요청 차단
        if (url.toString().includes('nlog/log/event')) {
            return new Promise((resolve) => {
                resolve(new Response('', {
                    status: 200,
                    statusText: 'OK'
                }));
            });
        }

        console.log('Fetch 요청 발생:', url);
        
        try {
            const response = await originalFetch.apply(this, arguments);
            
            if (url.includes('action.do')) {
                console.log('action.do 요청 감지:', url);
                const responseClone = response.clone();
                
                responseClone.text().then(text => {
                    try {
                        const jsonResponse = JSON.parse(text);
                        console.log('action.do 응답:', {
                            url: url,
                            data: jsonResponse
                        });
                        
                        // ASEISA001MR01 데이터 확인
                        if (jsonResponse.data && jsonResponse.data.ASEISA001MR01) {
                            console.log('Found ASEISA001MR01 data:', jsonResponse.data.ASEISA001MR01);
                            targetResponse = jsonResponse;
                        }
                    } catch (e) {
                        console.log('action.do 응답 (텍스트):', {
                            url: url,
                            text: text.substring(0, 200) + '...'
                        });
                    }
                });
            }
            
            return response;
        } catch (error) {
            console.error('Fetch 에러:', error);
            throw error;
        }
    };

    // XMLHttpRequest 가로채기
    const originalXHR = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function() {
        const url = arguments[1];
        console.log('XHR 요청:', url);
        
        if (url.includes('action.do')) {
            this.addEventListener('load', function() {
                try {
                    const response = JSON.parse(this.responseText);
                    console.log('action.do XHR 응답:', {
                        url: url,
                        data: response
                    });
                    
                    // ASEISA001MR01 데이터 확인
                    if (response.data && response.data.ASEISA001MR01) {
                        console.log('Found ASEISA001MR01 data:', response.data.ASEISA001MR01);
                        targetResponse = response;
                    }
                } catch (e) {
                    console.log('action.do XHR 응답 (텍스트):', {
                        url: url,
                        text: this.responseText.substring(0, 200) + '...'
                    });
                }
            });
        }
        
        return originalXHR.apply(this, arguments);
    };
})();

// 수집된 판례번호를 저장할 변수들
let collectedCaseNumbers = {
    question: [], // 세법해석례 번호들
    precedent: [] // 판례결정례 번호들
};

// 디바운스 타이머
let debounceTimer = null;
let isProcessing = false;

// 판례 수집 함수
function collectCaseNumbers() {
    if (isProcessing) return;
    isProcessing = true;

    let newCollectedNumbers = {
        question: [],
        precedent: []
    };

    // Case 1: 검색 결과 페이지의 경우
    const questionList = document.querySelector('#collectionDiv > div:nth-child(4) > ul[data-collection-ul="question"]');
    const precedentList = document.querySelector('#collectionDiv > div:nth-child(5) > ul[data-collection-ul="precedent"]');
    
    // Case 2: 전체 목록 페이지의 경우
    const fullList = document.querySelector('#bdltCtl');
    
    if (questionList || precedentList) {
        // 검색 결과 페이지 처리
        const hasQuestionItems = questionList && questionList.children.length > 0;
        const hasPrecedentItems = precedentList && precedentList.children.length > 0;
        
        if (hasQuestionItems) {
            Array.from(questionList.children).forEach(item => {
                const caseNumberElement = item.querySelector('div.board_box > div.substance_wrap > ul > li:nth-child(1) > strong');
                if (caseNumberElement) {
                    newCollectedNumbers.question.push(caseNumberElement.textContent.trim());
                }
            });
        }
        
        if (hasPrecedentItems) {
            Array.from(precedentList.children).forEach(item => {
                const caseNumberElement = item.querySelector('div.board_box > div.substance_wrap > ul > li:nth-child(1) > strong');
                if (caseNumberElement) {
                    newCollectedNumbers.precedent.push(caseNumberElement.textContent.trim());
                }
            });
        }
    } else if (fullList && fullList.children.length > 0) {
        // URL을 확인하여 현재 페이지 타입 판단
        const currentUrl = window.location.href;
        const isQuestionPage = currentUrl.includes('USEQTJ001M.do');
        const isPrecedentPage = currentUrl.includes('USEPDI001M.do');
        
        Array.from(fullList.children).forEach(item => {
            const caseNumberElement = item.querySelector('div.board_box > div.substance_wrap > ul > li:nth-child(1) > strong');
            if (caseNumberElement) {
                const number = caseNumberElement.textContent.trim();
                if (isQuestionPage) {
                    newCollectedNumbers.question.push(number);
                } else if (isPrecedentPage) {
                    newCollectedNumbers.precedent.push(number);
                }
            }
        });
    }

    // 이전 수집 결과와 비교하여 변경사항이 있는 경우에만 업데이트
    const hasChanged = JSON.stringify(collectedCaseNumbers) !== JSON.stringify(newCollectedNumbers);
    if (hasChanged) {
        collectedCaseNumbers = newCollectedNumbers;
        
        // 수집 결과 콘솔에 출력
        if (collectedCaseNumbers.question.length > 0) {
            console.log('수집된 세법해석례:', collectedCaseNumbers.question.length + '개');
        }
        if (collectedCaseNumbers.precedent.length > 0) {
            console.log('수집된 판례결정례:', collectedCaseNumbers.precedent.length + '개');
        }

        // 사이드 패널 내용 업데이트
        updateSidePanel();
    }
    
    isProcessing = false;
}

// 사이드 패널 업데이트 함수
function updateSidePanel() {
    if (collectedCaseNumbers.question.length > 0 || collectedCaseNumbers.precedent.length > 0) {
        const content = `
            <h2>검색된 판례 목록</h2>
            <div style="margin-top: 15px;">
                ${collectedCaseNumbers.question.length > 0 ? `
                    <div style="margin-bottom: 15px;">
                        <h3 style="font-size: 14px; margin-bottom: 10px;">세법해석례 (${collectedCaseNumbers.question.length})</h3>
                        ${collectedCaseNumbers.question.map(number => `
                            <div style="margin-bottom: 10px; padding: 8px; background: #f5f5f5; border-radius: 4px;">
                                <p>${number}</p>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                ${collectedCaseNumbers.precedent.length > 0 ? `
                    <div>
                        <h3 style="font-size: 14px; margin-bottom: 10px;">판례결정례 (${collectedCaseNumbers.precedent.length})</h3>
                        ${collectedCaseNumbers.precedent.map(number => `
                            <div style="margin-bottom: 10px; padding: 8px; background: #f5f5f5; border-radius: 4px;">
                                <p>${number}</p>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
        
        if (!sidePanel) {
            sidePanel = initializeSidePanel();
        }
        sidePanel.querySelector('.tax-law-side-panel-content').innerHTML = content;
    }
}

// 페이지 로드 및 DOM 변경 감지
const observer = new MutationObserver(function(mutations) {
    // 이전 타이머 취소
    if (debounceTimer) {
        clearTimeout(debounceTimer);
    }
    
    // 새로운 타이머 설정 (500ms 후에 실행)
    debounceTimer = setTimeout(() => {
        collectCaseNumbers();
    }, 500);
});

// observer는 계속 실행 상태로 유지 (disconnect 제거)

// DOM이 준비되면 감시 시작
function startObserver() {
    if (document.body) {
        console.log('DOM 감시 시작');
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    } else {
        console.log('document.body 없음, 대기 중...');
        setTimeout(startObserver, 100); // 100ms 후 다시 시도
    }
}

// document가 준비되면 observer 시작
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startObserver);
} else {
    startObserver();
}

// 메시지 리스너 수정
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    console.log('메시지 수신:', request.action);
    if (request.action === 'show-panel') {
        console.log('show-panel 액션 수신');
        // 패널이 이미 초기화되어 있고 내용이 있는지 확인
        if (sidePanel) {
            const content = sidePanel.querySelector('.tax-law-side-panel-content').innerHTML;
            console.log('패널 존재 여부:', !!sidePanel, '내용 존재 여부:', !!content);
            
            isPanelOpen = !isPanelOpen;
            if (isPanelOpen) {
                sidePanel.classList.add('open');
                console.log('패널 열림');
            } else {
                sidePanel.classList.remove('open');
                console.log('패널 닫힘');
            }
            sendResponse({ success: true });
        } else {
            console.log('패널이 초기화되지 않았거나 내용이 없습니다');
            sendResponse({ success: false, message: '표시할 내용이 없습니다.' });
        }
        return true;
    }
    
    // capture-text 핸들러 수정 - 사이드 패널 애니메이션 제거
    if (request.action === 'capture-text') {
        if (hoveredElement && lastCapturedText) {
            chrome.storage.local.set({ 'capturedText': lastCapturedText }, function() {
                console.log('텍스트 저장됨:', lastCapturedText);
                hoveredElement.style.outline = '2px solid red';
                setTimeout(() => {
                    hoveredElement.style.outline = '2px solid #4CAF50';
                }, 500);
                
                sendResponse({ success: true });
            });
            return true;
        } else {
            console.log('캡처할 텍스트 없음');
            sendResponse({ success: false, message: '캡처할 텍스트가 없습니다.' });
        }
    }
    if (request.action === 'get-target-response') {
        sendResponse({ response: targetResponse });
        return true;
    }
    if (request.action === 'get-case-content') {
        const content = document.querySelector('.main_contents')?.innerText || '';
        sendResponse({ content: content });
        return true;
    }
});

// 필요한 경우 저장된 응답을 가져오는 함수
function getTargetResponse() {
    return targetResponse;
}

// 사이드 패널 초기화 함수 수정
function initializeSidePanel() {
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        .tax-law-side-panel {
            position: fixed;
            top: 0;
            right: -33.33vw;
            width: 33.33vw;
            height: 100vh;
            background: white;
            box-shadow: -2px 0 5px rgba(0,0,0,0.1);
            z-index: 10000;
            transition: right 0.3s ease;
            padding: 20px;
            box-sizing: border-box;
            overflow-y: auto;
        }

        .tax-law-side-panel.open {
            right: 0;
        }

        .tax-law-side-panel-close {
            position: absolute;
            top: 15px;
            left: 15px;
            cursor: pointer;
            padding: 8px 12px;
            background: #f0f0f0;
            border: none;
            border-radius: 4px;
            font-size: 14px;
        }

        .tax-law-side-panel-close:hover {
            background: #e0e0e0;
        }

        .tax-law-side-panel h2 {
            font-size: 16px;
            margin-top: 10px;
            margin-bottom: 15px;
            padding-left: 50px; /* 닫기 버튼 공간 확보 */
        }
    `;
    document.head.appendChild(styleSheet);

    const sidePanel = document.createElement('div');
    sidePanel.className = 'tax-law-side-panel';
    sidePanel.innerHTML = `
        <button class="tax-law-side-panel-close">닫기</button>
        <div class="tax-law-side-panel-content"></div>
    `;

    // 닫기 버튼 이벤트 리스너를 여기서 바로 추가
    const closeButton = sidePanel.querySelector('.tax-law-side-panel-close');
    closeButton.addEventListener('click', () => {
        sidePanel.classList.remove('open');
        isPanelOpen = false;
    });

    document.body.appendChild(sidePanel);
    return sidePanel;
}

let sidePanel = null;
let isPanelOpen = false;

// 패널 토글 함수 수정
function toggleSidePanel(content = '') {
    if (!sidePanel) {
        sidePanel = initializeSidePanel();
    }

    if (!content) {
        // content가 없으면 패널을 닫음
        sidePanel.classList.remove('open');
        isPanelOpen = false;
        return;
    }

    // content가 있으면 패널을 열거나 내용을 업데이트
    sidePanel.querySelector('.tax-law-side-panel-content').innerHTML = content;
    if (!isPanelOpen) {
        sidePanel.classList.add('open');
        isPanelOpen = true;
    }
}

// DOM 준비되면 사이드 패널 초기화
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        sidePanel = initializeSidePanel();
    });
} else {
    sidePanel = initializeSidePanel();
}
  