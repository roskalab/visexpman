#!/bin/sh
outfolder="/mnt/mdrive/invivo/intrinsic/processed/georg"
if [ ! -d "$outfolder" ]; then
  echo "Need to mount m drive. Provide FMI password"
  echo "type the following command: sudo mount.cifs //argon.fmi.ch/groska.mdrive /mnt/mdrive -o username=koschgeor,uid=root,rw,file_mode=0777,dir_mode=0777"
else
    outfolder="$outfolder/$(basename $1)"
    #echo "$outfolder"
    if [ -d "$outfolder" ]; then
      echo "$outfolder already exists, remove it before running converter"
    else
      python3 /home/hd/converter_merged/visexpA/engine/dataprocessors/image.py --dirs $1
    fi
fi
