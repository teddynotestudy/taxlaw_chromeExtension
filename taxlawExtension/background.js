// 현재 열린 팝업 창의 ID를 저장할 변수
let popupWindowId = null;

// 단축키 명령어 리스너
chrome.commands.onCommand.addListener(function(command) {
    console.log('Command received:', command);
    if (command === 'capture-text') {
        // 현재 활성화된 탭에 메시지 전송
        chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { action: 'capture-text' }, (response) => {
                    if (response && response.success) {
                        if (popupWindowId === null) {
                            // 첫 실행 시 새 팝업 창 생성
                            chrome.windows.create({
                                url: 'popup.html',
                                type: 'popup',
                                width: 700,
                                height: 800,
                                top: 50,
                                left: 50
                            }, (window) => {
                                popupWindowId = window.id;
                            });
                        } else {
                            // 기존 팝업 창이 있는 경우 해당 창이 존재하는지 확인
                            chrome.windows.get(popupWindowId, (window) => {
                                if (chrome.runtime.lastError) {
                                    // 창이 닫혀있는 경우 새로 생성
                                    chrome.windows.create({
                                        url: 'popup.html',
                                        type: 'popup',
                                        width: 700,
                                        height: 800,
                                        top: 50,
                                        left: 50
                                    }, (window) => {
                                        popupWindowId = window.id;
                                    });
                                } else {
                                    // 창이 존재하는 경우 포커스만 이동
                                    chrome.windows.update(popupWindowId, { 
                                        focused: true,
                                        drawAttention: true
                                    });
                                }
                            });
                        }
                    }
                });
            }
        });
    } else if (command === 'show-panel') {
        chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { action: 'show-panel' }, function(response) {
                    console.log('show-panel response:', response);
                });
            }
        });
    }
});

// 팝업 창이 닫힐 때 ID 초기화
chrome.windows.onRemoved.addListener((windowId) => {
    if (windowId === popupWindowId) {
        popupWindowId = null;
    }
});

// 확장프로그램이 설치되거나 업데이트될 때 실행
chrome.runtime.onInstalled.addListener(function() {
    console.log('판례 Summary 확장프로그램이 설치되었습니다.');
}); 