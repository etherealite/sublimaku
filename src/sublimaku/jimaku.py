import re

from dataclasses import dataclass
from typing import Any, ClassVar, NamedTuple
from collections.abc import Callable, Sequence

import requests

from babelfish import Language
from dogpile.cache import CacheRegion
from guessit import guessit
from subliminal import (
    Movie,
    Episode,
    Provider,
    Subtitle,
    Video,
    
)
from subliminal.exceptions import NotInitializedProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import SUBTITLE_EXTENSIONS
from subliminal.cache import region

from sublimaku.ani_id_links import AniIDLinkIndexer
from sublimaku.common import session_factory
from sublimaku.jimaku_api import JimakuClient, JimakuEntry,JimakuFile


ani_id_links = AniIDLinkIndexer()

class JimakuSubtitle(Subtitle):
    provider_name: ClassVar[str] = 'jimaku'

    series: str
    """Series title"""
    season: int
    """Season number"""
    episode: int
    """Episode number"""
    title: str
    """Episode title"""
    year: int
    """Episode year"""
    release_group: str
    """Release group name"""

    def __init__(
        self,
        # Base class parameters
        language: Language | None,
        subtitle_id: str,
        *,
        hearing_impaired: bool | None = None,
        page_link: str | None = None,
        encoding: str | None = None,
        subtitle_format: str | None = None,
        fps: float | None = None,
        guess_encoding: bool = True,

        # this class specific parameters
        video: Video,
        series: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        title: str | None = None,
        year: int | None = None,
        release_group: str | None = None,
    ):
        super().__init__(
            language,
            subtitle_id,
            hearing_impaired=hearing_impaired,
            page_link=page_link,
            encoding=encoding,
            subtitle_format=subtitle_format,
            fps=fps,
            guess_encoding=guess_encoding,
        )
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.release_group = release_group


    @property
    def info(self) -> str:
        """Information about the subtitle."""
        # Series (with year)
        series_year = f'{self.series} ({self.year})' if self.year is not None else self.series

        # Title with release group
        parts = []
        if self.title:
            parts.append(self.title)
        if self.release_group:
            parts.append(self.release_group)
        title_part = ' - '.join(parts)

        return f'{series_year} s{self.season:02d}e{self.episode:02d}{title_part}'


    def get_matches(self, video: Movie | Episode) -> set[str]:
        """Get the matches against the `video`."""

        # series name
        matches = guess_matches(
            video,
            {
                'title': self.series,
                'season': self.season,
                'episode': self.episode,
                'episode_title': self.title,
                'year': self.year,
                'release_group': self.release_group,
            },
        )

        # other properties
        # if self.release_group:
        #     matches |= guess_matches(video, guessit(self.release_group, {'type': 'episode'}), partial=True)

        return matches
    



class ArchiveRepo:
    supported_exts = ('zip', '7z')
    def __init__(self, region: CacheRegion = region):
        self._region = region
    
    def list_zip(self, jimaku_file: JimakuFile) -> list[str]:
        pass


    @classmethod
    def supported(cls, file: JimakuFile) -> bool:
        name = file.name
        stem = name.split('.')[-1].lower()
        return stem in cls.supported_exts
    

def create_query_filter():
    surrounds = lambda s: fr'[\[\(]{s}[\]\)]'
    whisper_expr = re.compile(
        fr'{surrounds("whisperai")}|{surrounds("whisper")}', re.IGNORECASE
    )

    exts = set(ext[1:] for ext in SUBTITLE_EXTENSIONS)

    min_size = 500
    def filter_query(result: QueryResult) -> bool:
        return (
            # get rid of whisperai trash.
            not whisper_expr.search(result.real_filename)
            # filter out all the archive files for now.
            and '.'.split(result.real_filename)[-1].lower() in exts
            # discard files that are too small to be real subtitles
            and result.real_file_size >= min_size
        )

    return filter_query



class QueryResult(NamedTuple):
    api_entry: JimakuEntry
    api_file: JimakuFile
    real_filename: str
    real_file_size: int
    is_archived: bool
    archive_name: str | None = None
    archive_key: str | None = None


class JimakuProvider(Provider):
    languages: set[Language] = {Language('jpn')}

    subtitle_class = JimakuSubtitle

    def __init__(self, apikey: str):
        self.apikey = apikey

    def initialize(
            self,
            jimaku_client: JimakuClient | None = None,
            session: requests.Session | None = None,
            archive_repo: ArchiveRepo | None = None
    ) -> None:
        """Initialize the provider."""
        self.session = (
            session
            if session else session_factory(requests.Session())
        )

        self.session.headers.setdefault('Api-Key', self.apikey)

        self.jimaku_client = (
            jimaku_client
            if jimaku_client else JimakuClient(self.apikey, self.session)
        )

        self.archive_repo = (
            archive_repo
            if archive_repo else ArchiveRepo()
        )

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.session:
            raise NotInitializedProviderError

    def query(self, video: Movie | Episode) -> QueryResult:
        """Query the provider for subtitles."""

        tmdb_id = video.tmdb_id
        anilist_id = getattr(video, 'anilist_id', None)
    
        if tmdb_id and not anilist_id:
            id_links =ani_id_links.lookup_themoviedb_id(tmdb_id)
            anilist_id = id_links.get('anilist_id') if id_links else None

        use_anilist = anilist_id is not None
        use_tmdb = not use_anilist and tmdb_id is not None
        use_fuzzy = not use_anilist and use_tmdb

        title = video.series if isinstance(video, Episode) else video.title

        entries = self.jimaku_client.search(
            anilist_id=anilist_id if use_anilist else None,
            tmdb_series_id=tmdb_id if not anilist_id else None,
            tmdb_series_id_is_movie=use_tmdb and isinstance(video, Movie),
            query=title if use_fuzzy else None
        )

        if not entries:
            entries = self.jimaku_client.search(query=title)

        if not entries:
            return None


        api_entry = entries[0]
        api_files = self.jimaku_client.files(jimaku_id=api_entry.id)

        results: list[QueryResult] = []
        for api_file in api_files:
            if self.archive_repo.supported(api_file):
                continue
            else:
                result = QueryResult(
                    api_entry=api_entry,
                    api_file=api_file,
                    real_filename=api_file.name,
                    real_file_size=api_file.size,
                    is_archived=False,
                )
                results.append(result)

        return results
        

    def list_subtitles(self, video: Video, *args, **kwargs) -> list[JimakuSubtitle]:
        results = filter(create_query_filter(), self.query(video))

        def create(result: QueryResult) -> JimakuSubtitle:
            api_entry = result.api_entry
            filename = result.real_filename
            page_link = f"https://jimaku.cc/entry/{api_entry.id}"
            return JimakuSubtitle(None, filename, page_link=page_link)

        return [create(result) for result in results]


