#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: baoyi
# Datetime: 2021/3/12 19:40

import time
import folium
import requests
import pandas as pd
import geopandas as gpd
import numpy as np
import streamlit as st

from faker import Factory
from pypinyin import lazy_pinyin
from requests_html import HTMLSession
from collections import defaultdict
from shapely.geometry import Point, LineString
from streamlit_folium import folium_static
from trans import gcj02_to_wgs84


def transPoint(coords: str):
    """
    将gcj02转成utf-8
    :param coords: 
    :return: 
    """
    result = []
    p = coords.split(";")
    for _ in p:
        lng, lat = float(_.split(',')[0]), float(_.split(',')[1])
        t_lng, t_lat = gcj02_to_wgs84(lng, lat)
        result.append(tuple([t_lat, t_lng]))

    return result


def get_bus_name(city):
    """
    根据城市名获取公交站点名字
    :param city:
    :return:
    """
    session = HTMLSession()
    name_list = []
    py_city = "".join(lazy_pinyin(city))

    url = f"https://bus.mapbar.com/{py_city}/xianlu/"
    st.markdown(f"从网站 {url} 获取站点信息", unsafe_allow_html=True)
    r = session.get(url)
    dd = r.html.find('dd')
    for d in dd:
        name = d.find('a[target=_blank]')
        for n in name:
            name_list.append(n.text)

    return name_list


def stations_to_geopandas(busstops: dict, line_id: str):
    """
    整理站点信息
    :param busstops:
    :return:
    """
    stops_list = defaultdict(list)
    for stops in busstops:
        lng, lat = list(map(float, stops['location'].split(',')))
        stops_list['line_id'].append(line_id)
        stops_list['bus_id'].append(stops['id'])
        stops_list['name'].append(stops['name'])
        stops_list['sequence'].append(stops['sequence'])
        stops_list['X'].append(gcj02_to_wgs84(lng, lat)[0])
        stops_list['Y'].append(gcj02_to_wgs84(lng, lat)[1])

    stop_df = pd.DataFrame(stops_list)
    geometry = [Point(xy) for xy in zip(stop_df.X, stop_df.Y)]
    geo_df = gpd.GeoDataFrame(stop_df, geometry=geometry)
    return geo_df


def get_bus_line(key, cityname, keywords):
    """
    获取公交线路信息
    :param key: gaode的key
    :param cityname:
    :param keywords:
    :return:
    """
    url = f'https://restapi.amap.com/v3/bus/linename?&extensions=all&key={key}&output=json&city={cityname}&offset=1&keywords={keywords}'
    j = requests.get(url).json()
    busline = j['buslines'][0]

    bus_info = {
        'id': [busline['id']],
        'type': [str(busline['type'])],
        'name': [busline['name']],
        'start_stop': [busline['start_stop']],
        'end_stop': [busline['end_stop']],
        'start_time': [str(busline['start_time'])],
        'end_time': [str(busline['end_time'])],
        'distance': [busline['distance']],
        'basic_price': [str(busline['basic_price'])],
        'total_price': [str(busline['total_price'])],
        'busstops_number': [len(busline['busstops'])]
    }
    return pd.DataFrame(bus_info), transPoint(busline['polyline']), stations_to_geopandas(busline['busstops'],
                                                                                          busline['id'])


def get_main(city, key, data):
    """
    主函数
    :return:
    """
    faker = Factory.create()
    stop_df_list = []
    line_df_list = []

    length = len(data)
    with st.spinner(f"一共有{length}条公交线路"):
        time.sleep(2)

    # 初始化进度条文字信息
    status_txt = st.empty()
    # 初始化进度条
    pb = st.progress(0)
    df, points, stop_df = get_bus_line(key, city, data[0])

    # 保存站点信息
    stop_df_list.append(stop_df)
    line_df_list.append(df)

    # 初始化dataframe
    tb_table = st.dataframe(df)
    # 初始化folium地图
    m = folium.Map(location=[np.mean([i[0] for i in points]), np.mean([i[1] for i in points])], zoom_start=10)

    for index, line in enumerate(data[1:]):
        pb.progress((index + 2) * 100 // length)
        status_txt.text(
            f"正在抓取公交 {line} {index + 2} / {length}"
        )
        try:
            df, points, stop_df = get_bus_line(key, city, line)

            # 保存站点信息
            stop_df_list.append(stop_df)
            line_df_list.append(df)

            # 往st.dataframe 添加行数据
            tb_table.add_rows(df)
            # 往地图内添加公交线路，颜色随机
            folium.PolyLine(points, color=faker.hex_color(), weight=4, opacity=1, popup=f'{line}',
                            tooltip=f'{line}').add_to(m)
        except Exception as e:
            # 如果线路不存在则提示并跳过
            print(e)
            with st.spinner(f'**公交线 {line}, 暂时抓取失败，已跳过!**'):
                time.sleep(2)

    # 加载folium地图，展示公交线网数据
    folium_static(m)

    # 合并所有站点数据,构建站点dataframe
    all_stop_df = pd.concat(stop_df_list)
    all_stop_df = gpd.GeoDataFrame(all_stop_df, geometry='geometry')
    all_stop_df.crs = "EPSG:4326"
    # 导出站点文件
    all_stop_df.to_file(f"{city}_站点_{time.time()}", encoding='utf-8')
    st.success(
        f"**{city}公交站点shapefile数据已经保存在当前文件夹下的 '{city}_站点_{time.time()}' **"
    )

    all_line_df = pd.concat(line_df_list)
    geo_line = all_stop_df.groupby('line_id')['geometry'].apply(lambda x: LineString(x.tolist()))
    merge_df = pd.merge(all_line_df, geo_line, left_on='id', right_on='line_id')
    merge_df = gpd.GeoDataFrame(merge_df, geometry='geometry')
    merge_df.crs = "EPSG:4326"
    merge_df.to_file(f"{city}_线路_{time.time()}", encoding='utf-8')
    st.success(
        f"**{city}公交线路shapefile数据已经保存在当前文件夹下的 '{city}_线路_{time.time()}' **"
    )


if __name__ == '__main__':
    STYLE = """
    <style>
    img {
        max-width: 100%;
    }
    </style>
    """
    st.title("城市公交线路可视化及下载系统")
    st.markdown("输入城市名和高德API key 即可抓取公交线路信息，可视化，自动下载到本地(wgs84坐标系)")
    st.markdown(STYLE, unsafe_allow_html=True)

    # 输入框
    city = st.text_input("输入城市名")
    # 输入框
    key = st.text_input("输入高德api key")

    # 选择框
    option = st.selectbox(
        "选择抓取模式",
        ['1. 手动上传站点信息', '2. 自动从网站获取站点信息']
    )

    if option == '1. 手动上传站点信息':
        file = st.file_uploader("Upload file", type='csv')
        show_file = st.empty()
        if not file:
            show_file.info("Please upload a file of type: csv")
        else:
            st.subheader("公交数据DataFrame")
            data = pd.read_csv(file, header=None)[0].tolist()
            # 获取数据
            get_main(city, key, data)
    elif option == '2. 自动从网站获取站点信息':
        try:
            with st.spinner(f'**3秒后开始抓取**'):
                time.sleep(3)
            data = get_bus_name(city)
            # 获取数据
            get_main(city, key, data)
        except Exception as e:
            print(e)
            with st.spinner(f'**{city} 获取失败，请手动获取**'):
                time.sleep(2)
