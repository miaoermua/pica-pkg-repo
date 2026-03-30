# Pica 软件包源码 (Package Source)

本目录是 Pica 软件源的**元数据定义库**。这里不存放二进制大文件，只存放应用的“身份证”。

## 📦 核心组成

每个应用目录包含：
1.  **manifest**: 核心元数据（版本、架构、依赖、安装说明）。
2.  **cmd/**: 生命周期脚本占位符（install, update, remove）。

## 🛠️ 如何添加新包？

1.  在 `src/` 下创建子目录。
2.  编写 `manifest`。
3.  在 `src/opkg/manifest.json` 中完成注册。

**当 `pica-pack` 运行时，它会读取此处的 manifest 来生成最终提供给路由器的安装包。**
