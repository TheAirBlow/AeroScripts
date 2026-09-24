#!/bin/bash
IFS=$'\n'

term() {
  echo "Exiting..."
  exit -1
}

trap term INT

if [ "$1" != "--skip-warning" ]; then
  echo "This will recursively compress ALL images, gifs and videos."
  read -p "Do you want to continue? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled by user"
    exit -1
  fi
fi

find . -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpe" -o -name "*.jpeg" -o -name "*.jfif" \) -print0 | \
xargs -0 -P 8 -I {} bash -c '
  file="{}"
  new="${file%.*}.webp"
  temp="${file}_tmp.png"
  echo "$file -> $new"

  magick "$file" -resize 1920x1080\> "$temp"
  cwebp -q 90 -m 0 -quiet -mt "$temp" -o "$new"

  if [ $? -eq 0 ]; then
    rm "$file" "$temp"
  fi
'

for file in $(find . -type f -name "*.gif"); do
  new=${file%.*}.webp
  echo "$file -> $new"
  #gif2webp "$file" -o "$new"
  magick "$file" -resize 4800x1620\> -delay 4 "$new"
  rm "$file"
done

for file in $(find . -type f -name "*.mp4" -o -name "*.mov" -o -name "*.wmv" -o -name "*.mkv" -o -name "*.webm"); do
  new="${file%.*}.mp4"
  echo "$file -> $new"
  ffmpeg -i "$file" -vf "scale='min(1080,iw*min(1080/iw,2400/ih))':'min(2400,ih*min(1080/iw,2400/ih))'" -c:v hevc_nvenc -c:a aac "${file}_tmp.mp4"
  rm "$file"
  mv "${file}_tmp.mp4" "$new"
done
