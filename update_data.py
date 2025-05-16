import requests
import json
import time
import os
from datetime import datetime, UTC, timedelta

USER_AGENT = "EVEDaily (contact: TeamFT2005@gmail.com)"
ZKILLBOARD_API_BASE_URL = "https://zkillboard.com/api/"
ESI_API_BASE_URL = "https://esi.evetech.net/latest/"
HUGO_DATA_FILE = "data/destroyed_freighters.json"
TARGET_GROUP_IDS = [513, 902] # Фрейтер, джамп-фрейтер
SECONDS_TO_CHECK_ZKB = 7 * 24 * 60 * 60  
MAX_KILLS_TO_STORE = 200
ZKB_REQUEST_DELAY = 0.5
ESI_REQUEST_DELAY_GENERAL = 0.2
ESI_REQUEST_DELAY_HEAVY = 0.5

DAYS_TO_KEEP_KILLS_IN_FILE = 7

_TYPE_ID_TO_NAME_CACHE = {}
_SYSTEM_ID_TO_INFO_CACHE = {}
_CORP_ID_TO_NAME_CACHE = {}
_ALLIANCE_ID_TO_NAME_CACHE = {}
_CHAR_ID_TO_NAME_CACHE = {}

def make_request(url, params=None, headers=None, method='GET', data=None):
    default_headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
    if headers:
        default_headers.update(headers)

    retries = 0
    max_retries = 3 

    while retries <= max_retries:
        try:
            if method.upper() == 'POST':
                response = requests.post(url, headers=default_headers, json=data, timeout=15)
            else:
                response = requests.get(url, params=params, headers=default_headers, timeout=15)
            if response.status_code == 420:
                if retries == max_retries:
                    print(f"[API] Превышен лимит запросов к ESI (ошибка 420) после {max_retries} попыток. Пропуск этого запроса.")
                    return None # 
                wait_time_str = response.headers.get('X-ESI-Error-Limit-Reset', '60')
                try:
                    wait_time = int(wait_time_str) + 5
                except ValueError:
                    wait_time = 65 
                print(f"[API] Превышен лимит запросов к ESI (ошибка 420). Попытка {retries + 1}/{max_retries}. Ожидание {wait_time} секунд...")
                time.sleep(wait_time)
                retries += 1
                continue
            if response.status_code == 502:
                if retries == max_retries:
                    print(f"[API] Плохой путь (ошибка 502) после {max_retries} попыток. Пропуск этого запроса.")
                    return None 
                wait_time = 10
                print(f"[API] Плохой путь (ошибка 502). Попытка {retries + 1}/{max_retries}. Ожидание {wait_time} секунд...")
                time.sleep(wait_time)
                retries += 1
                continue 

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[API] Ошибка запроса к {url}: {e}")
            return None 
        except json.JSONDecodeError as e:
            print(f"[API] Ошибка декодирования JSON ответа от {url}: {e}. Ответ: {response.text[:200]}")
            return None 
    return None 


def get_type_name_esi(type_id):
    if not type_id: return "Unknown Ship"
    if type_id in _TYPE_ID_TO_NAME_CACHE:
        return _TYPE_ID_TO_NAME_CACHE[type_id]

    data = make_request(f"{ESI_API_BASE_URL}universe/types/{type_id}/?language=en-us")
    time.sleep(ESI_REQUEST_DELAY_GENERAL)
    if data and 'name' in data:
        _TYPE_ID_TO_NAME_CACHE[type_id] = data['name']
        return data['name']
    return "Unknown Ship"

def get_system_and_region_name_esi(system_id):
    if not system_id: return {"system_name": "Unknown System", "region_name": "Unknown Region"}
    if system_id in _SYSTEM_ID_TO_INFO_CACHE:
        return _SYSTEM_ID_TO_INFO_CACHE[system_id]

    system_info = make_request(f"{ESI_API_BASE_URL}universe/systems/{system_id}/?language=en-us")
    time.sleep(ESI_REQUEST_DELAY_GENERAL)
    if not system_info or 'name' not in system_info or 'constellation_id' not in system_info:
        return {"system_name": "Unknown System", "region_name": "Unknown Region"}

    system_name = system_info['name']
    constellation_id = system_info['constellation_id']

    constellation_info = make_request(f"{ESI_API_BASE_URL}universe/constellations/{constellation_id}/?language=en-us")
    time.sleep(ESI_REQUEST_DELAY_GENERAL)
    if not constellation_info or 'region_id' not in constellation_info:
        _SYSTEM_ID_TO_INFO_CACHE[system_id] = {"system_name": system_name, "region_name": "Unknown Region"}
        return _SYSTEM_ID_TO_INFO_CACHE[system_id]

    region_id = constellation_info['region_id']
    region_info = make_request(f"{ESI_API_BASE_URL}universe/regions/{region_id}/?language=en-us")
    time.sleep(ESI_REQUEST_DELAY_GENERAL)
    region_name = region_info['name'] if region_info and 'name' in region_info else "Unknown Region"

    _SYSTEM_ID_TO_INFO_CACHE[system_id] = {"system_name": system_name, "region_name": region_name}
    return _SYSTEM_ID_TO_INFO_CACHE[system_id]

def get_character_name_esi(character_id):
    if not character_id: return "Unknown Pilot"
    if character_id in _CHAR_ID_TO_NAME_CACHE:
        return _CHAR_ID_TO_NAME_CACHE[character_id]
    data = make_request(f"{ESI_API_BASE_URL}characters/{character_id}/")
    time.sleep(ESI_REQUEST_DELAY_GENERAL)
    if data and 'name' in data:
        _CHAR_ID_TO_NAME_CACHE[character_id] = data['name']
        return data['name']
    return "Unknown Pilot"

def get_corporation_name_esi(corporation_id):
    if not corporation_id: return "Unknown Corporation"
    if corporation_id in _CORP_ID_TO_NAME_CACHE:
        return _CORP_ID_TO_NAME_CACHE[corporation_id]
    data = make_request(f"{ESI_API_BASE_URL}corporations/{corporation_id}/")
    time.sleep(ESI_REQUEST_DELAY_GENERAL)
    if data and 'name' in data:
        _CORP_ID_TO_NAME_CACHE[corporation_id] = data['name']
        return data['name']
    return "Unknown Corporation"

def get_alliance_name_esi(alliance_id):
    if not alliance_id: return None
    if alliance_id in _ALLIANCE_ID_TO_NAME_CACHE:
        return _ALLIANCE_ID_TO_NAME_CACHE[alliance_id]
    data = make_request(f"{ESI_API_BASE_URL}alliances/{alliance_id}/")
    time.sleep(ESI_REQUEST_DELAY_GENERAL)
    if data and 'name' in data:
        _ALLIANCE_ID_TO_NAME_CACHE[alliance_id] = data['name']
        return data['name']
    return "N/A" 
def get_recent_freighter_kills_zkb():
    all_kills_from_zkb = []
    for group_id in TARGET_GROUP_IDS:
        url = f"{ZKILLBOARD_API_BASE_URL}groupID/{group_id}/pastSeconds/{SECONDS_TO_CHECK_ZKB}/"
        print(f"Запрос к zKillboard: {url}")
        kills_response = make_request(url)
        if kills_response:
            valid_kills = [k for k in kills_response if k is not None and isinstance(k, dict)] 
            if valid_kills:
                print(f"Получено {len(valid_kills)} валидных киллов для группы {group_id} за последние {SECONDS_TO_CHECK_ZKB} секунд.")
                all_kills_from_zkb.extend(valid_kills)
            else:
                print(f"Не получено валидных киллов для группы {group_id} (ответ мог быть [null] или пустым, или не содержать словарей).")
        else:
            print(f"Не получено ответа или произошла ошибка запроса для группы {group_id}.")
        time.sleep(ZKB_REQUEST_DELAY)
    print(f"Всего получено {len(all_kills_from_zkb)} потенциальных киллмейлов от zKillboard.")
    return all_kills_from_zkb

def process_killmails():
    print(f"[{datetime.now(UTC).isoformat()}] Начало обновления данных об уничтоженных фрейтерах...")

    hugo_data_dir = os.path.dirname(HUGO_DATA_FILE)
    if hugo_data_dir and not os.path.exists(hugo_data_dir):
        os.makedirs(hugo_data_dir)

    loaded_killmails_from_file = []
    if os.path.exists(HUGO_DATA_FILE):
        try:
            with open(HUGO_DATA_FILE, 'r', encoding='utf-8') as f:
                loaded_killmails_from_file = json.load(f)
            print(f"Загружено {len(loaded_killmails_from_file)} существующих киллмейлов из файла.")
        except json.JSONDecodeError:
            print(f"Ошибка чтения JSON из {HUGO_DATA_FILE}. Файл будет считаться пустым.")
            loaded_killmails_from_file = []
        except Exception as e:
            print(f"Не удалось загрузить существующие киллмейлы из {HUGO_DATA_FILE}: {e}")
            loaded_killmails_from_file = []

    current_killmails = []
    existing_kill_ids = set()
    removed_due_to_age = 0
    now_utc = datetime.now(UTC)
    cutoff_date = now_utc - timedelta(days=DAYS_TO_KEEP_KILLS_IN_FILE)

    for km in loaded_killmails_from_file:
        kill_time_str = km.get('kill_time')
        km_id = km.get('killmail_id', 'N/A')
        if not kill_time_str:
            print(f"Киллмейл {km_id} не имеет 'kill_time', Будет удален")
            removed_due_to_age += 1
            if 'killmail_id' in km: 
                existing_kill_ids.add(km['killmail_id'])
            continue
        try:
            kill_datetime = datetime.fromisoformat(kill_time_str.replace('Z', '+00:00'))
            if kill_datetime.tzinfo is None:
                kill_datetime = kill_datetime.replace(tzinfo=UTC)
            if kill_datetime >= cutoff_date:
                current_killmails.append(km)
                if 'killmail_id' in km: 
                    existing_kill_ids.add(km['killmail_id'])
            else:
                print(f"Удаление старого киллмейла (ID: {km_id}, время: {kill_time_str}) из списка")
                removed_due_to_age += 1
        except ValueError:
            print(f"Некорректный формат 'kill_time' ({kill_time_str}) для киллмейла {km_id}. Будет удален")
            removed_due_to_age += 1
    if removed_due_to_age > 0:
        print(f"Удалено {removed_due_to_age} киллмейлов по истечения срока хранения ({DAYS_TO_KEEP_KILLS_IN_FILE} дней/некорректных данных).")
    print(f"Осталось {len(current_killmails)} киллмейлов после фильтрации по дате. Уникальных ID: {len(existing_kill_ids)}")

    raw_zkb_kills = get_recent_freighter_kills_zkb()
    if not raw_zkb_kills:
        print("Не удалось получить новые данные от zKillboard. Сохранение только отфильтрованных старых данных (если есть).")
        # Если новых нет, все равно сохраним отфильтрованные старые (если они изменились)
        if loaded_killmails_from_file != current_killmails or removed_due_to_age > 0 : # Сохраняем если список изменился
            try:
                # Сортируем перед сохранением, чтобы самые свежие были вверху
                current_killmails.sort(key=lambda x: x.get('kill_time', ''), reverse=True)
                final_killmails_to_save = current_killmails[:MAX_KILLS_TO_STORE]

                with open(HUGO_DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(final_killmails_to_save, f, indent=2, ensure_ascii=False)
                print(f"Данные ({len(final_killmails_to_save)} киллмейлов) успешно сохранены в {HUGO_DATA_FILE} после фильтрации старых.")
            except IOError as e:
                print(f"Ошибка записи в файл {HUGO_DATA_FILE}: {e}")
        else:
            print("Список существующих киллмейлов не изменился, новых не получено. Запись в файл не требуется.")
        print(f"[{datetime.now(UTC).isoformat()}] Обновление данных завершено (без новых киллов).")
        return

    newly_processed_killmails = []
    processed_in_this_run_ids = set()
    raw_zkb_kills.sort(key=lambda k: k.get('killmail_id', 0), reverse=True)


    for zkb_kill_info in raw_zkb_kills:
        if not zkb_kill_info or not isinstance(zkb_kill_info, dict): 
            print(f"Пропуск пустой или некорректной записи из zKillboard: {zkb_kill_info}")
            continue

        killmail_id = zkb_kill_info.get('killmail_id')
        killmail_hash = zkb_kill_info.get('zkb', {}).get('hash')

        if not killmail_id or not killmail_hash:
            print(f"Запись из zKillboard без ID или hash: {zkb_kill_info}")
            continue

        if killmail_id in existing_kill_ids or killmail_id in processed_in_this_run_ids:
            print(f"Килл {killmail_id} уже существует или обработан в этом запуске, пропускаем.") 
            continue

        print(f"Обработка нового килла: ID {killmail_id}, Hash {killmail_hash}")

        esi_kill_detail = make_request(f"{ESI_API_BASE_URL}killmails/{killmail_id}/{killmail_hash}/")
        time.sleep(ESI_REQUEST_DELAY_HEAVY)

        if not esi_kill_detail:
            print(f"Не удалось получить детали из ESI для килла {killmail_id}. Пропуск.")
            continue

        victim_data = esi_kill_detail.get('victim', {})
        victim_ship_type_id = victim_data.get('ship_type_id')

        if not victim_ship_type_id:
            print(f"Килл {killmail_id}: отсутствует ship_type_id у жертвы. Пропуск.")
            continue

        victim_ship_name = _TYPE_ID_TO_NAME_CACHE.get(victim_ship_type_id)
        victim_ship_group_id = None

        if victim_ship_name: 
            for km_data in current_killmails + newly_processed_killmails:
                if km_data.get('ship_type_id') == victim_ship_type_id and 'victim_ship_group_id_for_filter' in km_data: 
                    victim_ship_group_id = km_data['victim_ship_group_id_for_filter']
                    break
        
        if victim_ship_group_id is None: 
            try: 
                victim_ship_details_from_esi = make_request(f"{ESI_API_BASE_URL}universe/types/{victim_ship_type_id}/?language=en-us")
            except requests.exceptions.RequestException as e:
                print(f"[API] Ошибка запроса к ESI для получения деталей типа корабля атакующего {victim_ship_type_id}: {e}")
                victim_ship_details_from_esi = None
            time.sleep(ESI_REQUEST_DELAY_GENERAL)

            if not victim_ship_details_from_esi or \
               'group_id' not in victim_ship_details_from_esi or \
               'name' not in victim_ship_details_from_esi:
                print(f"[DEBUG] Килл {killmail_id}, ID корабля {victim_ship_type_id}: ПРОПУСК - неполные детали типа корабля от ESI ({victim_ship_details_from_esi}).")
                continue
            
            victim_ship_group_id = victim_ship_details_from_esi['group_id']
            victim_ship_name = victim_ship_details_from_esi['name']
            _TYPE_ID_TO_NAME_CACHE[victim_ship_type_id] = victim_ship_name 
        else: 
            if not victim_ship_name: 
                victim_ship_name = get_type_name_esi(victim_ship_type_id)


        print(f"[DEBUG] Килл {killmail_id}, ID корабля {victim_ship_type_id}, Имя: '{victim_ship_name}', GroupID: {victim_ship_group_id}. Целевые группы: {TARGET_GROUP_IDS}")

        if victim_ship_group_id not in TARGET_GROUP_IDS:
            print(f"[DEBUG] Килл {killmail_id}, ID корабля {victim_ship_type_id} (Имя: '{victim_ship_name}', Группа: {victim_ship_group_id}): "
                  f"ПРОПУСК - group_id ({victim_ship_group_id}) не в целевом списке {TARGET_GROUP_IDS}.")
            continue
        
        print(f"Килл {killmail_id} подтвержден как потеря фрейтера/джамп-фрейтера ({victim_ship_name}).")

        system_info = get_system_and_region_name_esi(esi_kill_detail.get('solar_system_id'))

        victim_char_id = victim_data.get('character_id')
        victim_corp_id = victim_data.get('corporation_id')
        victim_alliance_id = victim_data.get('alliance_id')

        final_killmail_data = {
            "killmail_id": killmail_id,
            "killmail_hash": killmail_hash,
            "kill_time": esi_kill_detail.get('killmail_time'), 
            "ship_type_id": victim_ship_type_id,
            "ship_type_name": victim_ship_name,
            "victim_ship_group_id_for_filter": victim_ship_group_id, 
            "solar_system_id": esi_kill_detail.get('solar_system_id'),
            "solar_system_name": system_info.get('system_name'),
            "region_name": system_info.get('region_name'),
            "victim": {
                "character_id": victim_char_id,
                "character_name": get_character_name_esi(victim_char_id) if victim_char_id else "NPC/Structure",
                "corporation_id": victim_corp_id,
                "corporation_name": get_corporation_name_esi(victim_corp_id) if victim_corp_id else "N/A",
                "alliance_id": victim_alliance_id,
                "alliance_name": get_alliance_name_esi(victim_alliance_id) if victim_alliance_id else None,
            },
            "zkb_url": f"https://zkillboard.com/kill/{killmail_id}/",
            "total_value": zkb_kill_info.get('zkb', {}).get('totalValue', 0.0)
        }

        attackers = esi_kill_detail.get('attackers', [])
        final_attacker_info = None
        if attackers:
            final_blow_attackers = [att for att in attackers if att.get('final_blow')]
            chosen_attacker = None
            if final_blow_attackers:
                chosen_attacker = sorted(final_blow_attackers, key=lambda x: x.get('damage_done', 0), reverse=True)[0]
            elif attackers:
                chosen_attacker = sorted(attackers, key=lambda x: x.get('damage_done', 0), reverse=True)[0]

            if chosen_attacker:
                attacker_char_id = chosen_attacker.get('character_id')
                attacker_corp_id = chosen_attacker.get('corporation_id')
                attacker_alliance_id = chosen_attacker.get('alliance_id')
                attacker_ship_id = chosen_attacker.get('ship_type_id')
                final_attacker_info = {
                    "character_name": get_character_name_esi(attacker_char_id) if attacker_char_id else "NPC/Structure",
                    "corporation_name": get_corporation_name_esi(attacker_corp_id) if attacker_corp_id else "N/A",
                    "alliance_name": get_alliance_name_esi(attacker_alliance_id) if attacker_alliance_id else None,
                    "ship_type_name": get_type_name_esi(attacker_ship_id) if attacker_ship_id else "Unknown Ship"
                }

        final_killmail_data["final_attacker"] = final_attacker_info

        if 'victim_ship_group_id_for_filter' in final_killmail_data:
            del final_killmail_data['victim_ship_group_id_for_filter']

        newly_processed_killmails.append(final_killmail_data)
        processed_in_this_run_ids.add(killmail_id)

        print(f"Килл {killmail_id} успешно обработан и добавлен в список для сохранения.")

    if newly_processed_killmails:
        print(f"Добавлено {len(newly_processed_killmails)} новых киллмейлов.")
        combined_killmails = newly_processed_killmails + current_killmails 
        combined_killmails.sort(key=lambda x: x.get('kill_time', '0'), reverse=True)
        final_killmails_to_save = combined_killmails[:MAX_KILLS_TO_STORE]
        try:
            with open(HUGO_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(final_killmails_to_save, f, indent=2, ensure_ascii=False)
            print(f"Данные ({len(final_killmails_to_save)} киллмейлов) успешно сохранены в {HUGO_DATA_FILE}")
        except IOError as e:
            print(f"Ошибка записи в файл {HUGO_DATA_FILE}: {e}")
    elif removed_due_to_age > 0 : 
        print("Новых киллмейлов для добавления не найдено, но были удалены старые.")
        current_killmails.sort(key=lambda x: x.get('kill_time', '0'), reverse=True) 
        final_killmails_to_save = current_killmails[:MAX_KILLS_TO_STORE]
        try:
            with open(HUGO_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(final_killmails_to_save, f, indent=2, ensure_ascii=False)
            print(f"Обновленные данные ({len(final_killmails_to_save)} киллмейлов) успешно сохранены в {HUGO_DATA_FILE} после удаления старых.")
        except IOError as e:
            print(f"Ошибка записи в файл {HUGO_DATA_FILE}: {e}")
    else:
        print("Новых киллмейлов для добавления не найдено в этом запуске, старые не удалялись. Файл не изменен.")

    print(f"[{datetime.now(UTC).isoformat()}] Обновление данных завершено.")

if __name__ == "__main__":
    process_killmails()
    # import schedule
    # print("Скрипт запущен в режиме периодического обновления.")
    # process_killmails()
    # schedule.every(60).minutes.do(process_killmails) 
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)