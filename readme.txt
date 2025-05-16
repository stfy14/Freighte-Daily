##Каждый флот имеет класс, к которому он относиться. Нужные нам относяться к группам [513, 902]##

https://zkillboard.com/api/groupID/{GROUP_ID}/pastSeconds/{SECONDS}/
Первым делом мы обращяемся к эндпоинту pastSeconds c groupsID, который отдает нам список киллмейлов УЧАСТНИКОВ с этой группой. 
То есть любой флот, который как то учавствовал в сражении с фрейтером и был уничтожен, отдается апишкой 
    {
        "killmail_id": 127077318,
        "zkb": {
        "locationID": 40016911,
        "hash": "69b593a7d2cc2542f8b9f74a41237d774ec84b96", 
        "fittedValue": 1730454200.24,
        "droppedValue": 397368036.46,
        "destroyedValue": 1457853463.74,
        "totalValue": 1855221500.2,
        "points": 69,
        "npc": false,
        "solo": true,
        "awox": false,
        "labels": [
            "cat:6",
            "solo",
            "pvp",
            "loc:nullsec",
            "isk:1b+"
        ]
    }

Эндпоинт не отдает класс флота, так что приходится обращаться к ESI через ID мейла и его хеш для получения 
подробной информации
https://esi.evetech.net/latest/killmails/{KILLMAIL_ID}/{KILLMAIL_HASH}/
{
  "attackers": [
    {
      "alliance_id": 99003581,
      "character_id": 96044825,
      "corporation_id": 98800997,
      "damage_done": 52812,
      "final_blow": true,
      "security_status": 0.8,
      "ship_type_id": 73793,
      "weapon_type_id": 27339
    }
  ],
  "killmail_id": 127077318,
  "killmail_time": "2025-05-14T05:14:29Z",
  "solar_system_id": 30000268,
  "victim": {
    "alliance_id": 1900696668,
    "character_id": 2123236313,
    "corporation_id": 98715582,
    "damage_taken": 52812,
    "items": [
      {
        "flag": 13,
        "item_type_id": 31900,
        "quantity_dropped": 1,
        "singleton": 0
      },
      И так далее... 
    ],
    "position": {
      "x": 77730201469.7448,
      "y": 664187958257.644,
      "z": -74021644650.5523
    },
    "ship_type_id": 22428   <- нужный нам ID
}

Дальше узнаем подробности о флоте по его id. Конкретно нужно узнать к какой группе он относиться для дальнейшего отсеивания 
https://esi.evetech.net/latest/universe/types/{TYPE_ID}/
{
  "capacity": 800,
  "description": "Тяжёлые диверсионные линкоры предназначены для шпионажа и проникновения в тыл врага. Они снабжены гипердвигателем и генератором гиперпорталов и способны создавать особые каналы, проходить через которые могут только диверсионные суда. Это позволяет незаметно внедрять разведывательные и шпионские корабли в пространство противника. Идеальное решение в сфере секретных операций.",
  "dogma_attributes": [
    {
      "attribute_id": 3,
      "value": 0
    },
    И так далее...
  ],
  "dogma_effects": [
    {
      "effect_id": 542,
      "is_default": false
    },
    И так далее...
  ],
  "graphic_id": 3356,
  "group_id": 898,               <- нужный нам ID группы
  "market_group_id": 1076,
  "mass": 150300000,
  "name": "Redeemer",
  "packaged_volume": 50000,
  "portion_size": 1,
  "published": true,
  "radius": 250,
  "type_id": 22428,
  "volume": 470000
}

Дальше идут проверки и в итоговом результате сохраняется только те флоты, которые относяться к группам [513, 902]