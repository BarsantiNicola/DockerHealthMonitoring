#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul  3 16:28:21 2021

@author: nico
"""
import os
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from datetime import timedelta
import numpy
import math
import json
from scipy import stats

def load_data(file_name) -> DataFrame:
    return pd.read_csv(file_name)

def remove_outliers(data):
    normalized_data = list()
    numpy_data = numpy.array(data)
    mean = numpy_data.mean()
    threshold = 1.5*stats.iqr(numpy_data)
    for pos in range(0,len(data)):
        if data[pos]<mean+threshold and data[pos]>mean-threshold:
            normalized_data.append(data[pos])
    return normalized_data

def compute_availability(file_name,discarded_pos=0):
    last_time = None
    last_total_time = None
    total_time = timedelta()
    available_time = timedelta()
    data = load_data(file_name)
    for pos in range(discarded_pos,int(data.size/2)):
        if last_time is not None:
            available_time += datetime.strptime(data.loc[pos][0], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S.%f')
        if data.loc[pos]['availability'] == 1:
            last_time = data.loc[pos][0]
        else:
            last_time = None
        if last_total_time is not None:
            total_time += datetime.strptime(data.loc[pos][0], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(last_total_time, '%Y-%m-%d %H:%M:%S.%f')
        last_total_time = data.loc[pos][0]
    return available_time/total_time*100

def compute_test_availability(test_name, threshold,discarded_pos=0, outliers= False):
    results = list()
    tests = os.listdir('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/availability')
    for test in tests:
        results.append(compute_availability('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/availability/'+test,discarded_pos))
    if outliers is True:
        results = remove_outliers(results)
    data = numpy.array(results)
    
    return {
            'name': test_name+'_'+threshold,
            'mean': data.mean(), 
            'variance': data.var(), 
            'bound': data.std()*1.94/math.sqrt(len(results))}

def availability_test(discarded_pos=0, outliers=False):
    test_names = ['low_low','low_high', 'high_low', 'high_high']
    test_values = ['0.1','1','2.5']
    results = list()
    for test_name in test_names:
        for test_value in test_values:
            results.append(compute_test_availability(test_name, test_value,discarded_pos, outliers)) 
    
    with open('/home/nico/Scrivania/results/availability.txt','w') as writer:
        json.dump(results, writer)

def evaluate_means(discarded_pos=0, outliers=False):
    test_names = ['low_low','low_high', 'high_low', 'high_high']
    test_values = ['0.1','1','2.5']
    results = list()
    for test_name in test_names:
        for test_value in test_values:
            results.append(compute_mean_availability(test_name, test_value,discarded_pos,outliers)) 

    with open('/home/nico/Scrivania/results/means.txt','w') as writer:
        json.dump(results, writer)
    
def compute_mean_availability(test_name, threshold,discarded_pos=0, outliers= False):
    results = list()
    tests = os.listdir('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/availability')
    for test in tests:
        results.append(compute_availability('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/availability/'+test, discarded_pos))
    if outliers is True:
        results = remove_outliers(results)
    return results

def compute_bandwidth(file_name, discarded_pos = 0):
    total_data = 0
    data = load_data(file_name)
    for pos in range(math.floor(discarded_pos/5),int(data.size/2)):
        total_data += data.loc[pos]['size']
    return total_data/int(data.size/2)

def compute_test_bandwidth(test_name, threshold, discarded_pos=0, outliers=False):
    results = list()
    tests = os.listdir('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/bandwidth')
    for test in tests:
        results.append(compute_bandwidth('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/bandwidth/'+test, discarded_pos))
    if outliers is True:
        results = remove_outliers(results)

    data = numpy.array(results)
    
    return {
            'name': test_name+'_'+threshold,
            'mean': data.mean(), 
            'variance': data.var(), 
            'bound': data.std()*1.94/math.sqrt(len(results))}
    return results
    
def bandwidth_test(discarded_pos=0, outliers=False):
    test_names = ['low_low','low_high', 'high_low', 'high_high']
    test_values = ['0.1','1','2.5']
    results = list()
    for test_name in test_names:
        for test_value in test_values:
            results.append(compute_test_bandwidth(test_name, test_value,discarded_pos, outliers)) 
    

    with open('/home/nico/Scrivania/results/bandwidth.txt','w') as writer:
        json.dump(results, writer)

def compute_max_bandwidth(file_name, discarded_pos = 0):
    data = load_data(file_name)
    max_val = 0
    for pos in range(discarded_pos,int(data.size/2)):
        if data.loc[pos]['size']>max_val:
            max_val = data.loc[pos]['size']
            
    return max_val

def compute_test_max_bandwidth(test_name, threshold, discarded_pos=0):
    results = list()
    tests = os.listdir('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/bandwidth')
    for test in tests:
        results.append(compute_max_bandwidth('/home/nico/Documenti/remotedata/'+test_name+'/'+test_name+'_'+threshold+'/bandwidth/'+test, discarded_pos))

    data = numpy.array(results)
    
    return {
            'name': test_name+'_'+threshold,
            'max': str(data.max())
            }
    
def bandwidth_max_test(discarded_pos = 0):
    test_names = ['low_low','low_high', 'high_low', 'high_high']
    test_values = ['0.1','1','2.5']
    results = list()
    for test_name in test_names:
        for test_value in test_values:
            results.append(compute_test_max_bandwidth(test_name, test_value,discarded_pos)) 
    
    with open('/home/nico/Scrivania/results/max_bandwidth.txt','w') as writer:
        json.dump(results, writer)    

def data_analysis(discarded_pos=0, outliers = False):
    bandwidth_max_test(discarded_pos)
    bandwidth_test(discarded_pos,outliers)
    availability_test(discarded_pos,outliers)
    