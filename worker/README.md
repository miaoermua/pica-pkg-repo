# Pica Cloudflare 分发引擎 (Worker)

本目录包含仓库的 **Cloudflare Worker** 代理逻辑，负责将 GitHub 上的资源秒速分发至全球。

## ⚡ 核心能力

1.  **索引代理**: 缓存并分发 `repo.json` 索引文件。
2.  **智能缓存 (Smart Cache)**:
    *   通过 `repo.json` 里的 SHA256 哈希值对二进制包进行指纹识别。
    *   命中缓存时，用户直接从 Cloudflare CDN 下载，**速度极快**且不占用 GitHub 带宽。
    *   SHA256 变化时，自动刷新缓存，确保永不过时。

## 🚀 部署

*   基于 `wrangler.toml` 配置。
*   支持 GitHub 同步自动部署。

**地址**: `https://pica-pkg-repo.<username>.workers.dev/`
