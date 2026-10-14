# QCL-Plugins · QCL-CE 插件市场

QCL-CE（Android 上的 Minecraft Java 启动器）的**资源型插件**目录。

- 🌐 **网页市场**：https://weeb123321.github.io/QCL-Plugins/
- 📦 **插件目录（数据库）**：`index.json`
- 📖 **格式规范**：`SCHEMA.md`
- ⬇️ **插件包**：全部挂在 Release [`plugins`](../../releases/tag/plugins) 下，国内可走 `gh-proxy.com` 镜像

## 插件是什么

一个 zip，里面是一份 `plugin.json` 加一个资源目录。**不含任何可执行代码** ——
生成脚本会拒绝 `.dex` / `.jar` / `.so` / `.apk`，所以不存在「插件里藏代码」的可能。

| 类型 | 内容 | 装到哪里 |
|---|---|---|
| `control` | 一整套控键布局（`info.json` + 4 个布局 json） | 启动器 `<filesDir>/control/<布局名>/` |
| `layout` | 界面排版（`qcl_layout.json`） | 启动器设置里的 `qcl_layout.json` |

> 启动器**没有插件运行时**（不加载代码、不申请新权限）。这是刻意的：
> 在 Android 上动态加载外部代码既有兼容问题也有安全风险。所以 v1 只分发资源。

## 目录结构

```
index.html          市场网页（GitHub Pages 首页）
index.json          插件目录，由 tools/build_index.py 生成 —— 不要手改
theme.js            主题切换（与启动器官网同一份）
SCHEMA.md           插件格式规范（契约）
plugins-src/<id>/   插件源：plugin.json + <target>/
dist/               打包产物（<id>-<version>.zip）
tools/
  make_plugins.py   控键 / 排版插件生成器（从启动器内置 Default 派生，防四个文件漂移）
  build_index.py    打包 + 生成 index.json（算 size 与 sha256）
```

## 加一个插件

```bash
# 1) 在 plugins-src/<id>/ 放 plugin.json 与 <target>/
# 2) 打包并重算目录
python tools/build_index.py
# 3) 提交 PR；维护者打 tag plugins、建 Release 上传 dist/*.zip，再推 index.json
```

`build_index.py` 会做这些校验，不通过就直接退出：

- `id` 只允许小写字母 / 数字 / 连字符，且必须与目录名一致
- `version` 必须是 `MAJOR.MINOR.PATCH`
- zip 根**只能**有一个文件（`plugin.json`）+ **恰好一个**目录，目录名必须等于 `target`
- 资源目录里出现 `.dex` / `.jar` / `.so` / `.apk` / `.class` → 拒收
- `description` 不超过 120 字

## 为什么 zip 根就是资源目录

启动器里**已经存在**的「控键布局 → 导入」流程会解压 zip、取第一个目录当布局名，
并要求它等于 `info.json` 的 `name`。照这个结构打包，
**同一个 zip 既能被市场一键安装，也能被老流程手动导入** —— 多放一层 `payload/` 就会选错目录。

## 许可

插件包默认 CC-BY-4.0（可在 `plugin.json` 里改）。工具脚本与网页同 QCL-CE，GPL-3.0。

by WEEB123321
