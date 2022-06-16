#!/bin/bash

# download relative wealth index
wget -O rwi.zip "https://data.humdata.org/dataset/76f2a2ea-ba50-40f5-b79c-db95d668b843/resource/bff723a4-6b55-4c51-8790-6176a774e13c/download/relative-wealth-index-april-2021.zip"
mkdir -p "raw/facebook/"
unzip rwi.zip -d "raw/facebook/"
rm rwi.zip

