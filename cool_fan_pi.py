# -*- coding:utf-8 -*-
# date: 2018-10-08 23:54
"""
控制树莓派风扇
"""
import os
import time
import commands
import RPi.GPIO as GPIO
from datetime import datetime

T_HIGH = 48  # 温度>48度开始转动，在温度传感器失效时使用
T_LOW = 42  # 温度<42度停止转动，在温度传感器失效时使用
T_DIFF_HIGH = 24  # 温差>24度开始转动
T_DIFF_LOW = 18  # 温差<18度停止转动
T_SENOR_DIFF = 0  # 温度传感器和真实环境温度矫正值
fan_pin = 12  # 风扇IO针脚BOARD编号
NPN = True  # 控制风扇用的是NPN三极管
IS_LOG_FILE = True  # 是否输出温度信息到文件
IS_LOG_CONSOLE = True  # 是否输出温度信息到控制台
time_interval = 5  # 检测温度间隔时间单位秒
log_file_duration = 12  # 日志记录保留时间长度，单位小时

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_file_path = os.path.join(base_dir, 'temperature_log')
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(fan_pin, GPIO.OUT)
temp_path = None

if NPN:
    START = 1
    STOP = 0
else:
    START = 0
    STOP = 1

# 自动获取温度传感器温度信息所在的文件位置
try:
    for each_dir in os.listdir('/sys/bus/w1/devices/'):
        if '28-' in each_dir:
            temp_path = '/sys/bus/w1/devices/'+each_dir+'/w1_slave'
except FileNotFoundError:
    print('Warning!: 没有检测到温度传感器！')


def get_gpu_temp():
    gpu_temp = commands.getoutput('/opt/vc/bin/vcgencmd measure_temp').replace('temp=', '').replace('\'C', '')
    return float(gpu_temp)


def get_env_temp():
    with open(temp_path, 'r') as temp_file:
        # 读取文件所有内容
        text = temp_file.read()
        # a7 01 4b 46 7f ff 09 10 e0 : crc=e0 YES
        # a7 01 4b 46 7f ff 09 10 e0 t=26437

        temp_line = text.split("\n")[1]
        # a7 01 4b 46 7f ff 09 10 e0 t=26437

        temperature_data = temp_line.split(" ")[9]
        # 't=26437'
        env_temperature = float(temperature_data[2:])
        # 26437
        env_temperature = env_temperature / 1000
        # 26.437
        # print(temperature)
        return env_temperature


def main():
    count = 0
    env_temp = None
    temp_diff = None
    count_per_min = 60/time_interval
    while True:
        gpu_temp_loop = get_gpu_temp()
        if temp_path is not None:
            env_temp = get_env_temp()
            temp_diff = gpu_temp_loop - env_temp

        if IS_LOG_FILE:
            try:
                if count <= count_per_min * 60 * log_file_duration:
                    fp = open(log_file_path, 'a')
                    if temp_diff is None:
                        fp.write('{} CPU temp: {}C\n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gpu_temp_loop))
                    else:
                        fp.write('{} CPUtemp: {}C, ENVtemp: {}C, DIFF: {}C\n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                                                     gpu_temp_loop, env_temp, temp_diff))
                    count += 1
                    fp.close()
                else:
                    fp = open(log_file_path, 'w')
                    fp.write('{} CPU temp: {}C\n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gpu_temp_loop))
                    count = 0
                    fp.close()
            except Exception as e:
                print('Error: {}-{}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e))

        if IS_LOG_CONSOLE:
            if temp_diff is None:
                print('{} CPU temp: {}C\n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gpu_temp_loop))
            else:
                print('{} CPUtemp: {}C, ENVtemp: {}C, DIFF: {}C\n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                                          gpu_temp_loop, env_temp, temp_diff))
        if temp_diff is None:
            if gpu_temp_loop > T_HIGH:
                GPIO.output(fan_pin, START)
            elif gpu_temp_loop < T_LOW:
                GPIO.output(fan_pin, STOP)
        else:
            if temp_diff > T_DIFF_HIGH:
                GPIO.output(fan_pin, START)
            elif temp_diff < T_DIFF_LOW:
                GPIO.output(fan_pin, STOP)
        time.sleep(time_interval)


if __name__ == '__main__':
    main()
