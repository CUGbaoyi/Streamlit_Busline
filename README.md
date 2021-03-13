# Streamlit Busline

本软件是基于Streamlit的公交线路抓取系统，使用十分方便，只需输入gaode api的key和待抓取的城市名即可抓取公交线路数据，并下载站点和线路的shapefile到本地

## Installation
首先使用pip安装相关依赖

```python
pip install requests_html geopandas folium pypinyin faker streamlit_folium
```

## Usage
直接使用
```python
streamlit run streamlit_busline.py
```
一共有两种抓取方式

1. 上传站点文件抓取
2. 根据["网站"](https://bus.mapbar.com/beijing/xianlu/) 自动抓取

## Example
![](https://i.loli.net/2021/03/13/mujPs9CIlcLTho1.png)
![](https://i.loli.net/2021/03/13/qYVOeCIF6KaPBvS.png)