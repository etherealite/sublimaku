import re

from dataclasses import dataclass, field
from collections.abc import Callable, Set
from typing import Any, Annotated, cast, ClassVar, NamedTuple, TypeVar

import requests


from babelfish import Language # type: ignore
from dogpile.cache import CacheRegion # type: ignore
from guessit import guessit # type: ignore
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

T = TypeVar('T')

type VideoDual[T] = Annotated[T, Movie | Episode]
"""Dual perpose attribute, significance depends on the type of `video`"""
type EpisodeOnly[T] = Annotated[T, Episode]
"""Only present on episodes"""
type MovieOnly[T] = Annotated[T, Movie]
"""Only present on movies"""

@dataclass
class VideoMatchable:
    series: EpisodeOnly[str] | None = None
    """Name of the Series"""
    season: EpisodeOnly[int] | None = None
    """Season number of the series"""
    episode: EpisodeOnly[int] | None = None
    """Episode number  of the series"""
    year: VideoDual[int] | None = None
    """Year of the series or movie not the episode"""
    title: VideoDual[str] | None = None
    """Episode title or Movie title"""
    alternative_titles: MovieOnly[list[str]] = field(default_factory=list)
    """Alternative titles for the movie"""
    alternative_series: EpisodeOnly[list[str]] = field(default_factory=list)
    """Alternative names for the series"""
    tmdb_id: VideoDual[int] | None = None
    """TMDB ID of the exact episode or movie not the series"""
    imdb_id: VideoDual[str] | None = None
    """IMDB ID of the exact episode or movie not the series"""
    series_imdb_id: EpisodeOnly[str] | None = None
    """IMDB ID of the whole series"""
    series_tvdb_id: EpisodeOnly[str] | None = None
    """TVDB ID of the whole series"""
    series_tmdb_id: EpisodeOnly[int] | None = None
    """TMDB ID of the whole series"""
    series_anilist_id: EpisodeOnly[int] | None = None
    """AniList ID of the whole series"""


class JimakuSubtitle(Subtitle):
    # Super class stuff
    provider_name: ClassVar[str] = 'jimaku'
    """The entrypoint? of the provider that produced this subtitle"""

    language: Language
    """Language of the subtitle"""

    page_link: str | None
    """Link to the web page from which the subtitle can be downloaded"""

    video: Video
    """The video providing criteria for this subtitle"""

    file_path: str
    """
    The path and file name of the archive file
    
    Includes both the possible name of the archive as a directory
    and any subdirectories in the archive.
    """

    is_archived: bool
    """Whether the subtitle is in an archive"""

    matchable: VideoMatchable
    """Attributes that can be used to match against the video"""


    def __init__(
        self,
        # Base class parameters
        language: Language,
        subtitle_id: str,
        *,
        page_link: str | None = None,
        subtitle_format: str | None = None,
        fps: float | None = None,
        guess_encoding: bool = True,

        # this class specific parameters
        ##################################
        video: Video,
        file_path: str,
        is_archived: bool,
        matchable: VideoMatchable,
    ):
        super().__init__(
            language,
            subtitle_id,
            page_link=page_link,
            subtitle_format=subtitle_format,
            fps=fps,
            guess_encoding=guess_encoding,
        )
        self._matchable = matchable
        self.video = video
        self.file_path = file_path
        self.is_archived = is_archived


    @property
    def info(self) -> str:
        """Information about the subtitle."""
        return self.file_path
    
    # @property
    # def series(self):
    #     return self._matchable.series
    
    # @property
    # def season(self):
    #     return self._matchable.season

    # @property
    # def episode(self):
    #     return self._matchable.episode

    # @property
    # def year(self):
    #     return self._matchable.year

    # @property
    # def title(self):
    #     return self._matchable.title

    # @property
    # def alternative_titles(self):
    #     return self._matchable.alternative_titles

    # @property
    # def alternative_series(self):
    #     return self._matchable.alternative_series

    # @property
    # def tmdb_id(self):
    #     return self._matchable.tmdb_id

    # @property
    # def imdb_id(self):
    #     return self._matchable.imdb_id
    
    # @property
    # def series_imdb_id(self):
    #     return self._matchable.series_imdb_id
    
    # @property
    # def series_tvdb_id(self):
    #     return self._matchable.series_tvdb_id
    
    # @property
    # def series_tmdb_id(self):
    #     return self._matchable.series_tmdb_id
    
    # @property
    # def series_anilist_id(self):
    #     return self._matchable.series_anilist_id

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""

        matchable = self._matchable

        guess: dict[str, Any] = cast(dict[str, Any], guessit(self.file_path))
        assert isinstance(guess, dict)

        # series name
        matches = guess_matches(
            video,
            {
                'series': matchable.series,
                'title': matchable.title,
                'season': matchable.season,
                'episode': matchable.episode,
                'year': matchable.year,
                #'country': matchable.country,
                #'release_group': release_group_matches,
                #'streaming_service': streaming_service_matches,
                #'resolution': resolution_matches,
                #'source': source_matches,
                #'video_codec': video_codec_matches,
                #'audio_codec': audio_codec_matches,
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
    
    def list_zip(self, jimaku_file: JimakuFile):
        pass


    @classmethod
    def has_supported_ext(cls, file: JimakuFile) -> bool:
        name = file.name
        stem = name.split('.')[-1].lower()
        return stem in cls.supported_exts
    

def create_query_filter():
    br: Callable[[str], str] = lambda s: fr'[\[\(]{s}[\]\)]'
    whisper_expr = re.compile(
        fr'{br("whisperai")}|{br("whisper")}', re.IGNORECASE
    )

    exts = set(ext[1:] for ext in SUBTITLE_EXTENSIONS)

    min_size = 500
    def filter_query(result: QueryResult) -> bool:
        file_path = result.file_path
        return (
            # get rid of whisperai trash.
            not whisper_expr.search(file_path.lower())
            # filter out all the archive files for now.
            and '.'.split(file_path)[-1].lower() in exts
            # discard files that are too small to be real subtitles
            and result.real_file_size >= min_size
        )

    return filter_query



class QueryResult(NamedTuple):
    # entry object returned by api
    api_entry: JimakuEntry
    # file object returned by api associated with the entry
    api_file: JimakuFile
    # file size as extracted if arhived
    real_file_size: int
    # path of the file including the archive as the directory
    # ex:
    # "Show Name - Season 01.zip/some directory name/Show Name - 01.srt"
    file_path: str
    is_archived: bool
    archive_name: str | None = None
    archive_key: str | None = None


class JimakuProvider(Provider[JimakuSubtitle]):
    languages: ClassVar[Set[Language]] = frozenset({Language('jpn')})

    subtitle_class = JimakuSubtitle

    def __init__(
        self, 
        apikey: str,
        jimaku_client: JimakuClient | None = None,
        session: requests.Session | None = None,
        archive_repo: ArchiveRepo | None = None,
    ):
        self.apikey = apikey

        self.session = (
            session
            if session else session_factory(requests.Session())
        )

        self.session.headers.setdefault('Authorization', self.apikey)

        self.jimaku_client = (
            jimaku_client
            if jimaku_client else JimakuClient(self.apikey, self.session)
        )

        self.archive_repo = (
            archive_repo
            if archive_repo else ArchiveRepo()
        )


    def initialize(self) -> None:
        """Initialize the provider."""

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.session:
            raise NotInitializedProviderError


    def query(self, video: Video) -> list[JimakuSubtitle]:
        """
        Query Jimaku based on video attrs and Transform results

        Jimaku doesn't track episode specific information aso all the
        id's in this code are for the whole series and not invdividual
        episodes.
        """

        id_link = (
            ani_id_links.lookup_themoviedb_id(video.tmdb_id)
            if video.tmdb_id else None
        )


        anilist_id = None
        if id_link:
            anilist_id = (
                getattr(video, 'series_anilist_id', None) or
                id_link.get('anilist_id')
            )

        title = video.series if isinstance(video, Episode) else video.title

        is_movie = isinstance(video, Movie)
        # results = filter(create_query_filter(), self.query(video))
        results = self.query_jimaku(
            anilist_id=anilist_id,
            tmdb_id=video.tmdb_id,
            title=title,
            is_movie=is_movie
        )


        series_imdb_id = None
        imdb_id = None # movie id, else the episode id
        series_tvdb_id = None
        if id_link:
            if is_movie:
                imdb_id = id_link.get('imdb_id')
            else:
                series_imdb_id = id_link.get('imdb_id')
                series_tvdb_id = id_link.get('tvdb_id')

        def create_subtitle(result: QueryResult) -> JimakuSubtitle:
            api_entry = result.api_entry
            file_path = result.file_path
            page_link = f"https://jimaku.cc/entry/{api_entry.id}"

            alternatives: list[str] = [
                title for title in (api_entry.name, api_entry.japanese_name)
                if isinstance(title, str)
            ]


            matchable = None
            if is_movie:
                matchable = VideoMatchable(
                    title=api_entry.english_name,
                    alternative_titles=alternatives,
                    tmdb_id=api_entry.tmdb_id,
                    imdb_id=imdb_id,
                )

            else:
                matchable = VideoMatchable(
                    series = api_entry.english_name,
                    series_tmdb_id=api_entry.tmdb_id,
                    series_anilist_id=api_entry.anilist_id,
                    series_imdb_id=series_imdb_id,
                    series_tvdb_id=series_tvdb_id,
                    alternative_series=alternatives,
            )

            return JimakuSubtitle(
                Language('jpn'),
                f"{api_entry.id}:{file_path}",
                matchable=matchable,
                page_link=page_link,
                video=video,
                file_path=file_path,
                is_archived=False,
            )

        return [create_subtitle(result) for result in results]

    def query_jimaku(
        self,
        anilist_id: int | None = None,
        tmdb_id: int | None = None,
        title: str | None = None,
        is_movie: bool | None = None
    ) -> list[QueryResult]:
        """Query the provider for subtitles."""

        entries = None
        # prefer anilist
        if anilist_id:
            entries = self.jimaku_client.search(
                anilist_id=anilist_id
            )

        if not entries and tmdb_id:
            entries = self.jimaku_client.search(
                tmdb_id=tmdb_id,
                tmdb_is_movie=is_movie,
            )

        if not entries:
            entries = self.jimaku_client.search(query=title)

        if not entries:
            return []

        results: list[QueryResult] = []
        for entry in entries:
            files = self.jimaku_client.files(jimaku_id=entry.id)
            for file in files:
                if self.archive_repo.has_supported_ext(file):
                    continue
                else:
                    result = QueryResult(
                        api_entry=entry,
                        api_file=file,
                        # no archive support yet for the bellow
                        file_path=file.name,
                        real_file_size=file.size,
                        is_archived=False,
                    )
                    results.append(result)

        return results
        

    def list_subtitles(
            self, video: Video, languages: Set[Language]
    ) -> list[JimakuSubtitle]:

        return self.query(video)