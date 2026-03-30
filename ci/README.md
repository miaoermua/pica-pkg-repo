# Pica CI 配置中心 (Continuous Integration)

本目录存放 Pica 软件源的**自动化抓取逻辑**。

## 📂 目录结构

*   `opkg/`：针对基于 OpenWrt opkg 管理的应用构建规则。
*   `none/`：针对免管理器（纯脚本/二进制）的应用构建规则。

## ⚙️ build.json 职能

每个子目录下的 `build.json` 都是一个“抓取任务单”：
*   **Source**: 指定从 GitHub 或 HTTP 镜像站抓取什么。
*   **Matrix**: 定义要支持的硬件架构（如 x86_64, aarch64）。
*   **Pack**: 指示 `pica-pack` 如何将这些文件打包。

**修改此处的 JSON 后，GitHub Actions 会自动触发对应的抓取和打包任务。**
