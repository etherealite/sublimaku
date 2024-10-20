from subliminal import cli

p = r'D:\library\immersion-movies\Non Non Biyori Vacation (2018)\Non Non Biyori Vacation.mkv'
cli.subliminal(['download', '--language', 'jpn', '--provider', 'jimaku', '--refiner', 'tmdb', p])
