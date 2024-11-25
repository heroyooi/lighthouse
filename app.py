from flask import Flask, jsonify, render_template, send_file
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

def run_lighthouse(url):
    """Lighthouse CLI를 실행하고 FCP, LCP 데이터를 반환"""
    try:
        result = subprocess.run(
            [
                'C:\\Program Files\\nodejs\\lighthouse.cmd', url, 
                '--quiet', '--output=json', '--only-categories=performance', 
                '--disable-storage-reset', '--max-wait-for-load=30000', '--headless',
                '--emulated-form-factor=desktop',   # 데스크탑 환경 설정
                '--throttling-method=provided'     # 네트워크 속도 제한 제거
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0 or not result.stdout:
            return {"url": url, "error": f"Lighthouse 실행 실패: {result.stderr}"}

        lighthouse_output = json.loads(result.stdout)
        audits = lighthouse_output["audits"]
        fcp = audits["first-contentful-paint"]["displayValue"]
        lcp = audits["largest-contentful-paint"]["displayValue"]

        return {"url": url, "FCP": fcp, "LCP": lcp}

    except json.JSONDecodeError as e:
        return {"url": url, "error": "JSON 디코딩 에러 발생: " + str(e)}
    except Exception as e:
        return {"url": url, "error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['GET'])
def check():
    urls = [
        "https://www.megagong.net",
        "https://gong.conects.com",
        "https://gosi.hackers.com",
        "https://gov.eduwill.net",
        "https://www.pmg.co.kr",
        "https://www.modoogong.com",
        "https://sobang.megagong.net",
        "https://sobang.conects.com",
        "https://fire.hackers.com",
        "https://www.megajob.co.kr"
    ]

    # 첫 번째 실행: 병렬로 모든 URL 체크
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(run_lighthouse, urls))

    # 실패한 URL만 추출
    failed_urls = [result['url'] for result in results if 'error' in result]
    
    # 실패한 URL들만 다시 실행
    if failed_urls:
        with ThreadPoolExecutor() as executor:
            retry_results = list(executor.map(run_lighthouse, failed_urls))
        
        # 실패한 URL 결과를 다시 합침
        results = [result if 'error' not in result else next(r for r in retry_results if r['url'] == result['url']) for result in results]

    # 결과를 pandas DataFrame으로 변환
    df = pd.DataFrame(results)

    # 실행 시간에 따른 파일명 생성
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"lighthouse_results_{now}.xlsx"
    file_path = os.path.join(os.getcwd(), file_name)
    
    # 엑셀 파일로 저장
    df.to_excel(file_path, index=False)

    # 엑셀 파일 다운로드 링크 반환
    download_url = f"/download/{file_name}"

    # JSON 결과와 엑셀 다운로드 링크 반환
    return jsonify({"metrics": results, "excel_file": download_url})

@app.route('/download/<filename>')
def download(filename):
    """엑셀 파일 다운로드"""
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)