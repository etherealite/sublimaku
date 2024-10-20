import os
import pytest

from unittest.mock import Mock

from subliminal import Episode
from subliminal.cache import region

TESTS = os.path.dirname(__file__)

@pytest.fixture(autouse=True, scope='session')
def _configure_region():
    region.configure('dogpile.cache.null')
    region.configure = Mock()  # type: ignore[method-assign]


@pytest.fixture()
def episodes() -> dict[str, Episode]:
    return {
        "nonnon_s02e05": Episode(
            os.path.join(
                "Non Non Biyori (2013)", "Season 02", "Non Non Biyori-S02E05.mkv"
            ),
            'Non Non Biyori',
            2,
            12,
            original_series=False,
            title='We Ate Okonomiyaki',
            year=2015,
            tvdb_id=5260689,
            series_tvdb_id=272316,
            series_imdb_id='tt3114358',
            series_tmdb_id=66875,
            alternative_series=[
                'Non Non Biyori: Repeat',
                'のんのんびより りぴーと',
            ],
        )
    }
