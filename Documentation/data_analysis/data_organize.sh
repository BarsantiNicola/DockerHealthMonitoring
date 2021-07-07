#!/bin/sh

scp root@namenode:/root/data/bandwidth/* /home/nico/Documenti/remotedata/temp
scp root@namenode:/root/data/availability/* /home/nico/Documenti/remotedata/temp

mv /home/nico/Documenti/remotedata/temp/availability_test_high_low_2.5*.csv /home/nico/Documenti/remotedata/high_low/high_low_2.5/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_high_low_1*.csv /home/nico/Documenti/remotedata/high_low/high_low_1/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_high_low_0.1*.csv /home/nico/Documenti/remotedata/high_low/high_low_0.1/availability

mv /home/nico/Documenti/remotedata/temp/availability_test_low_low_2.5*.csv /home/nico/Documenti/remotedata/low_low/low_low_2.5/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_low_low_1*.csv /home/nico/Documenti/remotedata/low_low/low_low_1/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_low_low_0.1*.csv /home/nico/Documenti/remotedata/low_low/low_low_0.1/availability

mv /home/nico/Documenti/remotedata/temp/availability_test_low_high_2.5*.csv /home/nico/Documenti/remotedata/low_high/low_high_2.5/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_low_high_1*.csv /home/nico/Documenti/remotedata/low_high/low_high_1/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_low_high_0.1*.csv /home/nico/Documenti/remotedata/low_high/low_high_0.1/availability

mv /home/nico/Documenti/remotedata/temp/availability_test_high_high_2.5*.csv /home/nico/Documenti/remotedata/high_high/high_high_2.5/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_high_high_1*.csv /home/nico/Documenti/remotedata/high_high/high_high_1/availability
mv /home/nico/Documenti/remotedata/temp/availability_test_high_high_0.1*.csv /home/nico/Documenti/remotedata/high_high/high_high_0.1/availability

mv /home/nico/Documenti/remotedata/temp/bandwidth_test_high_low_2.5*.csv /home/nico/Documenti/remotedata/high_low/high_low_2.5/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_high_low_1*.csv /home/nico/Documenti/remotedata/high_low/high_low_1/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_high_low_0.1*.csv /home/nico/Documenti/remotedata/high_low/high_low_0.1/bandwidth

mv /home/nico/Documenti/remotedata/temp/bandwidth_test_low_low_2.5*.csv /home/nico/Documenti/remotedata/low_low/low_low_2.5/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_low_low_1*.csv /home/nico/Documenti/remotedata/low_low/low_low_1/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_low_low_0.1*.csv /home/nico/Documenti/remotedata/low_low/low_low_0.1/bandwidth

mv /home/nico/Documenti/remotedata/temp/bandwidth_test_low_high_2.5*.csv /home/nico/Documenti/remotedata/low_high/low_high_2.5/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_low_high_1*.csv /home/nico/Documenti/remotedata/low_high/low_high_1/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_low_high_0.1*.csv /home/nico/Documenti/remotedata/low_high/low_high_0.1/bandwidth

mv /home/nico/Documenti/remotedata/temp/bandwidth_test_high_high_2.5*.csv /home/nico/Documenti/remotedata/high_high/high_high_2.5/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_high_high_1*.csv /home/nico/Documenti/remotedata/high_high/high_high_1/bandwidth
mv /home/nico/Documenti/remotedata/temp/bandwidth_test_high_high_0.1*.csv /home/nico/Documenti/remotedata/high_high/high_high_0.1/bandwidth

