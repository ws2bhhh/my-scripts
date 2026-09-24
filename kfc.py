import argparse
import concurrent.futures
import json
import math
import os
import re
import threading
import time
import urllib.request

# =================================================================
# 城市代码表（kfc-api 仓库快照，371 个市/州；可自行增补）
# =================================================================

CITIES = {
    "景德镇": "360200",
    "周口": "411600",
    "枣庄": "370400",
    "泰安": "370900",
    "深圳": "440300",
    "九江": "360400",
    "黄山": "341000",
    "长治": "140400",
    "定西": "621100",
    "唐山": "130200",
    "邢台": "130500",
    "抚州": "361000",
    "泉州": "350500",
    "渭南": "610500",
    "大同": "140200",
    "郑州": "410100",
    "延安": "610600",
    "西安": "610100",
    "泸州": "510500",
    "抚顺": "210400",
    "牡丹江": "231000",
    "乐山": "511100",
    "宝鸡": "610300",
    "鄂州": "420700",
    "新乡": "410700",
    "丹东": "210600",
    "临汾": "141000",
    "淮南": "340400",
    "临沂": "371300",
    "阜阳": "341200",
    "潮州": "445100",
    "伊犁哈萨克自治州": "654000",
    "南京": "320100",
    "哈尔滨": "230100",
    "贵港": "450800",
    "保定": "130600",
    "重庆": "500100",
    "汕尾": "441500",
    "通辽": "150500",
    "常德": "430700",
    "张家界": "430800",
    "大理白族自治州": "532900",
    "驻马店": "411700",
    "长沙": "430100",
    "太原": "140100",
    "六盘水": "520200",
    "绥化": "231200",
    "宜春": "360900",
    "白银": "620400",
    "益阳": "430900",
    "阿坝藏族羌族自治州": "513200",
    "邵阳": "430500",
    "德宏傣族景颇族自治州": "533100",
    "红河哈尼族彝族自治州": "532500",
    "张家口": "130700",
    "榆林": "610800",
    "上饶": "361100",
    "烟台": "370600",
    "毕节": "520500",
    "玉林": "450900",
    "内江": "511000",
    "济南": "370100",
    "天津": "120100",
    "成都": "510100",
    "湖州": "330500",
    "玉树藏族自治州": "632700",
    "阿克苏地区": "652900",
    "厦门": "350200",
    "河池": "451200",
    "桂林": "450300",
    "黄冈": "421100",
    "吕梁": "141100",
    "黄南藏族自治州": "632300",
    "昭通": "530600",
    "日喀则": "540200",
    "喀什地区": "653100",
    "梧州": "450400",
    "甘孜藏族自治州": "513300",
    "武汉": "420100",
    "鄂尔多斯": "150600",
    "吉安": "360800",
    "邯郸": "130400",
    "普洱": "530800",
    "大连": "210200",
    "昆明": "530100",
    "扬州": "321000",
    "阜新": "210900",
    "济宁": "370800",
    "福州": "350100",
    "三明": "350400",
    "荆州": "421000",
    "湘西土家族苗族自治州": "433100",
    "德阳": "510600",
    "廊坊": "131000",
    "拉萨": "540100",
    "楚雄彝族自治州": "532300",
    "北京": "110100",
    "金华": "330700",
    "北屯": "659005",
    "百色": "451000",
    "杭州": "330100",
    "吴忠": "640300",
    "十堰": "420300",
    "德州": "371400",
    "石家庄": "130100",
    "南充": "511300",
    "亳州": "341600",
    "和田地区": "653200",
    "淮安": "320800",
    "昆玉": "659009",
    "茂名": "440900",
    "无锡": "320200",
    "吐鲁番": "650400",
    "青岛": "370200",
    "澳门特别行政区": "820000",
    "陇南": "621200",
    "宁波": "330200",
    "韶关": "440200",
    "锡林郭勒盟": "152500",
    "山南": "540500",
    "沈阳": "210100",
    "三亚": "460200",
    "铜川": "610200",
    "阳泉": "140300",
    "承德": "130800",
    "通化": "220500",
    "本溪": "210500",
    "赣州": "360700",
    "温州": "330300",
    "宜宾": "511500",
    "漯河": "411100",
    "雅安": "511800",
    "襄阳": "420600",
    "阿勒泰地区": "654300",
    "安康": "610900",
    "衡水": "131100",
    "湘潭": "430300",
    "许昌": "411000",
    "朔州": "140600",
    "宣城": "341800",
    "忻州": "140900",
    "齐齐哈尔": "230200",
    "甘南藏族自治州": "623000",
    "林芝": "540400",
    "蚌埠": "340300",
    "果洛藏族自治州": "632600",
    "保山": "530500",
    "赤峰": "150400",
    "萍乡": "360300",
    "恩施土家族苗族自治州": "422800",
    "苏州": "320500",
    "河源": "441600",
    "佛山": "440600",
    "郴州": "431000",
    "商洛": "611000",
    "黔南布依族苗族自治州": "522700",
    "海西蒙古族藏族自治州": "632800",
    "咸阳": "610400",
    "南宁": "450100",
    "晋中": "140700",
    "黔东南苗族侗族自治州": "522600",
    "石嘴山": "640200",
    "台州": "331000",
    "鸡西": "230300",
    "泰州": "321200",
    "固原": "640400",
    "沧州": "130900",
    "衡阳": "430400",
    "安阳": "410500",
    "岳阳": "430600",
    "宁德": "350900",
    "上海": "310100",
    "伊春": "230700",
    "吉林": "220200",
    "鹤壁": "410600",
    "肇庆": "441200",
    "铁岭": "211200",
    "南通": "320600",
    "宿迁": "321300",
    "海南藏族自治州": "632500",
    "威海": "371000",
    "黄石": "420200",
    "天门": "429006",
    "哈密地区": "652200",
    "铜陵": "340700",
    "鹰潭": "360600",
    "黔西南布依族苗族自治州": "522300",
    "龙岩": "350800",
    "曲靖": "530300",
    "松原": "220700",
    "神农架林区": "429021",
    "洛阳": "410300",
    "那曲": "542400",
    "安庆": "340800",
    "中卫": "640500",
    "南阳": "411300",
    "澄迈县": "469023",
    "焦作": "410800",
    "梅州": "441400",
    "塔城地区": "654200",
    "玉溪": "530400",
    "聊城": "371500",
    "乌兰察布": "150900",
    "南平": "350700",
    "凉山彝族自治州": "513400",
    "广州": "440100",
    "嘉兴": "330400",
    "淄博": "370300",
    "张掖": "620700",
    "锦州": "210700",
    "商丘": "411400",
    "临沧": "530900",
    "防城港": "450600",
    "南昌": "360100",
    "怀化": "431200",
    "丽水": "331100",
    "滨州": "371600",
    "随州": "421300",
    "朝阳": "211300",
    "荆门": "420800",
    "娄底": "431300",
    "运城": "140800",
    "辽源": "220400",
    "绍兴": "330600",
    "乌鲁木齐": "650100",
    "广元": "510800",
    "延边朝鲜族自治州": "222400",
    "长春": "220100",
    "云浮": "445300",
    "常州": "320400",
    "白山": "220600",
    "漳州": "350600",
    "迪庆藏族自治州": "533400",
    "连云港": "320700",
    "黑河": "231100",
    "自贡": "510300",
    "晋城": "140500",
    "包头": "150200",
    "潍坊": "370700",
    "博尔塔拉蒙古自治州": "652700",
    "孝感": "420900",
    "宜昌": "420500",
    "昌都": "540300",
    "合肥": "340100",
    "双鸭山": "230500",
    "北海": "450500",
    "遵义": "520300",
    "鞍山": "210300",
    "濮阳": "410900",
    "宿州": "341300",
    "佳木斯": "230800",
    "咸宁": "421200",
    "银川": "640100",
    "丽江": "530700",
    "巴中": "511900",
    "营口": "210800",
    "酒泉": "620900",
    "鹤岗": "230400",
    "平顶山": "410400",
    "临夏回族自治州": "622900",
    "安顺": "520400",
    "琼中黎族苗族自治县": "469030",
    "徐州": "320300",
    "资阳": "512000",
    "株洲": "430200",
    "贵阳": "520100",
    "辽阳": "211000",
    "仙桃": "429004",
    "双河": "659007",
    "巴音郭楞蒙古自治州": "652800",
    "滁州": "341100",
    "海口": "460100",
    "呼伦贝尔": "150700",
    "湛江": "440800",
    "汕头": "440500",
    "开封": "410200",
    "广安": "511600",
    "盐城": "320900",
    "镇江": "321100",
    "淮北": "340600",
    "清远": "441800",
    "白城": "220800",
    "日照": "371100",
    "文山壮族苗族自治州": "532600",
    "东营": "370500",
    "西宁": "630100",
    "兰州": "620100",
    "遂宁": "510900",
    "可克达拉": "659008",
    "汉中": "610700",
    "永州": "431100",
    "盘锦": "211100",
    "克拉玛依": "650200",
    "保亭黎族苗族自治县": "469029",
    "攀枝花": "510400",
    "新余": "360500",
    "大兴安岭地区": "232700",
    "达州": "511700",
    "临高县": "469024",
    "揭阳": "445200",
    "石河子": "659001",
    "克孜勒苏柯尔克孜自治州": "653000",
    "柳州": "450200",
    "中山": "442000",
    "贺州": "451100",
    "武威": "620600",
    "莆田": "350300",
    "四平": "220300",
    "哈密": "650500",
    "铜仁": "520600",
    "钦州": "450700",
    "芜湖": "340200",
    "呼和浩特": "150100",
    "昌吉回族自治州": "652300",
    "胡杨河": "659010",
    "海东": "630200",
    "天水": "620500",
    "信阳": "411500",
    "庆阳": "621000",
    "辛集": "139002",
    "西双版纳傣族自治州": "532800",
    "衢州": "330800",
    "大庆": "230600",
    "菏泽": "371700",
    "平凉": "620800",
    "六安": "341500",
    "惠州": "441300",
    "秦皇岛": "130300",
    "来宾": "451300",
    "眉山": "511400",
    "嘉峪关": "620200",
    "海北藏族自治州": "632200",
    "崇左": "451400",
    "陵水黎族自治县": "469028",
    "七台河": "230900",
    "兴安盟": "152200",
    "济源": "419001",
    "阳江": "441700",
    "马鞍山": "340500",
    "阿里地区": "542500",
    "阿拉尔": "659002",
    "阿拉善盟": "152900",
    "葫芦岛": "211400",
    "五指山": "469001",
    "东方": "469007",
    "绵阳": "510700",
    "怒江傈僳族自治州": "533300",
    "巴彦淖尔": "150800",
    "香港特别行政区": "810000",
    "五家渠": "659004",
    "定安县": "469021",
    "文昌": "469005",
    "池州": "341700",
    "江门": "440700",
    "金昌": "620300",
    "琼海": "469002",
    "三门峡": "411200",
    "乌海": "150300",
    "珠海": "440400",
    "全省": "710000",
    "昌江黎族自治县": "469026",
    "图木舒克": "659003",
    "舟山": "330900",
    "万宁": "469006",
    "白沙黎族自治县": "469025",
    "儋州": "460400",
    "屯昌县": "469022",
    "东莞": "441900",
    "铁门关": "659006",
    "潜江": "429005",
    "乐东黎族自治县": "469027",
}
STORE_LIST_URL = "https://kfcoo.oreo20.cn/h5api/store/list"
STORE_LIST_HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
    "content-type": "application/json",
    "platform": "H5",
    "priority": "u=1, i",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0 Safari/537.36",
}


def fetch_store_list(city_code):
    """H5 分页接口拉取城市全部门店（含经纬度/营业时间），按 storecode 去重。"""
    stores, seen = {}, set()
    page = 1
    total_pages = 1
    while page <= total_pages:
        body = {
            "gbCityCode": city_code,
            "page": page,
            "keyword": "",
            "latitude": "",
            "longitude": "",
            "token": "",
            "uniacid": "1",
        }

        try:
            req = urllib.request.Request(
                STORE_LIST_URL,
                data=json.dumps(body).encode("utf-8"),
                headers=STORE_LIST_HEADERS,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                response = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print("[H5] 第 %d 页请求失败: %r" % (page, e))
            break
        if response.get("code") != 0:
            print(
                "[H5] 接口异常 code=%s msg=%s"
                % (response.get("code"), str(response.get("msg"))[:80])
            )
            break
        data = response.get("data") or {}
        total_pages = int(data.get("pages") or total_pages)
        for rec in data.get("records") or []:
            code = rec.get("storeCode")
            if not code or code in seen:
                continue
            seen.add(code)
            stores[code] = {
                "storecode": code,
                "storename": (rec.get("storeName") or "").replace("BBN", ""),
                "address": rec.get("address") or "",
                "lat": rec.get("lat"),
                "lng": rec.get("lng"),
                "phone": rec.get("phone") or "",
                "business": "%s-%s"
                % (rec.get("startTime") or "?", rec.get("endTime") or "?"),
            }
        page += 1
        time.sleep(0.3)
    return stores


# =====================================================================
# 磁盘缓存：仅门店列表
# =====================================================================
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".kfc_store_cache")


def load_store_cache(city_code, max_age_hours):
    if max_age_hours <= 0:
        return None
    cache_file = os.path.join(CACHE_DIR, "%s.json" % city_code)
    try:
        if not os.path.isfile(cache_file):
            return None
        with open(cache_file, "r", encoding="utf-8") as f:
            obj = json.load(f)
        age_hours = (time.time() - float(obj.get("fetched_ts", 0))) / 3600.0
        if age_hours > max_age_hours:
            print(
                "  ↳ 门店缓存已过期（%.1f 小时，超过 %s 小时）"
                % (age_hours, max_age_hours)
            )
            return None
        stores_list = obj.get("stores") or []
        stores = {s["storecode"]: s for s in stores_list if "storecode" in s}
        print("  ↳ 命中门店缓存：%d 家（%.1f 小时前拉取）" % (len(stores), age_hours))
        return stores
    except Exception as e:
        print("  ↳ 读取门店缓存失败：%r" % e)
        return None


def save_store_cache(city_code, stores):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        store_list = list(stores.values()) if isinstance(stores, dict) else list(stores)
        obj = {
            "city_code": city_code,
            "fetched_ts": time.time(),
            "source": "H5全门店分页列表",
            "total": len(store_list),
            "stores": store_list,
        }
        cache_file = os.path.join(CACHE_DIR, "%s.json" % city_code)
        tmp_file = cache_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp_file, cache_file)
        print("  ↳ 门店列表已缓存：%s（%d 家）" % (cache_file, len(store_list)))
    except Exception as e:
        print("  ↳ 写门店缓存失败：%r" % e)


BASE_URL = "https://rnorder.kfc.com.cn"
DEVICE_ID = "f50bff5b-a862-4cd9-9227-0bf0d90dc1091760437392797"

HEADERS = {
    "accept": "*/*",
    "cache-control": "no-cache",
    "user-agent": (
        "Android KFCSuperApp,6.28.0,rn-0.68.5,kfc-ordering-preorder,"
        "593f077a7d7db8e7eea0fdffb487d52ad55ae944,v190,12,HONOR LGE-AN10"
    ),
    "x-yumc-route-cell": "yumc3",
    "x-yumc-client-channel": "app",
    "x-yumc-client-deviceid": DEVICE_ID,
    "content-type": "application/json",
}

SESSION_ID = ""
_SESSION_LOCK = threading.Lock()


def ensure_session():
    global SESSION_ID
    if SESSION_ID:
        return SESSION_ID
    with _SESSION_LOCK:
        if SESSION_ID:
            return SESSION_ID
        payload = {
            "portalType": "APP",
            "channelName": "SuperApp",
            "channelId": "13_2",
            "brand": "KFC_PRE",
            "business": "preorder",
            "deviceId": DEVICE_ID,
            "clientVersion": "v5.924(593f077a)",
            "fversion": "250924",
            "versionNum": "5",
        }
        try:
            req = urllib.request.Request(
                BASE_URL + "/preorder-portal/api/v2/init/initSession",
                data=json.dumps(payload).encode("utf-8"),
                headers=HEADERS,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise RuntimeError("刷新 sessionId 失败: %r" % e)

        SESSION_ID = (data.get("data") or {}).get("sessionId")
        if not SESSION_ID:
            raise RuntimeError("刷新 sessionId 失败: %s" % str(data)[:200])
        return SESSION_ID


def get_menu(store_code):
    # 默认跳过附属门店：类似 “车速取车速取窗口” 这类门店.
    if not store_code or re.search(r"_[A-Za-z]?\d+$", store_code):
        return {}

    payload = {
        "portalType": "APP",
        "channelName": "SuperApp",
        "channelId": "13_2",
        "brand": "KFC_PRE",
        "business": "preorder",
        "deviceId": DEVICE_ID,
        "clientVersion": "v5.924(593f077a)",
        "fversion": "250924",
        "versionNum": "5",
        "store": {"storecode": store_code},
        "env": "wgb",
        "sessionId": ensure_session(),
    }
    try:
        req = urllib.request.Request(
            BASE_URL + "/preorder-portal/api/v2/menu/list",
            data=json.dumps(payload).encode("utf-8"),
            headers=HEADERS,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print("[get_menu] 门店 %s 请求失败: %r" % (store_code, e))
        return {}

    if data.get("code") == 100250550:  # 不在营业时段/打烊
        return {}
    return data.get("data") or {}


def search_menu(menu, keywords: list[str]):
    out = []

    # 提前转换关键词为小写，优化命中效率
    lower_keywords = [kw.lower() for kw in keywords]

    def hit(name):
        if not name:
            return False
        return any(keyword in name.lower() for keyword in lower_keywords)

    for item in menu.get("menuData", []):
        children = item["childClassList"] if "childClassList" in item else [item]

        # 场景 A: 顶级分类命中，将所有子类的产品全部压入一维数组 out 中
        if hit(item.get("nameCn")):
            for child in children:
                out.extend(child.get("menuList", []))
            continue

        # 场景 B: 顶级分类未命中，遍历子分类
        for child in children:
            if hit(child.get("nameCn")):
                # 子分类命中，将该分类下的产品列表直接拼接进 out
                out.extend(child.get("menuList", []))
            else:
                # 子分类未命中，仅将符合条件的产品逐个放入 out
                out.extend(
                    product
                    for product in child.get("menuList", [])
                    if hit(product.get("menuCn"))
                )
        pass
    return out


def check_stock(products: list):
    out = []
    for product in products:
        if product.get("saleFlag") == "Y":
            pass
        elif "会员产品校验失败" in (product.get("invalidReason") or ""):
            pass
        else:
            continue

        out.append(product.get("menuCn"))
    return out


# =====================================================================
# 输出
# =====================================================================
def annotate_distance(stores, ref_pt=None, ref_lat=None, ref_lng=None):
    """计算与参考门店的距离/与给定坐标的距离. 单位为km."""
    if isinstance(stores, dict):
        store_list = [dict(s) for s in stores.values()]
        store_map = stores
    else:
        store_list = [dict(s) for s in stores]
        store_map = {s.get("storecode"): s for s in stores if s.get("storecode")}

    target_lat, target_lng = None, None

    if ref_pt is not None:
        if isinstance(ref_pt, (list, tuple)) and len(ref_pt) == 2:
            try:
                target_lat, target_lng = float(ref_pt[0]), float(ref_pt[1])
            except (TypeError, ValueError):
                pass
        elif isinstance(ref_pt, str) and ref_pt in store_map:
            s_ref = store_map[ref_pt]
            if s_ref.get("lat") is not None and s_ref.get("lng") is not None:
                try:
                    target_lat, target_lng = float(s_ref["lat"]), float(s_ref["lng"])
                except (TypeError, ValueError):
                    pass

    if target_lat is None and ref_lat is not None and ref_lng is not None:
        try:
            target_lat, target_lng = float(ref_lat), float(ref_lng)
        except (TypeError, ValueError):
            pass

    for s in store_list:
        s_lat = s.get("lat")
        s_lng = s.get("lng")
        if (
            target_lat is not None
            and target_lng is not None
            and s_lat is not None
            and s_lng is not None
        ):
            try:
                lat1, lng1 = math.radians(target_lat), math.radians(target_lng)
                lat2, lng2 = math.radians(float(s_lat)), math.radians(float(s_lng))
                dlat = lat2 - lat1
                dlng = lng2 - lng1
                a = (
                    math.sin(dlat / 2) ** 2
                    + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
                )
                s["dist"] = round(2 * 6371.0 * math.asin(math.sqrt(a)), 2)
            except (TypeError, ValueError):
                s["dist"] = None
        else:
            s["dist"] = None

    if target_lat is not None and target_lng is not None:
        store_list.sort(
            key=lambda x: (x["dist"] is None, x["dist"] or 0.0), reverse=True
        )
    else:
        store_list.sort(key=lambda x: str(x.get("storecode", "")), reverse=True)

    return store_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KFC 门店菜单与库存检查")
    parser.add_argument("city", nargs="?", default="北京", help="城市名")
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="关键词，可多次指定",
    )
    parser.add_argument("--threads", type=int, default=8, help="并发线程数（默认：8）")
    parser.add_argument(
        "--cache-hours",
        type=float,
        default=24.0,
        help="缓存有效期(小时)（默认：24）",
    )
    parser.add_argument("--refresh", action="store_true", help="强制刷新门店缓存")
    parser.add_argument("--ref", default="", help="参照门店代码，如 GZ4400")
    parser.add_argument("--ref-lat", type=float, help="参照点纬度")
    parser.add_argument("--ref-lng", type=float, help="参照点经度")
    parser.add_argument(
        "--all",
        action="store_true",
        help="显示所有门店（包括无货/未命中的门店）",
    )
    args = parser.parse_args()

    city_code = CITIES.get(args.city)
    if not city_code:
        print("[错误] 未知城市: %s" % args.city)
        exit(1)

    print(
        "[信息] 城市: %s (%s)  关键词: %s"
        % (args.city, city_code, "/".join(args.keyword))
    )

    stores = None
    if not args.refresh:
        stores = load_store_cache(city_code, args.cache_hours)

    if not stores:
        print("[信息] 拉取城市门店列表...")
        stores = fetch_store_list(city_code)
        if stores and args.cache_hours > 0:
            save_store_cache(city_code, stores)

    if not stores:
        print("[警告] 未找到任何门店。")
        exit(0)

    # 滤掉附属门店
    filtered_stores = {
        code: st
        for code, st in stores.items()
        if not re.search(r"_[A-Za-z]?\d+$", code)
    }
    print(
        "[信息] 共有 %d 家主门店参与检查 (已跳过 %d 家附属门店)"
        % (len(filtered_stores), len(stores) - len(filtered_stores))
    )

    # 多线程查询菜单与检查库存
    results = {}

    def inspect_store(code):
        st = dict(filtered_stores[code])
        menu = get_menu(code)
        matched_products = search_menu(menu, args.keyword)
        stock_items = check_stock(matched_products)
        st["matched_products"] = matched_products
        st["stock_items"] = stock_items
        return code, st

    print("[信息] 开始并发查询菜单 (线程数: %d)..." % args.threads)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(inspect_store, code) for code in filtered_stores]
        for future in concurrent.futures.as_completed(futures):
            code, st = future.result()
            results[code] = st

    # 标注距离并排序
    annotated = annotate_distance(
        results,
        ref_pt=args.ref if args.ref else None,
        ref_lat=args.ref_lat,
        ref_lng=args.ref_lng,
    )

    # 打印结果
    print("=" * 80)
    in_stock_count = 0
    for st in annotated:
        stock_items = st.get("stock_items", [])
        dist_str = ("  %5.2fkm" % st["dist"]) if st.get("dist") is not None else ""
        if stock_items:
            in_stock_count += 1
            print(
                "[有货] %-10s %-20s %s 有货: %s"
                % (
                    st["storecode"],
                    st["storename"][:20],
                    dist_str,
                    ", ".join(stock_items),
                )
            )
        elif args.all:
            print(
                "[无货] %-10s %-20s %s 无货/打烊"
                % (st["storecode"], st["storename"][:20], dist_str)
            )

    print("=" * 80)
    print("汇总: 检查 %d 家门店 | 有货门店 %d 家" % (len(annotated), in_stock_count))
