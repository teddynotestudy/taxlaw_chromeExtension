from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from openai import OpenAI
import os
from pydantic import BaseModel
from dotenv import load_dotenv
from templates.prompt_template import CASE_SUMMARY_TEMPLATE

# .env 파일 로드
load_dotenv()

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

# HTML 파일을 제공하는 엔드포인트
@app.get("/data/{case_number}.html", response_class=HTMLResponse)
async def get_case_file(case_number: str):
    try:
        file_path = f"data/{case_number}.html"
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

@app.get("/data/{case_number}/metadata")
async def get_case_metadata(case_number: str):
    try:
        file_path = f"data/{case_number}.md"
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            
        # metadata 섹션 파싱
        metadata = {}
        in_metadata = False
        in_basic_info = False
        
        for line in content.split('\n'):
            line = line.strip()
            if line == '# Metadata':  # 대소문자 구분
                in_metadata = True
                continue
            elif in_metadata and line == '## 기본정보':
                in_basic_info = True
                continue
            elif in_basic_info and line.startswith('##'):
                break
            elif in_basic_info and line.startswith('- '):  # "- " 로 시작하는 라인 처리
                if ':' in line:
                    # "- key: value" 형식 파싱
                    key_value = line[2:].split(':', 1)  # "- " 제거 후 분리
                    if len(key_value) == 2:
                        key = key_value[0].strip()
                        value = key_value[1].strip()
                        metadata[key] = value
        
        return {
            "문서명": metadata.get("문서명", ""),
            "url": metadata.get("URL", ""),  # 대문자 URL로 수정
            "문서번호": metadata.get("문서번호", ""),
            "세목": metadata.get("세목", ""),
            "판결결과": metadata.get("판결결과", "")
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="메타데이터 파일을 찾을 수 없습니다")

class SummarizeRequest(BaseModel):
    content: str

@app.post("/summarize")
async def summarize_text(request: SummarizeRequest):
    try:
        # 템플릿에 내용 삽입
        prompt = CASE_SUMMARY_TEMPLATE.format(content=request.content)
        
        # response = client.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=[
        #         {"role": "system", "content": "당신은 법률 전문가입니다. 판례를 분석하고 요약하는 것이 전문입니다."},
        #         {"role": "user", "content": prompt}
        #     ],
        #     temperature=0.7,
        #     max_tokens=1000
        # )
        
        # summary = response.choices[0].message.content
        #return {"summary": summary}
        return {"summary": "임시주석처리"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=3000)
  