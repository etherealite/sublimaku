from datetime import timedelta
from typing import Any, TypedDict, Literal

import logging
import requests

from dogpile.cache import CacheRegion
from subliminal import (
    Movie,
    Episode,
    Video,
    __short_version__,
)
from subliminal.cache import REFINER_EXPIRATION_TIME, region

from sublimaku.common import session_factory

logger = logging.getLogger(__name__)


AniIDLink = TypedDict('AniIDLink', {
    'anidb_id': int,
    'anilist_id': int,
    'anime-planet_id': str,
    'anisearch_id': int,
    'imdb_id': str,
    'kitsu_id': int,
    'livechart_id': int,
    'mal_id': int,
    'notify.moe_id': str,
    'themoviedb_id': int,
    'thetvdb_id': int,
    'type': Literal['MOVIE', 'TV', 'UNKNOWN', 'ONA', 'OVA', 'SPECIAL'],
}, total=False)


class AniIDLinksCache:
    links_key = "AniIDLinks"
    etag_key = "AniIDLinksEtag"
    region: CacheRegion = region

    @classmethod
    def get(cls, expiration_time: int = REFINER_EXPIRATION_TIME) -> list[AniIDLink]:
        return cls.region.get(cls.links_key, expiration_time=expiration_time)

    @classmethod
    def set(cls, data: list[AniIDLink], etag: str) -> None:
        cls.region.set(cls.links_key, data)
        cls._set_etag(etag)


    @classmethod
    def get_etag(cls) -> str | None:
        return cls.region.get(cls.etag_key)

    @classmethod
    def _set_etag(cls, etag: str) -> None:
        cls.region.set(cls.etag_key, etag)


class AniIDLinkIndexer:
    data_url: str = 'https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-list-mini.json'
    # _ani_id_links: list[AniIDLink]
    # _themoviedb_table: dict[int, AniIDLink]
    # _thetvdb_table: dict[int, AniIDLink]
    # _updated: bool

    def __init__(
        self,
        ani_id_links: list[AniIDLink] | None = None,
        themoviedb_table: dict[int, AniIDLink] | None = None,
        thetvdb_table: dict[int, AniIDLink] | None = None,
        updated: bool = False,
    ) -> None:
        self._ani_id_links = ani_id_links
        self._themoviedb_table = themoviedb_table
        self._thetvdb_table = thetvdb_table
        self._updated = updated

    def lookup_themoviedb_id(self, themoviedb_id: int) -> AniIDLink | None:
        if not self._themoviedb_table:
            links = self.ani_id_links()
            self._themoviedb_table = {
                item["themoviedb_id"]: item for item in links if "themoviedb_id" in item
            }

        return self._themoviedb_table.get(themoviedb_id)

    def ani_id_links(self) -> list[AniIDLink]:
        if self._updated and self._ani_id_links:
            return self._ani_id_links

        if cached_list := AniIDLinksCache.get(REFINER_EXPIRATION_TIME):
            self._ani_id_links = cached_list
            self._updated = True
            return cached_list

        logger.debug('Updating AniIDLinks')

        data_url = self.data_url
        session = session_factory(requests.Session())

        cached_list = AniIDLinksCache.get(0)
        etag = region.get(
            "AniIDLinkIndexer.etag", expiration_time=timedelta(days=30).total_seconds()
        )

        if etag and cached_list:
            session.headers['If-None-Match'] = etag
            r = session.get(data_url)
            if r.status_code == 304:
                # no change
                self._ani_id_links = cached_list
                self._updated = True
                return cached_list

        # update
        r = session.get(data_url)

        AniIDLinksCache.set(self._ani_id_links, r.headers['ETag'])

        _ani_id_links = [AniIDLink(**item) for item in r.json()]
        self._ani_id_links = _ani_id_links
        self._updated = True
        return _ani_id_links
