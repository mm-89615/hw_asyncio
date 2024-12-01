import asyncio
import logging
import os

import aiohttp
from dotenv import load_dotenv

from hw_asyncio.database import Session, close_db, init_db
from hw_asyncio.models import Character

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_character_count(http_session):
    async with http_session.get('https://swapi.dev/api/people/') as response:
        json_data = await response.json()
        return json_data.get('count')


async def parse_urls(urls, key, http_session):
    if not urls:
        return ''
    if isinstance(urls, str):
        urls = [urls]
    results = []
    for url in urls:
        async with http_session.get(url) as response:
            json_data = await response.json()
            if json_data.get('detail'):
                continue
            results.append(json_data.get(key, ''))
    return ', '.join(results)


async def get_character(character_id, http_session):
    url = f"https://swapi.dev/api/people/{character_id}"
    async with http_session.get(url) as response:
        json_data = await response.json()
        if json_data.get('detail'):
            return
        return {
            'name': json_data.get('name'),
            'birth_year': json_data.get('birth_year'),
            'eye_color': json_data.get('eye_color'),
            'films': await parse_urls(json_data.get('films'), 'title', http_session),
            'gender': json_data.get('gender'),
            'hair_color': json_data.get('hair_color'),
            'height': json_data.get('height'),
            'homeworld': await parse_urls(json_data.get('homeworld'), 'name', http_session),
            'mass': json_data.get('mass'),
            'skin_color': json_data.get('skin_color'),
            'species': await parse_urls(json_data.get('species'), 'name', http_session),
            'starships': await parse_urls(json_data.get('starships'), 'name', http_session),
            'vehicles': await parse_urls(json_data.get('vehicles'), 'name', http_session),
        }


async def insert_character(characters_list: list[dict]):
    async with Session() as session:
        characters = [Character(**character) for character in characters_list]
        session.add_all(characters)
        await session.commit()


async def main():
    await init_db()
    async with aiohttp.ClientSession() as http_session:
        character_count = await get_character_count(http_session)
        character_counter = 0
        current_id = 1
        chunk_size = int(os.getenv("CHUNK_SIZE", 10))

        while character_counter < character_count:
            ids_to_request = range(current_id, current_id + chunk_size)
            characters = [get_character(i, http_session) for i in ids_to_request]
            result = await asyncio.gather(*characters)
            result = [char for char in result if char]
            asyncio.create_task(insert_character(result))
            character_counter += len(result)
            logger.info(f"Processed {character_counter}/{character_count} characters.")

            current_id += chunk_size

        tasks = asyncio.all_tasks()
        task_main = asyncio.current_task()
        tasks.remove(task_main)
        await asyncio.gather(*tasks)
    await close_db()


if __name__ == '__main__':
    asyncio.run(main())
