#!/bin/bash
IFS=$'\n'
dir=$(realpath -e -- $(dirname -- "$0"))

config_dir="$HOME/.local/share/aeroscripts"
state_file="$config_dir/installed_links.txt"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "[!] WARNING: \$HOME/.local/bin is not in your PATH."
fi

if [[ -f "$state_file" ]]; then
    while read -r link_path; do
        if [[ -L "$link_path" ]]; then
            target=$(readlink "$link_path")
            if [[ "$target" == $dir/* ]]; then
                if [[ ! -f "$target" ]]; then
                    echo "[-] $(basename "$link_path")"
                    rm "$link_path"
                fi
            fi
        fi
    done < "$state_file"
fi

mkdir -p "$config_dir"
> "$state_file"

for file in "$dir"/*; do
    if [[ ! -f "$file" ]]; then
        continue
    fi

    name=$(basename "$file")

    if [[ "$name" == "setup.sh" || "$name" == "install.sh" ]]; then
        continue
    fi

    if [[ "$name" == *.sh || "$name" == *.py ]]; then
        link_name="${name%.*}"
        dest_link="$HOME/.local/bin/$link_name"

        echo "[+] $name"
        ln -fs "$file" "$dest_link"
        chmod +x "$file"

        echo "$dest_link" >> "$state_file"
    fi
done
