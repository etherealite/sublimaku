from babelfish import Language
from sublimaku import JimakuSubtitle


def test_get_matches_episode_no_match(episodes):
    subtitle = JimakuSubtitle(
        language=Language('jpn'),
        subtitle_id='',
        series='Daily Lives of High School Boys',
        season=1,
        episode=3,
        title='High School Boys and the Morning Journey',
        year=2012,
    )
    matches = subtitle.get_matches(episodes['nonnon_s02e05'])
    assert matches == set()


def test_get_matches_episode_match(episodes):
    subtitle = JimakuSubtitle(
        language=Language('jpn'),
        subtitle_id='',
        series='Non Non Biyori',
        season=2,
        episode=12,
        title='We Ate Okonomiyaki',
        year=2015,
    )
    matches = subtitle.get_matches(episodes['nonnon_s02e05'])
    assert matches == {
        'series',
        'season',
        'episode',
        'title',
        'year',
    }