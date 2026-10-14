# QCL-CE 插件格式规范 v1

> 本文件是**契约**。网页、App、打包脚本三边都按它来，改这里就要同时改那三处。

## 0. 为什么是「资源型插件」

QCL-CE 的启动器**没有插件运行时**（无 `DexClassLoader`、无沙箱、无权限模型）。
动态加载任意代码在 Android 上既有兼容问题也有安全风险，所以 v1 的插件**只分发资源**，
由启动器已有的导入流程落盘生效：

| 类型 | 内容 | 落点 | 启动器侧 |
|---|---|---|---|
| `control` | 一整套控键布局（`info.json` + 若干 `*.json`） | `<INNER_FILE_DIR>/control/<名称>/` | 已有（`ControllerManagerDialog`） |
| `layout` | 界面排版（`qcl_layout.json` 的 `main` 键） | `SETTING_DIR/qcl_layout.json` | 已有（`LayoutShare`） |

**不做的事**：不加载代码、不改 APK、不申请新权限。插件包里出现 `.dex` / `.jar` / `.so` 一律拒装。

---

## 1. 插件包（zip）

```
<id>-<version>.zip
├── plugin.json                 # 清单（必需，必须位于 zip 根）
└── <target>/                   # 唯一的一个目录，名字 == plugin.json 的 target
    ├── （type=control）info.json + 4 个布局 json
    └── （type=layout） qcl_layout.json
```

约定：

- zip 根**只能**有 `plugin.json` 一个文件 + **恰好一个**目录。
- 那个目录的**名字必须等于** `plugin.json` 里的 `target`。
- `<target>` 允许中文（`type=control` 时它就是布局名）。

★ **为什么是这个结构**（不是随便定的）：启动器里**已经存在**的「控键布局 → 导入」
（`ControllerManagerDialog`）会解压 zip、取**第一个目录**当布局名，并要求它等于 `info.json`
的 `name`。照这个结构打包，**同一个 zip 既能被市场一键安装，也能被老流程手动导入**；
多放一个目录就会选错目录、导入失败。

---

## 2. `plugin.json`

```json
{
  "schemaVersion": 1,
  "id": "control-minimal",
  "name": "极简半透明控键",
  "version": "1.0.0",
  "type": "control",
  "author": "WEEB123321",
  "description": "把默认控键改成低不透明度，少挡画面。",
  "tags": ["控键", "透明"],
  "license": "CC-BY-4.0",
  "minLauncherVersionCode": 1742,
  "target": "极简半透明"
}
```

| 字段 | 必需 | 说明 |
|---|---|---|
| `schemaVersion` | ✅ | 固定 `1`。将来不兼容改动才 +1。 |
| `id` | ✅ | 全局唯一。小写字母 / 数字 / 连字符，`^[a-z0-9][a-z0-9-]{1,47}$`。**发布后不得改**（改了等于新插件）。 |
| `name` | ✅ | 显示名，允许中文，≤ 24 字。 |
| `version` | ✅ | 语义化版本 `MAJOR.MINOR.PATCH`。 |
| `type` | ✅ | `control` \| `layout`。 |
| `author` | ✅ | 作者署名。 |
| `description` | ✅ | 一句话说明「它改变什么」，≤ 60 字。 |
| `tags` | ➖ | 字符串数组，≤ 6 个。用于网页筛选。 |
| `license` | ➖ | 默认 `CC-BY-4.0`。 |
| `minLauncherVersionCode` | ✅ | 需要的最低启动器 `versionCode`。低于此值启动器应拒装并提示升级。 |
| `target` | ✅ | `type=control` 时为落盘目录名（即 `<布局名>`）；`type=layout` 时固定 `main`。 |

---

## 3. `index.json`（市场目录 / 数据库）

由 `tools/build_index.py` 从 `plugins-src/` **自动生成**，不要手改。

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-10-14T13:20:00Z",
  "minLauncherVersionCode": 1742,
  "count": 4,
  "plugins": [
    {
      "id": "control-minimal",
      "name": "极简半透明控键",
      "version": "1.0.0",
      "type": "control",
      "author": "WEEB123321",
      "description": "把默认控键改成低不透明度，少挡画面。",
      "tags": ["控键", "透明"],
      "license": "CC-BY-4.0",
      "minLauncherVersionCode": 1742,
      "updatedAt": "2026-10-14",
      "size": 45678,
      "sha256": "……",
      "download": {
        "url": "https://github.com/WEEB123321/QCL-Plugins/releases/download/plugins/control-minimal-1.0.0.zip",
        "mirror": "https://gh-proxy.com/https://github.com/WEEB123321/QCL-Plugins/releases/download/plugins/control-minimal-1.0.0.zip"
      }
    }
  ]
}
```

`index.json` 里比 `plugin.json` 多出来的字段：`updatedAt`、`size`、`sha256`、`download`。
App 安装前**必须**校验 `sha256`。

---

## 4. 取 index.json 的地址（按顺序重试）

`raw.githubusercontent.com` 与 `cdn.jsdelivr.net` 在中国大陆不可达，所以给多路：

```
1  https://cdn.jsdmirror.com/gh/WEEB123321/QCL-Plugins@main/index.json
2  https://jsdelivr.b-cdn.net/gh/WEEB123321/QCL-Plugins@main/index.json
3  https://fastly.jsdelivr.net/gh/WEEB123321/QCL-Plugins@main/index.json
4  https://gcore.jsdelivr.net/gh/WEEB123321/QCL-Plugins@main/index.json
5  https://ghproxy.net/https://raw.githubusercontent.com/WEEB123321/QCL-Plugins/main/index.json
6  https://gh-proxy.com/https://raw.githubusercontent.com/WEEB123321/QCL-Plugins/main/index.json
```

（2026-10-14 实测 1–6 全部 200；`cdn.jsdelivr.net` 与裸 `raw.githubusercontent.com` 为 000，故不在列表内。）

插件包下载一律走 `gh-proxy.com` 前缀 + GitHub Release 直链，两条都给出。

---

## 5. 新增一个插件（贡献流程）

1. 在 `plugins-src/<id>/` 下放 `plugin.json` 与 `<target>/` 目录
2. 跑 `python tools/build_index.py` —— 生成 `dist/<id>-<version>.zip` 与 `index.json`
3. 提 PR；维护者打 tag `plugins` 建 Release 上传 zip，再推 `index.json`

> `tools/make_plugins.py` 是控键/排版插件的**生成器**：它从启动器内置的
> `assets/control/Default` 派生出样式变体，保证四个布局文件之间不漂移。
> 手工做的插件不需要用它，但结构必须符合 §1。
