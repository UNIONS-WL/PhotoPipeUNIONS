#!/bin/bash

md=$1
csv=$2
ldac=$3
image=$4

awk 'BEGIN{FS=","; OFS=","}{if (NR>1) print NR-1,$4, $5, $6, $159, $160, $164, $26, $27, $28, $32, $33}' \
     $csv \
     > $csv.tmp1.csv

awk 'BEGIN{FS=","}{for (i=1;i<=NF;i++) if ($i=="") printf "-99.0 "; else printf "%s ",$i; printf "\n"}' \
     $csv.tmp1.csv \
     > $csv.tmp2.asc

asctoldac_theli \
    -a $csv.tmp2.asc \
    -o $ldac.tmp1 \
    -c @RUNROOT@/@CONFIGPATH@/asctoldac_HSCPipe.conf

python3 @RUNROOT@/@SCRIPTPATH@/convert_HSCPipe_cat.py \
	$ldac.tmp1 \
	$ldac \
	$image

#rm $csv.tmp1.csv $csv.tmp2.asc $ldac.tmp1
