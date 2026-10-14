# -*- coding: utf-8 -*-
"""
打包 plugins-src/ 下的每个插件为 dist/<id>-<version>.zip，并生成 index.json（市场目录）。

★ 为什么 index.json 由脚本生成而不是手写：
  size / sha256 必须和真实 zip 一致，手写一定会漂移。
  启动器要拿 sha256 校验下载结果，错一个字符就等于装不上。

用法：python tools/build_index.py [仓库根目录]
"""
import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "plugins-src")
DIST_DIR = os.path.join(ROOT, "dist")

OWNER = "WEEB123321"
REPO = "QCL-Plugins"
RELEASE_TAG = "plugins"          # 所有插件包都挂在这一个 Release 下

ALLOWED_TYPES = {"control", "layout"}
# ★ 资源型插件只允许这些扩展名。出现 dex/jar/so/apk 一律拒收 —— 不做代码加载。
ALLOWED_EXT = {".json", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md"}
FORBIDDEN_EXT = {".dex", ".jar", ".so", ".apk", ".class", ".aar", ".zip"}

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
VER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def die(msg):
    print("!! " + msg)
    sys.exit(1)


def check_manifest(pid, m):
    for k in ("schemaVersion", "id", "name", "version", "type", "author",
              "description", "minLauncherVersionCode", "target"):
        if k not in m:
            die("%s: plugin.json 缺字段 %s" % (pid, k))
    if m["schemaVersion"] != 1:
        die("%s: schemaVersion 必须是 1" % pid)
    if m["id"] != pid:
        die("%s: plugin.json 里的 id(%s) 与目录名不一致" % (pid, m["id"]))
    if not ID_RE.match(m["id"]):
        die("%s: id 不合法（只允许小写字母/数字/连字符）" % pid)
    if not VER_RE.match(str(m["version"])):
        die("%s: version 必须是 MAJOR.MINOR.PATCH" % pid)
    if m["type"] not in ALLOWED_TYPES:
        die("%s: type=%s 不在允许列表 %s" % (pid, m["type"], sorted(ALLOWED_TYPES)))
    if len(m["description"]) > 120:
        die("%s: description 太长（%d 字）" % (pid, len(m["description"])))
    return m


def scan_payload(pid, plugin_dir, manifest):
    """检查 zip 根结构：plugin.json + 恰好一个名为 target 的目录；返回文件数。

    ★ 这条约束不是为了好看，是为了**兼容启动器里已有的手动导入**：
      ControllerManagerDialog 解压后取「第一个目录」当布局名，并要求它 == info.json 的 name。
      多一个目录就会选错 ✗
    """
    entries = [e for e in sorted(os.listdir(plugin_dir)) if not e.startswith(".")]
    dirs = [e for e in entries if os.path.isdir(os.path.join(plugin_dir, e))]
    files = [e for e in entries if os.path.isfile(os.path.join(plugin_dir, e))]

    if files != ["plugin.json"]:
        die("%s: zip 根只能有 plugin.json 一个文件，实际 %s" % (pid, files))
    if len(dirs) != 1:
        die("%s: zip 根必须恰好有一个目录（target），实际 %s" % (pid, dirs))
    if dirs[0] != manifest["target"]:
        die("%s: 目录名 %s 与 plugin.json 的 target(%s) 不一致" % (pid, dirs[0], manifest["target"]))

    n = 0
    for dirpath, _dirs, fs in os.walk(os.path.join(plugin_dir, dirs[0])):
        for f in fs:
            ext = os.path.splitext(f)[1].lower()
            if ext in FORBIDDEN_EXT:
                die("%s: 出现 %s —— 资源型插件不允许携带可执行文件" % (pid, f))
            if ext not in ALLOWED_EXT:
                die("%s: 出现不认识的扩展名 %s" % (pid, f))
            n += 1
    if n == 0:
        die("%s: target 目录是空的" % pid)
    return n


def make_zip(pid, plugin_dir, out_path):
    """把 plugin.json + target 目录打进 zip（UTF-8 文件名）。"""
    files = [("plugin.json", os.path.join(plugin_dir, "plugin.json"))]
    for entry in sorted(os.listdir(plugin_dir)):
        if entry.startswith(".") or entry == "plugin.json":
            continue
        full = os.path.join(plugin_dir, entry)
        if os.path.isfile(full):
            continue
        for dirpath, _dirs, fs in os.walk(full):
            for f in sorted(fs):
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, plugin_dir).replace(os.sep, "/")
                files.append((rel, p))

    files.sort(key=lambda x: x[0])
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, full in files:
            zi = zipfile.ZipInfo(rel, date_time=(2026, 10, 14, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(full, "rb") as fh:
                z.writestr(zi, fh.read())
    return len(files)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.isdir(SRC_DIR):
        die("找不到 plugins-src/")
    os.makedirs(DIST_DIR, exist_ok=True)

    plugins = []
    for pid in sorted(os.listdir(SRC_DIR)):
        plugin_dir = os.path.join(SRC_DIR, pid)
        if not os.path.isdir(plugin_dir):
            continue
        mpath = os.path.join(plugin_dir, "plugin.json")
        if not os.path.isfile(mpath):
            die("%s: 缺 plugin.json" % pid)
        with open(mpath, encoding="utf-8") as f:
            m = check_manifest(pid, json.load(f))
        nfiles = scan_payload(pid, plugin_dir, m)

        zip_name = "%s-%s.zip" % (m["id"], m["version"])
        zip_path = os.path.join(DIST_DIR, zip_name)
        nzip = make_zip(pid, plugin_dir, zip_path)

        size = os.path.getsize(zip_path)
        digest = sha256_of(zip_path)

        url = "https://github.com/%s/%s/releases/download/%s/%s" % (OWNER, REPO, RELEASE_TAG, zip_name)
        plugins.append({
            "id": m["id"],
            "name": m["name"],
            "version": m["version"],
            "type": m["type"],
            "author": m["author"],
            "description": m["description"],
            "tags": m.get("tags", []),
            "license": m.get("license", "CC-BY-4.0"),
            "minLauncherVersionCode": m["minLauncherVersionCode"],
            "updatedAt": m.get("updatedAt", ""),
            "size": size,
            "sha256": digest,
            "download": {
                "url": url,
                "mirror": "https://gh-proxy.com/" + url,
            },
        })
        print("打包 %-18s %6d B  %d 文件（zip 内 %d 项）" % (m["id"], size, nfiles, nzip))

    plugins.sort(key=lambda p: (p["type"], p["id"]))
    index = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "minLauncherVersionCode": min([p["minLauncherVersionCode"] for p in plugins]) if plugins else 0,
        "count": len(plugins),
        "plugins": plugins,
    }
    out = os.path.join(ROOT, "index.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("已写 index.json：%d 个插件" % len(plugins))


if __name__ == "__main__":
    main()
