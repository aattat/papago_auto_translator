import os
import sys
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import tkinter as tk
from tkinter import filedialog

LANGUAGE_MAP = {
    '1': {'code': 'ko', 'name': '한국어'},
    '2': {'code': 'ja', 'name': '일본어'},
    '3': {'code': 'en', 'name': '영어'},
    '4': {'code': 'zh-CN', 'name': '중국어(간체)'},
    '5': {'code': 'zh-TW', 'name': '중국어(번체)'},
    '6': {'code': 'es', 'name': '스페인어'},
    '7': {'code': 'fr', 'name': '프랑스어'},
    '8': {'code': 'de', 'name': '독일어'}, 
    '9': {'code': 'ru', 'name': '러시아어'},
    '10': {'code': 'pt', 'name': '포르투갈어'}, 
    '11': {'code': 'it', 'name': '이탈리아어'},
    '12': {'code': 'vi', 'name': '베트남어'}, 
    '13': {'code': 'th', 'name': '태국어'}, 
    '14': {'code': 'id', 'name': '인도네시아어'}, 
    '15': {'code': 'hi', 'name': '힌디어'}, 
    '16': {'code': 'ar', 'name': '아랍어'} 
}

def select_language(prompt, options):
    print(prompt)
    for key, value in options.items():
        print(f"{key}. {value['name']}")
    while True:
        choice = input("선택 (번호 입력): ").strip()
        if choice in options:
            return options[choice]
        print("잘못된 선택입니다. 다시 입력해주세요.")

def split_text_by_lines(input_path, output_dir, max_chars=2999):
    os.makedirs(output_dir, exist_ok=True)
    chunk = []
    current_length = 0
    chunk_number = 1

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_length = len(line)
            
            if current_length + line_length > max_chars:
                output_path = os.path.join(output_dir, f'chunk_{chunk_number:04d}.txt')
                with open(output_path, 'w', encoding='utf-8') as out:
                    out.writelines(chunk)
                chunk_number += 1
                chunk = []
                current_length = 0
            
            chunk.append(line)
            current_length += line_length

        if chunk:
            output_path = os.path.join(output_dir, f'chunk_{chunk_number:04d}.txt')
            with open(output_path, 'w', encoding='utf-8') as out:
                out.writelines(chunk)
    return chunk_number

def check_and_reset_language(driver, expected_source, expected_target):
    """URL의 언어 설정을 검사하고 필요시 재설정하는 함수"""
    current_url = driver.current_url
    
    # URL 파라미터 파싱
    parsed = urllib.parse.urlparse(current_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    # 현재 언어 코드 추출
    current_source = query_params.get('sk', [expected_source])[0]
    current_target = query_params.get('tk', [expected_target])[0]

    # 언어 설정이 변경되었는지 확인
    if current_source != expected_source or current_target != expected_target:
        print(f"⚠️ 언어 설정 변경 감지: {current_source}→{current_target}")
        print(f"🔄 원래 설정 복구 시도: {expected_source}→{expected_target}")
        
        # 언어 강제 재설정
        driver.get(
            f"https://papago.naver.com/"
            f"?sk={expected_source}"
            f"&tk={expected_target}"
            f"&hn=0"
        )
        
        # 페이지 안정화 대기
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#txtSource"))
        )
        return True
    return False

def translate_text(driver, text, expected_source, expected_target):
    max_retries = 0
    for attempt in range(max_retries + 1):
        try:
            # 언어 설정 체크
            check_and_reset_language(driver, expected_source, expected_target)
            
            # 이전 출력 텍스트 저장
            previous_output = driver.find_element(By.ID, "txtTarget").text.strip()
            
            # 입력 영역 캐싱 및 초기화
            input_area = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "txtSource"))
            )
            input_area.clear()
            input_area.send_keys("a")
            input_area.send_keys(Keys.BACK_SPACE)
            
            # 입력 텍스트 초기화 감지 대기
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: len(driver.find_element(By.ID, "txtTarget").text.strip()) == 0
                )
            except TimeoutException:
                print(f"번역 실패 (시간 초과): {str(e)}")
                os.system('taskkill /f /im cmd.exe')
                sys.exit("번역 실패로 인해 프로그램 종료") 
            
            # 자바스크립트로 텍스트 직접 입력
            driver.execute_script("arguments[0].value = arguments[1];", input_area, text)
            
            # 더미 입력으로 이벤트 트리거
            input_area.send_keys(" ")  # 공백 추가
            input_area.send_keys(Keys.BACK_SPACE)  # 공백 제거
            
            # 번역 버튼 JavaScript 클릭
            driver.find_element(By.ID, "btnTranslate").click()
            
            # 출력 텍스트 변경 감지 대기
            WebDriverWait(driver, 10).until(
                lambda d: driver.find_element(By.ID, "txtTarget").text.strip() != previous_output
                and len(driver.find_element(By.ID, "txtTarget").text.strip()) > 5
            )
            
            # 최종 결과 추출
            output_area = driver.find_element(By.ID, "txtTarget")
            return output_area.text.strip()
        
        except Exception as e:
            print(f"번역 실패 (시간 초과): {str(e)}")
            os.system('taskkill /f /im cmd.exe')
            sys.exit("번역 실패로 인해 프로그램 종료") 
    return ""

def merge_translated_files(translated_folder, final_output_path):
    translated_files = sorted(
        [f for f in os.listdir(translated_folder) if f.startswith('translated_')],
        key=lambda x: int(x.split('_')[2].split('.')[0])
    )
    
    with open(final_output_path, 'w', encoding='utf-8') as merged_file:
        for filename in translated_files:
            file_path = os.path.join(translated_folder, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                merged_file.write(f.read() + '\n')

def get_processed_indices(translated_dir):
    processed = set()
    for f in os.listdir(translated_dir):
        if f.startswith('translated_chunk_'):
            parts = f.split('_')
            try:
                num = int(parts[2].split('.')[0])
                processed.add(num)
            except ValueError:
                continue
    return processed

def main_process():
    root = tk.Tk()
    root.withdraw()
    original_file = filedialog.askopenfilename(
        title="번역할 텍스트 파일 선택",
        filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        initialdir=os.getcwd()  # 기본 경로 설정
    )
    root.destroy()

    if not original_file:
        print("🚫 파일 선택이 취소되었습니다. 프로그램을 종료합니다.")
        sys.exit()
    
    print(f"📄 선택한 텍스트 파일: {original_file}")
    
    # 언어 선택
    print("="*40)
    print("번역 언어 선택: 출발 언어 → 도착 언어")
    print("-"*40)
    source_lang = select_language("출발 언어를 선택하세요:", LANGUAGE_MAP)
    target_lang = select_language("\n" + "도착 언어를 선택하세요:", LANGUAGE_MAP)
    print("="*40)
    
    
    base_name = os.path.splitext(os.path.basename(original_file))[0]
    split_dir = f"./{base_name}(분할 파일 번역전)"
    translated_dir = f"./{base_name}(분할 파일 번역후 - {target_lang['name']})"
    final_output = f"./{base_name}({source_lang['name']}→{target_lang['name']} 번역완료).txt"

    # 분할 파일 체크 및 생성
    if os.path.exists(split_dir) and os.path.isdir(split_dir):
        split_files = sorted([f for f in os.listdir(split_dir) if f.startswith('chunk_')])
        total_chunks = len(split_files)
        print(f"📁 기존 분할 파일 {total_chunks}개를 사용합니다.")
    else:
        print("📁 원본 파일 분할 중...")
        total_chunks = split_text_by_lines(original_file, split_dir)
        print(f"✅ {total_chunks}개 파일로 분할 완료!")

    # 번역된 파일 체크
    os.makedirs(translated_dir, exist_ok=True)
    processed_indices = get_processed_indices(translated_dir)
    print(f"🔍 {len(processed_indices)}개 파일 번역 완료. 남은 청크: {total_chunks - len(processed_indices)}개")
    print("="*40)

    # Chrome 옵션 설정
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")  # 헤드리스 모드
    chrome_options.add_argument("--disable-gpu")  # GPU 가속 비활성화
    chrome_options.add_argument("--no-sandbox")  # 샌드박스 비활성화
    chrome_options.add_argument("--disable-dev-shm-usage")  # 리소스 제한 해제
    chrome_options.add_argument("--window-size=1920,1080")  # 창 크기 고정
    
    # 웹드라이버 초기화
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    driver.get(f"https://papago.naver.com/?sk={source_lang['code']}&tk={target_lang['code']}&hn=0")
    time.sleep(3)

    for idx in range(1, total_chunks + 1):
        chunk_file = f"chunk_{idx:04d}.txt"
        input_path = os.path.join(split_dir, chunk_file)
        output_path = os.path.join(translated_dir, f"translated_{chunk_file}")

        if idx in processed_indices:
            print(f"[{idx}/{total_chunks}] 이미 번역 완료 → 건너뛰기")
            continue

        try:
            print(f"\n[{idx}/{total_chunks}] {chunk_file} 번역 시작...")
            
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()

            translated_text = ""
            max_retries = 0
            
            for attempt in range(max_retries + 1):
                translated_text = translate_text(
                    driver, 
                    text, 
                    source_lang['code'], 
                    target_lang['code']
                )
                if translated_text.strip():
                    break
                if attempt < max_retries:
                    print(f"[{idx}/{total_chunks}] 재시도 ({attempt+1}/{max_retries})")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translated_text)
            
            if translated_text.strip():
                print(f"[{idx}/{total_chunks}] ✅ 번역 성공")
            else:
                print(f"[{idx}/{total_chunks}] ❌ 번역 실패 (빈 결과)")
                os.system('taskkill /f /im cmd.exe')
                sys.exit("번역 실패로 인해 프로그램 종료")

        except Exception as e:
            print(f"[{idx}/{total_chunks}] ❌ 치명적 오류: {str(e)}")
            os.system('taskkill /f /im cmd.exe')
            sys.exit("번역 실패로 인해 프로그램 종료")

    driver.quit()

    print("="*40)
    print("📂 번역 파일 병합 중...")
    merge_translated_files(translated_dir, final_output)
    print(f"🎉 최종 파일 저장 완료: {final_output}")
    print("="*40)
    
    input("번역 완료! 엔터 키를 두 번 눌러 프로그램을 종료하세요.")

if __name__ == "__main__":
    main_process()