export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 1. 代理 repo.json 索引文件 (从 GitHub 原始链接抓取)
    if (path === "/repo.json" || path === "/r/repo.json") {
      const rawUrl = `https://raw.githubusercontent.com/${env.GITHUB_USER}/${env.GITHUB_REPO}/main/r/repo.json`;
      const resp = await fetch(rawUrl);
      
      if (!resp.ok) {
        return new Response(`Error fetching repo index from GitHub: ${resp.statusText}`, { status: resp.status });
      }

      return new Response(resp.body, {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "max-age=60" 
        }
      });
    }

    // 2. 代理发布包 (重定向到 GitHub Releases)
    // 预期路径格式: /releases/{tag}/{filename}
    // 或者是 /latest/{filename} 重定向到 latest 标签
    if (path.startsWith("/releases/")) {
      const parts = path.split("/");
      if (parts.length >= 4) {
        const tag = parts[2];
        const filename = parts[3];
        const releaseUrl = `https://github.com/${env.GITHUB_USER}/${env.GITHUB_REPO}/releases/download/${tag}/${filename}`;
        return Response.redirect(releaseUrl, 302);
      }
    }
    
    if (path.startsWith("/latest/")) {
      const filename = path.replace("/latest/", "");
      const releaseUrl = `https://github.com/${env.GITHUB_USER}/${env.GITHUB_REPO}/releases/download/latest/${filename}`;
      return Response.redirect(releaseUrl, 302);
    }

    return new Response("Pica Repository Worker is Running.\n\nUsage:\n- /repo.json\n- /latest/{filename}\n- /releases/{tag}/{filename}", { 
      status: 200,
      headers: { "content-type": "text/plain; charset=utf-8" }
    });
  }
};
