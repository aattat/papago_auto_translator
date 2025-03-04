import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def split_text_by_lines(input_path, output_dir, max_chars=3000):
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

def translate_text(driver, text):
    max_retries = 0
    for attempt in range(max_retries + 1):
        try:
            input_area = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "txtSource"))  # ✅ 괄호 수정
            )
            input_area.clear()
            time.sleep(0.5)
            input_area.send_keys(text)
            driver.find_element(By.ID, "btnTranslate").click()
            time.sleep(1)
            
            output_area = WebDriverWait(driver, 10).until(
                lambda d: (d.find_element(By.ID, "txtTarget")  # ✅ 조건문 수정
                          if len(d.find_element(By.ID, "txtTarget").text.strip()) > 1 
                          else None)
            )
            return output_area.text
        
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
    original_file = input("원본 txt 파일 경로: ").strip('"')
    base_name = os.path.splitext(os.path.basename(original_file))[0]
    split_dir = f"./{base_name}(분할 파일 번역전)"
    translated_dir = f"./{base_name}(분할 파일 번역후)"
    final_output = f"./{base_name}(번역완료).txt"

    # 분할 파일 체크 및 생성
    if os.path.exists(split_dir) and os.path.isdir(split_dir):
        split_files = sorted([f for f in os.listdir(split_dir) if f.startswith('chunk_')])
        total_chunks = len(split_files)
        print(f"📁 기존 분할 파일 {total_chunks}개를 사용합니다.")
    else:
        print("\n📁 원본 파일 분할 중...")
        total_chunks = split_text_by_lines(original_file, split_dir)
        print(f"✅ {total_chunks}개 파일로 분할 완료!")

    # 번역된 파일 체크
    os.makedirs(translated_dir, exist_ok=True)
    processed_indices = get_processed_indices(translated_dir)
    print(f"🔍 {len(processed_indices)}개 파일 번역 완료. 남은 청크: {total_chunks - len(processed_indices)}개")

    # 웹드라이버 초기화
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://papago.naver.com/?sk=ja&tk=ko&hn=0")
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
                translated_text = translate_text(driver, text)
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
                sys.exit("번역 실패로 인해 프로그램 종료")  # 추가된 종료 코드

        except Exception as e:
            print(f"[{idx}/{total_chunks}] ❌ 치명적 오류: {str(e)}")
            os.system('taskkill /f /im cmd.exe')
            sys.exit("번역 실패로 인해 프로그램 종료")

    driver.quit()

    print("\n📂 번역 파일 병합 중...")
    merge_translated_files(translated_dir, final_output)
    print(f"🎉 최종 파일 저장 완료: {final_output}")

if __name__ == "__main__":
    main_process()