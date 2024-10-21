from subliminal import cli

p = r'D:\library\immersion-shows\Non Non Biyori (2013)\Season 02\Non Non Biyori-S02E05.mkv'
cli.subliminal(
    [
        "--debug",
        "download",
        "--language",
        "jpn",
        "--provider",
        "jimaku",
        "--refiner",
        "tmdb",
        p,
    ]
)
