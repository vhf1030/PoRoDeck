import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import time

from util.common import setup_logging

BASE_URL = "https://pokemondb.net"

def get_generation_pokemon_data(generations=[1], logger=None):
    """세대별 포켓몬 데이터 수집"""
    if logger:
        logger.info(f"세대별 포켓몬 데이터 수집 시작: {generations}세대")
    
    pokemon_data = []
    
    for gen in generations:
        if logger:
            logger.debug(f"{gen}세대 포켓몬 정보 수집 중...")
        
        try:
            url = f"{BASE_URL}/pokedex/stats/gen{gen}"
            res = requests.get(url)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, "html.parser")
            table_rows = soup.select("table tbody tr")
            
            gen_count = 0
            for row in table_rows:
                try:
                    cells = row.select("td")
                    if len(cells) < 3:
                        continue
                    
                    # 번호 (첫 번째 셀)
                    dex_num = cells[0].text.strip().zfill(3)
                    
                    # 이름과 링크 (두 번째 셀)
                    name_link = cells[1].select_one("a[href*='/pokedex/']")
                    if not name_link:
                        continue
                    
                    name = name_link.text.strip()
                    link = BASE_URL + name_link["href"]
                    
                    # 타입 (세 번째 셀)
                    type_links = cells[2].select("a")
                    types = [t.text.strip() for t in type_links]
                    
                    pokemon_data.append({
                        "id": dex_num,
                        "name_en": name,
                        "link": link,
                        "type1": types[0] if types else None,
                        "type2": types[1] if len(types) > 1 else None,
                        "generation": gen
                    })
                    gen_count += 1
                    
                except Exception as e:
                    if logger:
                        logger.debug(f"테이블 행 파싱 오류: {str(e)}")
                    continue
            
            if logger:
                logger.info(f"{gen}세대: {gen_count}종 포켓몬 수집 완료")
                
        except Exception as e:
            if logger:
                logger.error(f"{gen}세대 정보 수집 실패: {str(e)}")
            continue
            
        time.sleep(0.5)
    
    if logger:
        logger.info(f"세대별 데이터 수집 완료: 총 {len(pokemon_data)}종")
    
    return pokemon_data



def get_pokemon_details(link, logger=None):
    """포켓몬 상세 정보 + 한글 이름 수집"""
    try:
        res = requests.get(link)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        data = {"form": "normal"}  # 기본적으로 normal 폼으로 설정

        # 기본 정보 (vitals-table에서)
        vitals_table = soup.select_one("table.vitals-table")
        if vitals_table:
            rows = vitals_table.select("tr")
            for row in rows:
                try:
                    th = row.select_one("th")
                    td = row.select_one("td")
                    if th and td:
                        th_text = th.text.strip()
                        td_text = td.text.strip()
                        
                        if "Species" in th_text:
                            # Pokémon을 Pokemon으로 변경
                            data["species"] = td_text.replace("Pokémon", "Pokemon")
                        elif "Height" in th_text:
                            height_text = td_text.split("m")[0].strip()
                            data["height_m"] = float(height_text)
                        elif "Weight" in th_text:
                            weight_text = td_text.split("kg")[0].strip()
                            data["weight_kg"] = float(weight_text)
                except (ValueError, AttributeError, IndexError) as e:
                    if logger:
                        logger.debug(f"기본 정보 파싱 오류 ({th_text if 'th_text' in locals() else 'unknown'}): {str(e)}")
                    continue

        # Training 섹션에서 Base Exp와 Catch rate 수집
        for h2 in soup.select("h2"):
            if "Training" in h2.text:
                training_table = h2.find_next("table")
                if training_table:
                    rows = training_table.select("tr")
                    for row in rows:
                        try:
                            th = row.select_one("th")
                            td = row.select_one("td")
                            if th and td:
                                th_text = th.text.strip()
                                td_text = td.text.strip()
                                
                                if "Base Exp" in th_text:
                                    data["base_exp"] = int(td_text.replace(",", ""))
                                if "Catch rate" in th_text:
                                    # "45 (5.9% with PokéBall, full HP)" → "45"
                                    catch_rate_text = td_text.split()[0]
                                    data["catch_rate"] = int(catch_rate_text)
                        except (ValueError, AttributeError, IndexError) as e:
                            if logger:
                                logger.debug(f"Training 정보 파싱 오류 ({th_text if 'th_text' in locals() else 'unknown'}): {str(e)}")
                            continue
                break

        # Base stats 수집 
        # "Base stats" 헤딩 찾기
        for h2 in soup.select("h2"):
            if "Base stats" in h2.text:
                stats_table = h2.find_next("table")
                if stats_table:
                    stats_rows = stats_table.select("tr")
                    for row in stats_rows:
                        try:
                            th = row.select_one("th")
                            tds = row.select("td")
                            
                            if th and tds:
                                stat_name = th.text.strip()
                                
                                # Total은 다른 구조를 가질 수 있음
                                if stat_name == "Total":
                                    # Total은 .cell-total 클래스를 찾거나 특별한 처리
                                    total_cell = row.select_one("td.cell-total")
                                    if total_cell:
                                        data["Tot"] = int(total_cell.text.strip())
                                    else:
                                        # 일반적인 경우 첫 번째 td 사용
                                        first_td = tds[0]
                                        stat_text = first_td.text.strip()
                                        data["Tot"] = int(stat_text)
                                else:
                                    # 일반 스탯들은 첫 번째 td에서 숫자만 추출
                                    first_td = tds[0]
                                    stat_text = first_td.text.strip()
                                    stat_value = int(stat_text)
                                    
                                    if stat_name == "HP":
                                        data["HP"] = stat_value
                                    elif stat_name == "Attack":
                                        data["Atk"] = stat_value
                                    elif stat_name == "Defense":
                                        data["Def"] = stat_value
                                    elif stat_name == "Sp. Atk":
                                        data["SpAtk"] = stat_value
                                    elif stat_name == "Sp. Def":
                                        data["SpDef"] = stat_value
                                    elif stat_name == "Speed":
                                        data["Spd"] = stat_value
                        except (ValueError, AttributeError, IndexError) as e:
                            if logger:
                                logger.debug(f"스탯 파싱 오류 ({stat_name if 'stat_name' in locals() else 'unknown'}): {str(e)}")
                            continue
                break

        # Pokédex entries 수집
        entries = []
        for h2 in soup.select("h2"):
            if "Pokédex entries" in h2.text:
                entries_table = h2.find_next("table")
                if entries_table:
                    for row in entries_table.select("tr"):
                        try:
                            th = row.select_one("th")
                            td = row.select_one("td")
                            if th and td:
                                # th 안에 여러 span이 있는 경우 &로 연결
                                spans = th.select("span")
                                if spans:
                                    game_names = [span.text.strip() for span in spans]
                                    game_name = "&".join(game_names)
                                else:
                                    game_name = th.text.strip()
                                
                                description = td.text.strip().replace("POKéMON", "POKEMON").replace("Pokémon", "POKEMON")
                                entries.append(f"({game_name}){description}")
                        except Exception as e:
                            if logger:
                                logger.debug(f"포켓덱스 엔트리 파싱 오류: {str(e)}")
                            continue
                break
        
        data["descriptions"] = ", ".join(entries) if entries else None

        # 진화 조건 수집
        data["evo_from_id"] = None
        data["evo_from_cond"] = None
        
        # Evolution chart 섹션 찾기
        for h2 in soup.select("h2"):
            if "Evolution chart" in h2.text:
                evo_container = h2.find_next("div", class_="infocard-list-evo")
                if evo_container:
                    # 진화 체인의 모든 요소 (카드 + 화살표) 순서대로 수집
                    evo_elements = evo_container.find_all(["div", "span"], class_=["infocard", "infocard-arrow"])
                    
                    current_pokemon_id = None
                    # 현재 페이지의 포켓몬 ID 추출 (URL에서)
                    try:
                        # link에서 포켓몬 이름 추출
                        pokemon_name = link.split("/")[-1]
                        
                        # 진화 체인에서 현재 포켓몬 찾기
                        for i, element in enumerate(evo_elements):
                            if "infocard" in element.get("class", []) and "infocard-arrow" not in element.get("class", []):
                                # 포켓몬 카드인 경우
                                name_link = element.select_one("a.ent-name")
                                if name_link:
                                    card_pokemon_name = name_link["href"].split("/")[-1]
                                    
                                    # 현재 포켓몬과 매칭되는 카드 찾기
                                    if card_pokemon_name == pokemon_name:
                                        # 이 포켓몬 바로 앞의 진화 조건과 진화 전 포켓몬 찾기
                                        if i >= 2:  # 최소 [포켓몬] -> [화살표] -> [현재포켓몬] 구조
                                            # 바로 앞 화살표에서 진화 조건 추출
                                            prev_arrow = evo_elements[i-1]
                                            if "infocard-arrow" in prev_arrow.get("class", []):
                                                condition_small = prev_arrow.select_one("small")
                                                if condition_small:
                                                    condition_text = condition_small.text.strip()
                                                    # 괄호 제거: "(Level 16)" -> "Level 16"
                                                    data["evo_from_cond"] = condition_text.strip("()")
                                            
                                            # 바로 앞 포켓몬에서 ID 추출
                                            prev_pokemon = evo_elements[i-2]
                                            if "infocard" in prev_pokemon.get("class", []) and "infocard-arrow" not in prev_pokemon.get("class", []):
                                                prev_id_small = prev_pokemon.select_one("small")
                                                if prev_id_small:
                                                    prev_id_text = prev_id_small.text.strip()
                                                    # "#0004" -> "0004"
                                                    data["evo_from_id"] = prev_id_text.replace("#", "")
                                        break
                    except Exception as e:
                        if logger:
                            logger.debug(f"진화 조건 파싱 오류: {str(e)}")
                break

        # 한글 이름
        data["name_kr"] = None
        # "Other languages" 섹션 찾기
        for h2 in soup.select("h2"):
            if "Other languages" in h2.text:
                table = h2.find_next("table")
                if table:
                    for row in table.select("tr"):
                        # th와 td 구조 확인: <th>Korean</th><td>이상해씨</td>
                        th = row.select_one("th")
                        td = row.select_one("td")
                        
                        if th and td:
                            lang_name = th.text.strip().lower()
                            if "korean" in lang_name:
                                korean_name = td.text.strip()
                                # 괄호 안의 내용 제거 (예: "이상해씨 (isanghaessi)" → "이상해씨")
                                data["name_kr"] = korean_name.split("(")[0].strip()
                                break
                if data["name_kr"]:
                    break

        return data
        
    except Exception as e:
        if logger:
            logger.warning(f"상세 정보 수집 실패 ({link}): {str(e)}")
        return {}


def collect_all_pokemon_data(generations=[1]):
    # 로깅 설정
    logger = setup_logging()
    logger.info("=== 포켓몬 데이터 수집 시작 ===")
    
    try:
        # 세대별 포켓몬 데이터 수집
        logger.info("세대별 포켓몬 데이터 수집")
        pokemon_list = get_generation_pokemon_data(generations=generations, logger=logger)
        
        if not pokemon_list:
            logger.error("포켓몬 데이터를 가져올 수 없습니다. 프로그램을 종료합니다.")
            return None

        # 상세 정보 수집
        logger.info(f"{len(pokemon_list)}종 포켓몬 상세 정보 수집")
        final_data = []
        success_count = 0
        error_count = 0
        
        for i, p in enumerate(tqdm(pokemon_list, desc="포켓몬 상세 정보 수집")):
            try:
                detail = get_pokemon_details(p["link"], logger=logger)

                final_data.append({
                    "id": p["id"],
                    "generation": p["generation"],
                    "name_en": p["name_en"],
                    "name_kr": detail.get("name_kr"),
                    "type1": p["type1"],
                    "type2": p["type2"],
                    "species": detail.get("species"),
                    "height_m": detail.get("height_m"),
                    "weight_kg": detail.get("weight_kg"),
                    "base_exp": detail.get("base_exp"),
                    "catch_rate": detail.get("catch_rate"),
                    "form": detail.get("form", "normal"),
                    "evo_from_id": detail.get("evo_from_id"),
                    "evo_from_cond": detail.get("evo_from_cond"),
                    "HP": detail.get("HP"),
                    "Atk": detail.get("Atk"),
                    "Def": detail.get("Def"),
                    "SpAtk": detail.get("SpAtk"),
                    "SpDef": detail.get("SpDef"),
                    "Spd": detail.get("Spd"),
                    "Tot": detail.get("Tot"),
                    "descriptions": detail.get("descriptions"),
                    "link": p["link"],
                })

                success_count += 1
                
                # 진행 상황 로깅 (매 50종마다)
                if (i + 1) % 50 == 1:
                    logger.info(f"진행 상황: {i + 1}/{len(pokemon_list)} 완료 ({((i + 1)/len(pokemon_list)*100):.1f}%)")
                    logger.info(f"포켓몬 정보: \n{p} \n{detail}")
                time.sleep(0.2)
                print(p["id"], p["name_en"], detail.get("name_kr"))
                
            except Exception as e:
                error_count += 1
                logger.error(f"포켓몬 정보 수집 실패 ({p['id']} {p['name_en']}): {str(e)}")
                continue

        logger.info(f"상세 정보 수집 완료: 성공 {success_count}종, 실패 {error_count}종")
        logger.info("=== 포켓몬 데이터 수집 완료 ===")
        
        return pd.DataFrame(final_data)
        
    except Exception as e:
        logger.error(f"데이터 수집 중 심각한 오류 발생: {str(e)}")
        return None


if __name__ == "__main__":
    # 1세대 포켓몬 데이터 수집
    df = collect_all_pokemon_data(generations=[1,2,3,4,5,6,7,8,9])
    # df = collect_all_pokemon_data(generations=[1])
    
    if df is not None and len(df) > 0:
        import os
        os.makedirs("data/raw", exist_ok=True)
        
        output_file = "data/raw/pokemon_basic.tsv"
        df.to_csv(output_file, index=False, sep="\t")
        print(f"수집 완료: 총 {len(df)} 포켓몬 데이터 {output_file}에 저장됨")
    else:
        print("데이터 수집 실패")
