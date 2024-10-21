from dataclasses import dataclass, field
from datetime import datetime
from typing import Self, Any, Iterator
from urllib.parse import urlparse, urlencode, urlparse


import requests

from subliminal.cache import region, SHOW_EXPIRATION_TIME

from sublimaku.common import session_factory



@dataclass
class JimakuFile:
    last_modified: datetime = field(
        metadata={
            "description": "The date of the newest uploaded file as an RFC3339 timestamp."
        }
    )
    name: str
    size: int
    url: str

    def __post_init__(self):
        if isinstance(self.last_modified, str):
            self.last_modified = datetime.fromisoformat(self.last_modified)


@dataclass
class JimakuFlags:
    adult: bool | None = field(
        default=None,
        metadata={"description": "The entry is meant for adult audiences."},
    )
    anime: bool | None = field(
        default=None, metadata={"description": "The entry is for an anime."}
    )
    external: bool | None = field(
        default=None,
        metadata={"description": "The entry comes from an external source."},
    )
    movie: bool | None = field(
        default=None, metadata={"description": "The entry is a movie."}
    )
    unverified: bool | None = field(
        default=None,
        metadata={
            "description": "The entry is unverified and has not been checked by editors."
        },
    )


@dataclass
class JimakuEntry:
    flags: JimakuFlags = field(
        metadata={"description": "Flags associated with the given entry."}
    )
    id: int = field(metadata={"description": "The ID of the entry."})
    name: str = field(
        metadata={
            "description": "The romaji name of the entry.",
            "example": "Sousou no Frieren",
        }
    )
    last_modified: datetime = field(
        metadata={
            "description": "The date of the newest uploaded file as an RFC3339 timestamp."
        }
    )
    anilist_id: int | None = field(
        default=None,
        metadata={"description": "The anilist ID of this entry.", "example": 154587},
    )
    creator_id: int | None = field(
        default=None, metadata={"description": "The account ID that created this entry"}
    )
    english_name: str | None = field(
        default=None,
        metadata={
            "description": "The English name of the entry.",
            "example": "Frieren: Beyond Journey’s End",
        },
    )
    japanese_name: str | None = field(
        default=None,
        metadata={
            "description": "The Japanese name of the entry, i.e. with kanji and kana.",
            "example": "葬送のフリーレン",
        },
    )
    notes: str | None = field(
        default=None,
        metadata={
            "description": "Extra notes that the entry might have. Supports a limited set of markdown. Can only be set by editors."
        },
    )
    tmdb_id: int | None = field(
        default=None,
        metadata={
            "description": "The TMDB ID of this entry.",
            "example": "tv:12345",
            "pattern": "(tv|movie):(\\d+)",
        },
    )


    def __post_init__(self):
        if isinstance(self.last_modified, str):
            self.last_modified = datetime.fromisoformat(self.last_modified)
        
        if isinstance(self.flags, dict):
            self.flags = JimakuFlags(**self.flags)



class JimakuClient:
    _session: requests.Session

    def __init__(self, apikey: str, session: requests.Session | None = None) -> None:
        self.url_base = 'https://jimaku.cc'

        if not session:
            session = session_factory(requests.Session())
            session.headers['Authorization'] = apikey

        self._session = session

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def search(
            self,
            anilist_id: int | str | None = None,
            tmdb_id: int | str | None = None,
            tmdb_is_movie: bool | None = None,
            query: str | None = None
    ) -> tuple[JimakuEntry, ...]:
        """
            Searches for the jimaku entry of the given anilist id. 
            
            endpoint:GET /api/entries/search{?anilist_id,tmdb_series_id,query}
        """

        assert (anilist_id or tmdb_id or query)

        if tmdb_id:
            assert(tmdb_is_movie is not None)
            tmdb_type = 'movie' if tmdb_is_movie else 'tv'
        else:
            tmdb_type = None


        params: dict[str, str] = dict(
            **{'anilist_id': anilist_id} if anilist_id else {},
            **{'tmdb_id': f"{tmdb_type}:{tmdb_id}"} if tmdb_id else {},
            **{'query': query} if query else {},
        )


        params_encoded = urlencode(params)

        endpoint = f"/api/entries/search?{params_encoded}"

        try:
            response = self._session.get(self.url_base + endpoint)
        except Exception as e:
            raise e

        if response.status_code != 200:
            response.raise_for_status()
        

        return tuple(
            JimakuEntry(**entry,)
            for entry in response.json()
        )


    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def files(self, jimaku_id: int) -> tuple[JimakuFile, ...]:
        """
            Gets the files of the given jimaku entry id. 
            
            endpoint:GET /api/entries/{id}/files
        """
        endpoint = f"/api/entries/{jimaku_id}/files"
        response = self._session.get(self.url_base + endpoint)

        if response.status_code != 200:
            response.raise_for_status()
        
        return tuple(
            JimakuFile(**file)
            for file in response.json()
        )