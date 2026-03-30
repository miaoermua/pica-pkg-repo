# Pica CI 自动化工具文档

这是 Pica 软件包仓库的核心自动化引擎，负责从全球各地的上游源抓取二进制文件，并将其转换为标准 Pica 格式。

## 🛠️ 脚本角色说明

### 1. `fetch_assets.py` (资源抓取器)
它是仓库的“采购员”，负责寻找、匹配并下载 `.ipk` 或 `.tar.gz` 二进制资源。

*   **GitHub Provider**: 通过 GitHub API 抓取指定 Release 各架构的资产。
*   **HTTP Template Provider**: 通过 URL 模板（如北大镜像站）批量拼接下载链接。
*   **双向映射**: 自动将上游架构名（如 `x86_64`）映射到 Pica 架构目录（`binary/amd64/x86_64`）。

### 2. `gen_repo_index.py` (索引聚合器)
它是仓库的“索引师”，负责在每个 CI 周期完成后，扫描 `build_output` 下的所有包，合并生成单一的 `repo.json` 索引文件。

---

## 📂 build.json 配置指南

每个应用在 `ci/opkg/<app_id>/build.json` 中定义其抓取逻辑。

### 示例 A：GitHub 抓取模式
```json
"source": {
  "provider": "github",
  "repo": "user/repo",
  "release": {
    "tag": { "regex": "^v?[0-9.]+$" },
    "assets": [
      {
        "regex": "^app_.*_(x86_64|aarch64)\\.ipk$",
        "capture_to": { "arch": 1 }
      }
    ]
  }
}
```

### 示例 B：HTTP 模板模式 (如镜像站)
```json
"source": {
  "provider": "http_template",
  "version": "1.2.3",
  "url_template": "https://mirrors.com/path/{arch}/file_{version}_{arch}.ipk"
}
```
*   **{arch}**: 会自动被 `build.matrix` 里的架构替换。
*   **{version}**: 会自动被 `source.version` 替换。

---

## 🚀 仓库结构规范

1.  **src/opkg/<app>/manifest**: 软件包的身份信息元数据。
2.  **src/opkg/<app>/cmd/ [install|update|remove]**: 软件包的生命周期脚本（目前设为 `exit 0` 占位）。
3.  **ci/opkg/<app>/build.json**: 软件包在 CI 周期中的自动化规则。
4.  **r/repo.json**: 最终通过 Worker 发布的二进制索引地图。
