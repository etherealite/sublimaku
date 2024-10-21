from unittest.mock import patch

import pytest
import responses

from dogpile.cache import make_region
from subliminal.cache import to_native_str_key_generator

from sublimaku.ani_id_links import AniIDLinkIndexer, AniIDLink, AniIDLinksCache


nonnon = AniIDLink(**{
    "anidb_id": 9722,
    "anilist_id": 17549,
    "anime-planet_id": "non-non-biyori",
    "anisearch_id": 8390,
    "imdb_id": "tt3114358",
    "kitsu_id": 7711,
    "livechart_id": 93,
    "mal_id": 17549,
    "notify.moe_id": "CGzppFiig",
    "themoviedb_id": 66875,
    "thetvdb_id": 272316,
    "type": "TV",
})


order_arabbit = AniIDLink(**{
    "anidb_id": 1292,
    "anilist_id": 1209,
    "anime-planet_id": "nasu-summer-in-andalusia",
    "anisearch_id": 673,
    "imdb_id": "tt0382868",
    "kitsu_id": 1087,
    "livechart_id": 5776,
    "mal_id": 1209,
    "notify.moe_id": "A3dxcFmmR",
    "themoviedb_id": 60843,
    "type": "MOVIE",
})

test_links: list[AniIDLink] = [nonnon, order_arabbit]

def mem_region(expiration_time=0):
    region = make_region(function_key_generator=to_native_str_key_generator)
    region.configure(
        'dogpile.cache.memory',
        expiration_time=0
    )
    return region


def add_mock_response(responses: responses.RequestsMock, json_data, status=200):
    return responses.add(
        responses.GET,
        'https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-list-mini.json',
        json=json_data,
        status=status,
        adding_headers={'Etag': 'test_etag'},
    )

@pytest.fixture(autouse=True)
def mock_responses_and_cache():
    with responses.RequestsMock() as rsps:
        add_mock_response(rsps, test_links)
        region = mem_region()
        with patch.object(AniIDLinksCache, 'region', region) as mock_region:
            yield rsps, mock_region

@pytest.fixture
def mock_cache():
    region = mem_region()
    with patch.object(AniIDLinksCache, 'region', region):
        yield region

def test_requests_only_once(mock_responses_and_cache):
    responses, _ = mock_responses_and_cache
    indexer = AniIDLinkIndexer()
    internal_list1 = indexer.ani_id_links()
    internal_list2 = indexer.ani_id_links()

    assert len(responses.calls) == 1

def test_get_list_cache_only_once(mock_responses_and_cache):
    _, mock_region = mock_responses_and_cache
    with patch.object(mock_region, 'get', return_value=test_links) as patched_get:
        AniIDLinksCache.set(test_links, 'test_etag')
        indexer = AniIDLinkIndexer()
        indexer.ani_id_links()
        indexer.ani_id_links()
        patched_get.assert_called_once()
    
def test_find_tmdb():
    indexer = AniIDLinkIndexer(test_links, updated=True)
    found = indexer.lookup_themoviedb_id(66875)
    assert found == nonnon

def test_no_find_tmdb():
    indexer = AniIDLinkIndexer(test_links, updated=True)
    found = indexer.lookup_themoviedb_id(42)
    assert found == None


# TODO: this doesn't actually test anything
def test_fetch_data():
    indexer = AniIDLinkIndexer()
    assert indexer.ani_id_links() == test_links


# TODO: this doesn't actually test anything
def test_uses_cached_etags(mock_cache):
    mock_cache.set(AniIDLinksCache.etag_key, 'test_etag')
    indexer = AniIDLinkIndexer()
    found = indexer.lookup_themoviedb_id(66875)
    assert found == nonnon


def test_uses_cached_list(mock_cache, mock_response):
    with patch.object(AniIDLinksCache, 'get', return_value=test_links) as mock_get:
        AniIDLinksCache.set(test_links, 'test_etag')
        indexer = AniIDLinkIndexer()
        found = indexer.lookup_themoviedb_id(66875)
        mock_get.assert_called_once()
        assert mock_response.call_count == 0
        assert found == nonnon