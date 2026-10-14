# -*- coding: utf-8 -*-
"""
从 QCL 内置的 control/Default 派生出控键布局插件，并手写两个界面排版插件。

★ 为什么用脚本而不是手改 JSON：
  控键布局是 4 个文件、每个文件里几十个按钮，每个按钮各带一份 buttonStyle。
  手改必然漏改、且四个文件之间会漂移。脚本保证「同一插件内所有布局文件的样式一致」。

用法：
  python tools/make_plugins.py <Default 目录> [输出目录]
  例：python tools/make_plugins.py "D:/A/.../QCL/src/main/assets/control/Default"
"""
import json
import os
import shutil
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else None
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins-src")

if not SRC or not os.path.isdir(SRC):
    sys.exit("用法: python tools/make_plugins.py <Default 目录> [输出目录]")

LAYOUT_FILES = ["initial_layout.json", "game_layout.json",
                "game_keyboard_layout.json", "full_keyboard_layout.json"]

MIN_VER = 1742


# ---------------------------------------------------------------- 颜色工具

def set_alpha(color, alpha):
    """把 #AARRGGBB / #RRGGBB 的 alpha 换成 alpha（0-255）。认不出来就原样返回。"""
    if not isinstance(color, str) or not color.startswith("#"):
        return color
    h = color[1:]
    if len(h) == 8:
        return "#%02X%s" % (alpha, h[2:].upper())
    if len(h) == 6:
        return "#%02X%s" % (alpha, h.upper())
    return color


def scale_size(obj, k):
    """缩放 {absoluteSize, object, percentSize} 里的尺寸字段。"""
    if not isinstance(obj, dict):
        return
    for key in ("absoluteSize", "percentSize"):
        v = obj.get(key)
        if isinstance(v, (int, float)) and v:
            obj[key] = round(v * k, 4)


# ---------------------------------------------------------------- 样式变换

def transform_style(st, spec):
    """对一份 buttonStyle / rockerStyle 施加变换。spec 是 {字段: 函数}。"""
    for key, fn in spec.items():
        if key in st:
            st[key] = fn(st[key])


# 三个控键插件的样式配方
RECIPES = {
    # ---- 极简半透明：把底色和描边的 alpha 压下去，少挡画面 ----
    "control-minimal": {
        "name": "极简半透明控键",
        "desc": "把默认控键的底色和描边透明度调低，游戏画面挡得更少。手感位置完全不变。",
        "tags": ["控键", "透明", "极简"],
        "target": "极简半透明",
        "btn": {
            "fillColor": lambda c: set_alpha(c, 0x26),
            "fillColorPress": lambda c: set_alpha(c, 0x45),
            "strokeColor": lambda c: set_alpha(c, 0x1A),
            "strokeColorPress": lambda c: set_alpha(c, 0x33),
        },
        "rocker": {
            "fillColor": lambda c: set_alpha(c, 0x1A),
            "fillColorPress": lambda c: set_alpha(c, 0x33),
            "strokeColor": lambda c: set_alpha(c, 0x33),
            "strokeColorPress": lambda c: set_alpha(c, 0x4D),
            "pointerColor": lambda c: set_alpha(c, 0xCC),
            "pointerColorPress": lambda c: set_alpha(c, 0x99),
        },
    },

    # ---- 大按钮易按：字号 + 圆角 + 整体尺寸一起放大 ----
    "control-bigbtn": {
        "name": "大按钮 · 易按",
        "desc": "把控键整体放大：字号 ×1.35、圆角加大、按钮和摇杆都放大约两成。适合小屏或手指粗。",
        "tags": ["控键", "大按钮", "易用"],
        "target": "大按钮",
        "btn": {
            "textSize": lambda v: round(v * 1.35, 1),
            "textSizePress": lambda v: round(v * 1.35, 1),
            "cornerRadius": lambda v: round(v * 1.4, 1),
            "cornerRadiusPress": lambda v: round(v * 1.4, 1),
        },
        "rocker": {
            "cornerRadius": lambda v: round(v * 1.15, 1),
            "cornerRadiusPress": lambda v: round(v * 1.15, 1),
        },
        "btn_size_k": 1.2,      # height
        "rocker_size_k": 1.15,  # size
    },

    # ---- 高对比描边：加粗描边、提高不透明度 ----
    "control-contrast": {
        "name": "高对比描边控键",
        "desc": "描边加粗到两倍、底色更实，暗背景和明亮场景下都能一眼看清按键边界。",
        "tags": ["控键", "高对比", "描边"],
        "target": "高对比",
        "btn": {
            "strokeWidth": lambda v: round(v * 2.0, 1),
            "strokeWidthPress": lambda v: round(v * 1.75, 1),
            "strokeColor": lambda c: set_alpha(c, 0xAA),
            "strokeColorPress": lambda c: set_alpha(c, 0xCC),
            "fillColor": lambda c: set_alpha(c, 0x99),
            "fillColorPress": lambda c: set_alpha(c, 0xB3),
        },
        "rocker": {
            "strokeWidth": lambda v: round(v * 2.0, 1),
            "strokeWidthPress": lambda v: round(v * 1.6, 1),
            "strokeColor": lambda c: set_alpha(c, 0xAA),
            "strokeColorPress": lambda c: set_alpha(c, 0xCC),
        },
    },
}


def build_control_plugin(pid, recipe, out_root):
    # ★ 为什么布局目录直接放在 zip 根（而不是 payload/control/ 下）：
    #   启动器里已有的「控键布局 → 导入」流程（ControllerManagerDialog）要求
    #   zip 根下就是布局目录、且目录名 == info.json 的 name。
    #   照这个结构打包 ⇒ 同一个 zip 既能被市场一键安装，也能被老流程手动导入 ✓
    dest = os.path.join(out_root, pid, recipe["target"])
    os.makedirs(dest, exist_ok=True)

    for fn in LAYOUT_FILES:
        src_path = os.path.join(SRC, fn)
        if not os.path.isfile(src_path):
            continue
        with open(src_path, encoding="utf-8") as f:
            data = json.load(f)

        for b in data.get("baseButtonList", []):
            if isinstance(b.get("buttonStyle"), dict):
                transform_style(b["buttonStyle"], recipe["btn"])
            if recipe.get("btn_size_k"):
                scale_size(b.get("height"), recipe["btn_size_k"])
                scale_size(b.get("width"), recipe["btn_size_k"])

        for r in data.get("baseRockerViewList", []):
            if isinstance(r.get("rockerStyle"), dict):
                transform_style(r["rockerStyle"], recipe["rocker"])
            if recipe.get("rocker_size_k"):
                scale_size(r.get("size"), recipe["rocker_size_k"])

        with open(os.path.join(dest, fn), "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    # info.json 是控键布局自己的元数据（启动器读它显示名字/作者），必须改写
    info = {
        "author": "WEEB123321",
        "describe": recipe["desc"] + "（QCL-CE 插件市场 · " + pid + "）",
        "launcherVersion": 1,
        "name": recipe["target"],
        "versionName": "1.0",
    }
    with open(os.path.join(dest, "info.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
        f.write("\n")

    write_manifest(out_root, pid, recipe["name"], recipe["desc"], recipe["tags"],
                   "control", recipe["target"])


# ---------------------------------------------------------------- 界面排版插件

LAYOUT_PLUGINS = [
    {
        "id": "layout-simple",
        "name": "主页 · 极简",
        "desc": "隐藏「联机 / 大厅 / 实验室」三个入口，主页只留账号、版本、下载、设置。排版随时可恢复默认。",
        "tags": ["界面", "极简", "主页"],
        "target": "main",
        "rules": {
            "start_ui_version_list": {"order": 0, "visible": True, "w": 0, "h": 0},
            "start_ui_download": {"order": 1, "visible": True, "w": 0, "h": 0},
            "start_ui_game_manager": {"order": 2, "visible": True, "w": 0, "h": 0},
            "start_ui_account": {"order": 3, "visible": True, "w": 0, "h": 0},
            "start_ui_setting": {"order": 4, "visible": True, "w": 0, "h": 0},
            "start_ui_multi_player": {"order": 90, "visible": False, "w": 0, "h": 0},
            "start_ui_lobby": {"order": 91, "visible": False, "w": 0, "h": 0},
            "start_ui_lab": {"order": 92, "visible": False, "w": 0, "h": 0},
        },
    },
    {
        "id": "layout-focus",
        "name": "主页 · 游戏优先",
        "desc": "把「版本列表」和「下载」提到最前，账号与设置沉到后面。常切版本的人少点几下。",
        "tags": ["界面", "排序", "主页"],
        "target": "main",
        "rules": {
            "start_ui_version_list": {"order": 0, "visible": True, "w": 0, "h": 0},
            "start_ui_download": {"order": 1, "visible": True, "w": 0, "h": 0},
            "start_ui_multi_player": {"order": 2, "visible": True, "w": 0, "h": 0},
            "start_ui_lobby": {"order": 3, "visible": True, "w": 0, "h": 0},
            "start_ui_lab": {"order": 4, "visible": True, "w": 0, "h": 0},
            "start_ui_game_manager": {"order": 5, "visible": True, "w": 0, "h": 0},
            "start_ui_account": {"order": 6, "visible": True, "w": 0, "h": 0},
            "start_ui_setting": {"order": 7, "visible": True, "w": 0, "h": 0},
        },
    },
]


def build_layout_plugin(p, out_root):
    # 与控键包同构：zip 根下就是 target 目录（layout 的 target = 页面 id，目前只有 main）
    dest = os.path.join(out_root, p["id"], p["target"])
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "qcl_layout.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"main": p["rules"]}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_manifest(out_root, p["id"], p["name"], p["desc"], p["tags"], "layout", p["target"])


# ---------------------------------------------------------------- 清单

def write_manifest(out_root, pid, name, desc, tags, ptype, target):
    manifest = {
        "schemaVersion": 1,
        "id": pid,
        "name": name,
        "version": "1.0.0",
        "type": ptype,
        "author": "WEEB123321",
        "description": desc,
        "tags": tags,
        "license": "CC-BY-4.0",
        "minLauncherVersionCode": MIN_VER,
        "updatedAt": "2026-10-14",
        "target": target,
    }
    path = os.path.join(out_root, pid, "plugin.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    for pid, recipe in RECIPES.items():
        d = os.path.join(OUT, pid)
        if os.path.isdir(d):
            shutil.rmtree(d)
        build_control_plugin(pid, recipe, OUT)
        print("生成控键插件:", pid)

    for p in LAYOUT_PLUGINS:
        d = os.path.join(OUT, p["id"])
        if os.path.isdir(d):
            shutil.rmtree(d)
        build_layout_plugin(p, OUT)
        print("生成排版插件:", p["id"])


if __name__ == "__main__":
    main()
