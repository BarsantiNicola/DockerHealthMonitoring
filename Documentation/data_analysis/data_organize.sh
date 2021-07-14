#!/bin/sh

mkdir temp
scp root@namenode:/root/data/bandwidth/* temp
scp root@namenode:/root/data/availability/* temp

mkdir -p low_low/low_low_0.1/availability
mkdir -p low_low/low_low_0.1/bandwidth

mkdir -p low_low/low_low_1/availability
mkdir -p low_low/low_low_1/bandwidth

mkdir -p low_low/low_low_2.5/availability
mkdir -p low_low/low_low_2.5/bandwidth


mkdir -p low_high/low_high_0.1/availability
mkdir -p low_high/low_high_0.1/bandwidth

mkdir -p low_high/low_high_1/availability
mkdir -p low_high/low_high_1/bandwidth

mkdir -p low_high/low_high_2.5/availability
mkdir -p low_high/low_high_2.5/bandwidth


mkdir -p high_low/high_low_0.1/availability
mkdir -p high_low/high_low_0.1/bandwidth

mkdir -p high_low/high_low_1/availability
mkdir -p high_low/high_low_1/bandwidth

mkdir -p high_low/high_low_2.5/availability
mkdir -p high_low/high_low_2.5/bandwidth


mkdir -p high_high/high_high_0.1/availability
mkdir -p high_high/high_high_0.1/bandwidth

mkdir -p high_high/high_high_1/availability
mkdir -p high_high/high_high_1/bandwidth

mkdir -p high_high/high_high_2.5/availability
mkdir -p high_high/high_high_2.5/bandwidth


mv temp/availability_test_high_low_2.5*.csv high_low/high_low_2.5/availability
mv temp/availability_test_high_low_1*.csv high_low/high_low_1/availability
mv temp/availability_test_high_low_0.1*.csv high_low/high_low_0.1/availability

mv temp/availability_test_low_low_2.5*.csv low_low/low_low_2.5/availability
mv temp/availability_test_low_low_1*.csv low_low/low_low_1/availability
mv temp/availability_test_low_low_0.1*.csv low_low/low_low_0.1/availability

mv temp/availability_test_low_high_2.5*.csv low_high/low_high_2.5/availability
mv temp/availability_test_low_high_1*.csv low_high/low_high_1/availability
mv temp/availability_test_low_high_0.1*.csv low_high/low_high_0.1/availability

mv temp/availability_test_high_high_2.5*.csv high_high/high_high_2.5/availability
mv temp/availability_test_high_high_1*.csv high_high/high_high_1/availability
mv temp/availability_test_high_high_0.1*.csv high_high/high_high_0.1/availability

mv temp/bandwidth_test_high_low_2.5*.csv high_low/high_low_2.5/bandwidth
mv temp/bandwidth_test_high_low_1*.csv high_low/high_low_1/bandwidth
mv temp/bandwidth_test_high_low_0.1*.csv high_low/high_low_0.1/bandwidth

mv temp/bandwidth_test_low_low_2.5*.csv low_low/low_low_2.5/bandwidth
mv temp/bandwidth_test_low_low_1*.csv low_low/low_low_1/bandwidth
mv temp/bandwidth_test_low_low_0.1*.csv low_low/low_low_0.1/bandwidth

mv temp/bandwidth_test_low_high_2.5*.csv low_high/low_high_2.5/bandwidth
mv temp/bandwidth_test_low_high_1*.csv low_high/low_high_1/bandwidth
mv temp/bandwidth_test_low_high_0.1*.csv low_high/low_high_0.1/bandwidth

mv temp/bandwidth_test_high_high_2.5*.csv high_high/high_high_2.5/bandwidth
mv temp/bandwidth_test_high_high_1*.csv high_high/high_high_1/bandwidth
mv temp/bandwidth_test_high_high_0.1*.csv high_high/high_high_0.1/bandwidth

rm -r temp

python3 test_tools.py
