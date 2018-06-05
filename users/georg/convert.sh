#!/bin/sh
outfolder="/mnt/mdrive/invivo/intrinsic/processed/georg"
if [ ! -d "$outfolder" ]; then
  echo "Need to mount m drive. Provide FMI password"
  sudo mount.cifs //argon.fmi.ch/groska.mdrive /mnt/mdrive -o username=koschgeor,uid=root,rw,file_mode=0777,dir_mode=0777
fi
outfolder="$outfolder/$(basename $1)"
#echo "$outfolder"
if [ -d "$outfolder" ]; then
  echo "$outfolder already exists, remove it before running converter"
else
  sudo python /home/hd/converter/visexpA/engine/dataprocessors/image.py $1
fi
