# Sublimaku

## A jimaku.cc Subtitle Provider for Subliminal


Usage
-----

Run subliminal as usual but with the caveat that you will need to ensure that you
are using the tmdb refiner

```bash
$ subliminal download 
  --language jpn 
  --refiner tmdb
  /path/to/vid.mkv
```

When you want to use jimaku.cc as the sole provider from witch to get subtiles.
```bash
$ subliminal download 
  --language jpn 
  --provider jimaku
  --refiner tmdb
  /path/to/vid.mkv
```

Requirements
------------
* Python >= 3.12
* Subliminal >= 2.2.1
* The Movie DB API Key
* Jimaku.cc API Key


Installation
------------
Follow the installation instructions for [Subliminal](https://github.com/Diaoul/subliminal) and then issue

`pip install git+https://github.com/etherealite/{repo_name}/archive/master.tar.gz`

to install sublimaku as a provider to Subliminal.
