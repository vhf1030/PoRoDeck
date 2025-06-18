import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import time

from util.common import setup_logging

BASE_URL = "https://pokemondb.net"
BULBAPEDIA_URL = "https://bulbapedia.bulbagarden.net"

def get_move_id_mapping(logger=None):
    """Bulbapedia에서 기술 ID와 이름 매핑 딕셔너리 생성"""
    if logger:
        logger.info("Bulbapedia에서 기술 ID와 이름 매핑 수집 시작")
    
    move_id_mapping = {}
    
    try:
        url = f"{BULBAPEDIA_URL}/wiki/List_of_moves"
        res = requests.get(url)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # sortable roundy 테이블 찾기
        main_table = soup.find('table', class_=['sortable', 'roundy'])
        if not main_table:
            if logger:
                logger.error("Bulbapedia에서 기술 테이블을 찾을 수 없습니다")
            return move_id_mapping
        
        rows = main_table.find_all('tr')
        if logger:
            logger.info(f"총 {len(rows)-1}개 기술 정보 처리 중...")
        
        for i, row in enumerate(rows[1:], 1):  # 헤더 제외
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                # ID (첫 번째 열)
                move_id = cells[0].get_text().strip()
                
                # 이름 (두 번째 열)
                name_cell = cells[1]
                name_link = name_cell.find('a')
                if name_link:
                    move_name = name_link.get_text().strip()
                    move_id_mapping[move_name.lower()] = move_id
                
            except Exception as e:
                if logger:
                    logger.debug(f"Bulbapedia 행 {i} 파싱 오류: {str(e)}")
                continue
        
        if logger:
            logger.info(f"기술 ID 매핑 완료: {len(move_id_mapping)}개 기술")
        
    except Exception as e:
        if logger:
            logger.error(f"Bulbapedia 기술 매핑 수집 실패: {str(e)}")
    
    return move_id_mapping

def get_generation_moves_data(generations=[1], logger=None):
    """세대별 기술 데이터 수집"""
    if logger:
        logger.info(f"세대별 기술 데이터 수집 시작: {generations}세대")
    
    moves_data = []
    
    for gen in generations:
        if logger:
            logger.debug(f"{gen}세대 기술 정보 수집 중...")
        
        try:
            url = f"{BASE_URL}/move/generation/{gen}"
            res = requests.get(url)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 메인 테이블 찾기
            table = soup.find('table', class_=['data-table', 'sticky-header', 'block-wide'])
            if not table:
                if logger:
                    logger.warning(f"{gen}세대 기술 테이블을 찾을 수 없습니다")
                continue
            
            rows = table.find_all('tr')
            gen_count = 0
            
            for row in rows[1:]:  # 헤더 제외
                try:
                    cells = row.find_all('td')
                    if len(cells) < 7:
                        continue
                    
                    # 이름과 링크 (첫 번째 셀)
                    name_link = cells[0].find('a')
                    if not name_link:
                        continue
                    
                    name = name_link.get_text().strip()
                    link = BASE_URL + name_link.get('href', '')
                    
                    # 타입 (두 번째 셀)
                    type_link = cells[1].find('a')
                    move_type = type_link.get_text().strip() if type_link else cells[1].get_text().strip()
                    
                    # 카테고리 (세 번째 셀) - 물리/특수/상태
                    category = cells[2].get_text().strip()
                    
                    # 위력 (네 번째 셀)
                    power = cells[3].get_text().strip()
                    if power == '—' or power == '-':
                        power = None
                    else:
                        try:
                            power = int(power)
                        except:
                            power = None
                    
                    # 명중률 (다섯 번째 셀)
                    accuracy = cells[4].get_text().strip()
                    if accuracy == '—' or accuracy == '-':
                        accuracy = None
                    elif accuracy == '∞' or 'inf' in accuracy.lower():
                        accuracy = "inf"
                    else:
                        try:
                            accuracy = int(accuracy)
                        except:
                            accuracy = None
                    
                    # PP (여섯 번째 셀)
                    pp = cells[5].get_text().strip()
                    try:
                        pp = int(pp)
                    except:
                        pp = None
                    
                    # 효과 (일곱 번째 셀)
                    effects = cells[6].get_text().strip()
                    
                    moves_data.append({
                        "name_en": name,
                        "link": link,
                        "type": move_type,
                        "category": category,
                        "power": power,
                        "accuracy": accuracy,
                        "pp": pp,
                        "effects": effects,
                        "generation": gen
                    })
                    gen_count += 1
                    
                except Exception as e:
                    if logger:
                        logger.debug(f"기술 행 파싱 오류: {str(e)}")
                    continue
            
            if logger:
                logger.info(f"{gen}세대: {gen_count}개 기술 수집 완료")
                
        except Exception as e:
            if logger:
                logger.error(f"{gen}세대 기술 정보 수집 실패: {str(e)}")
            continue
            
        time.sleep(0.5)
    
    if logger:
        logger.info(f"세대별 기술 데이터 수집 완료: 총 {len(moves_data)}개")
    
    return moves_data

def get_move_details(link, logger=None):
    """기술 상세 정보 수집"""
    try:
        res = requests.get(link)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        data = {}
        
        # 기본 정보 (첫 번째 vitals-table에서)
        vitals_tables = soup.find_all('table', class_='vitals-table')
        
        if vitals_tables:
            # 첫 번째 테이블: Type, Category, Power, Accuracy, PP
            first_table = vitals_tables[0]
            rows = first_table.find_all('tr')
            for row in rows:
                try:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        key = th.get_text().strip()
                        value = td.get_text().strip()
                        
                        if key == "Type":
                            data["type"] = value
                        elif key == "Category":
                            data["category"] = value
                        elif key == "Power":
                            if value == '—' or value == '-':
                                data["power"] = None
                            else:
                                try:
                                    data["power"] = int(value)
                                except:
                                    data["power"] = None
                        elif key == "Accuracy":
                            if value == '—' or value == '-':
                                data["accuracy"] = None
                            elif '∞' in value or 'inf' in value.lower():
                                data["accuracy"] = "inf"
                            else:
                                try:
                                    # "100%" → "100"
                                    clean_value = value.replace('%', '').strip()
                                    data["accuracy"] = int(clean_value)
                                except:
                                    data["accuracy"] = None
                        elif key == "PP":
                            # "25 (max. 40)" → "25"
                            pp_value = value.split()[0].strip()
                            try:
                                data["pp"] = int(pp_value)
                            except:
                                data["pp"] = None
                except Exception as e:
                    if logger:
                        logger.debug(f"기본 정보 파싱 오류: {str(e)}")
                    continue
        
        # 한글 이름 수집 (Other languages 섹션에서)
        data["name_kr"] = None
        h2_tags = soup.find_all('h2')
        for h2 in h2_tags:
            if 'Other languages' in h2.get_text():
                next_table = h2.find_next('table')
                if next_table:
                    rows = next_table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            lang = cells[0].get_text().strip()
                            name = cells[1].get_text().strip()
                            if 'Korean' in lang:
                                data["name_kr"] = name
                                break
                break
        
        # Target 정보 수집 (Move target 섹션에서)
        data["target"] = None
        for h2 in h2_tags:
            if 'Move target' in h2.get_text():
                next_element = h2.find_next_sibling()
                while next_element and next_element.name != 'h2':
                    if next_element.name == 'p':
                        target_text = next_element.get_text().strip()
                        if target_text:
                            data["target"] = target_text
                            break
                    next_element = next_element.find_next_sibling()
                break
        
        # Description 수집 (Game descriptions 섹션의 마지막 세대)
        data["description"] = None
        for h2 in h2_tags:
            if 'Game descriptions' in h2.get_text():
                next_table = h2.find_next('table')
                if next_table:
                    rows = next_table.find_all('tr')
                    if rows:
                        # 마지막 행 (가장 최신 세대)
                        last_row = rows[-1]
                        cells = last_row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            desc = cells[1].get_text().strip()
                            data["description"] = desc
                break
        
        # Learnable 포켓몬 정보 수집 (모든 학습 방법)
        learnable_pokemon_ids = set()
        
        # "Learnt"로 시작하는 모든 섹션 찾기
        for h2 in h2_tags:
            h2_text = h2.get_text().strip()
            if h2_text.startswith('Learnt'):
                infocard_div = h2.find_next('div', class_=['infocard-list', 'infocard-list-pkmn-md'])
                if infocard_div:
                    # infocard 클래스 div들 찾기
                    infocard_divs = infocard_div.find_all('div', class_='infocard')
                    for infocard in infocard_divs:
                        # <small>#0005</small> 형태의 ID 찾기
                        small_tag = infocard.find('small')
                        if small_tag:
                            id_text = small_tag.get_text().split('/')[0].strip()
                            if id_text.startswith('#'):
                                # "#0005" -> "0005" 형태로 변환
                                pokemon_id = id_text[1:]  # # 제거
                                learnable_pokemon_ids.add(pokemon_id)
        
        # learnable_pokemon_ids를 콤마로 구분된 문자열로 변환
        data["learnable"] = ','.join(sorted(learnable_pokemon_ids)) if learnable_pokemon_ids else None
        
        return data
        
    except Exception as e:
        if logger:
            logger.warning(f"기술 상세 정보 수집 실패 ({link}): {str(e)}")
        return {}

def collect_all_moves_data(generations=[1]):
    """모든 기술 데이터 수집"""
    # 로깅 설정
    logger = setup_logging()
    logger.info("=== 기술 데이터 수집 시작 ===")
    
    try:
        # 1. Bulbapedia에서 기술 ID 매핑 수집
        logger.info("1단계: 기술 ID 매핑 수집")
        move_id_mapping = get_move_id_mapping(logger=logger)
        
        if not move_id_mapping:
            logger.warning("기술 ID 매핑을 가져올 수 없습니다. ID 없이 진행합니다.")
        
        # 2. 세대별 기술 데이터 수집
        logger.info("2단계: 세대별 기술 데이터 수집")
        moves_list = get_generation_moves_data(generations=generations, logger=logger)
        
        if not moves_list:
            logger.error("기술 데이터를 가져올 수 없습니다. 프로그램을 종료합니다.")
            return None
        
        # 3. 상세 정보 수집
        logger.info(f"3단계: {len(moves_list)}개 기술 상세 정보 수집")
        final_data = []
        success_count = 0
        error_count = 0
        
        for i, move in enumerate(tqdm(moves_list, desc="기술 상세 정보 수집")):
            try:
                detail = get_move_details(move["link"], logger=logger)
                
                # ID 매핑에서 ID 찾기
                move_id = move_id_mapping.get(move["name_en"].lower())
                
                # power와 pp를 정수형으로 변환
                power = detail.get("power", move["power"])
                if power is not None:
                    power = int(power)
                
                pp = detail.get("pp", move["pp"])
                if pp is not None:
                    pp = int(pp)
                
                final_data.append({
                    "id": move_id,
                    "name_en": move["name_en"],
                    "name_kr": detail.get("name_kr"),
                    "type": detail.get("type", move["type"]),
                    "category": detail.get("category", move["category"]),
                    "power": power,
                    "accuracy": detail.get("accuracy", move["accuracy"]),
                    "pp": pp,
                    "effects": move["effects"],
                    "description": detail.get("description"),
                    "target": detail.get("target"),
                    "learnable": detail.get("learnable"),
                    "generation": move["generation"],
                    "link": move["link"]
                })
                
                success_count += 1
                
                # 진행 상황 로깅 (매 50개마다)
                if (i + 1) % 50 == 1:
                    logger.info(f"진행 상황: {i + 1}/{len(moves_list)} 완료 ({((i + 1)/len(moves_list)*100):.1f}%)")
                    logger.info(f"기술 정보: \n{move} \n{detail}")
                
                time.sleep(0.2)
                print(move_id, move["name_en"], detail.get("name_kr"))
                
            except Exception as e:
                error_count += 1
                logger.error(f"기술 정보 수집 실패 ({move['name_en']}): {str(e)}")
                continue
        
        logger.info(f"상세 정보 수집 완료: 성공 {success_count}개, 실패 {error_count}개")
        logger.info("=== 기술 데이터 수집 완료 ===")
        
        # DataFrame 생성 후 power와 pp를 정수형으로 변환
        df = pd.DataFrame(final_data)
        
        # power 열이 있는 경우 정수형으로 변환 (None은 그대로 유지)
        if 'power' in df.columns:
            df['power'] = df['power'].astype('Int64')  # nullable integer type
        
        # pp 열이 있는 경우 정수형으로 변환 (None은 그대로 유지)
        if 'pp' in df.columns:
            df['pp'] = df['pp'].astype('Int64')  # nullable integer type
        
        return df
        
    except Exception as e:
        logger.error(f"데이터 수집 중 심각한 오류 발생: {str(e)}")
        return None

if __name__ == "__main__":
    # 1세대 기술 데이터 수집
    df = collect_all_moves_data(generations=[1])
    # df = collect_all_moves_data(generations=[1,2,3,4,5,6,7,8,9])
    
    if df is not None and len(df) > 0:
        import os
        os.makedirs("data/raw", exist_ok=True)
        
        output_file = "data/raw/move_basic.tsv"
        df.to_csv(output_file, index=False, sep="\t")
        print(f"수집 완료: 총 {len(df)} 기술 데이터 {output_file}에 저장됨")
    else:
        print("데이터 수집 실패")
