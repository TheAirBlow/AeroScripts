# AeroScripts
Collection of useful miscellaneous scripts I personally use on a day-to-day basis.

## Installation
> [!NOTE]
> Make sure $HOME/.local/bin/ is in your PATH before proceeding

1. Run the `setup.sh` script to create the `venv` directory and install all required python dependencies
2. Run the `install.sh` script to link all scripts to `~/.local/bin/`

## Scripts
- `otval-daemon.sh` - monitors internet connection and notifies about it dropping out
- `swearscan.py` - scans GitHub repos for swear words across multiple users/orgs
- `deduplicate.py` - deduplicates images by perception hash and files by sha256
- `git-clean.sh` - recursively cleans git repositories in the current directory
- `ytmsync.py` - downloads youtube music playlist and appends metadata
- `extsort.sh` - sorts files recursively by their extension to folders
- `adbsync.py` - synchronizes local directory with remote through ADB
- `llmify.py` - combines a folder of files into one LLM-friendly file
- `fixnames.py` - fixes mojibake filenames and uppercase extensions
- `hashify.py` - recursively renames files to their MD5 hash
- `movloop.py` - generates a looping gif from video
- `scompress.sh` - simple compression script

## License
[Mozilla Public License Version 2.0](https://github.com/TheAirBlow/Scripts/blob/main/LICENCE)
