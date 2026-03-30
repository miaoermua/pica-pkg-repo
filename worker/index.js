export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const cache = caches.default;

    // --- Helper: Fetch repo.json with short-term cache ---
    const getRepoIndex = async () => {
      const repoUrl = `https://raw.githubusercontent.com/${env.GITHUB_USER}/${env.GITHUB_REPO}/main/r/repo.json`;
      const cacheKey = new Request(new URL("/repo.json", url.origin));
      
      let response = await cache.match(cacheKey);
      if (!response) {
        const resp = await fetch(repoUrl);
        if (!resp.ok) return null;
        
        // Cache for 60 seconds
        response = new Response(resp.body, resp);
        response.headers.set("Cache-Control", "max-age=60");
        await cache.put(cacheKey, response.clone());
      }
      return await response.json();
    };

    // 1. Route: /repo.json (Direct Proxy with Cache)
    if (path === "/repo.json" || path === "/r/repo.json") {
      const index = await getRepoIndex();
      if (!index) return new Response("Error fetching repo index", { status: 502 });
      
      return new Response(JSON.stringify(index), {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "max-age=60"
        }
      });
    }

    // 2. Route: Package Files (/latest/xxx or /releases/xxx)
    if (path.startsWith("/releases/") || path.startsWith("/latest/")) {
      const filename = path.split("/").pop();
      if (!filename.endsWith(".pkg.tar.gz")) {
        return new Response("Not a Pica package file", { status: 400 });
      }

      // 2a. Smart Cache Hook: Get SHA256 from Index
      const index = await getRepoIndex();
      const pkgInfo = index ? index.packages.find(p => p.filename === filename) : null;
      
      // If we can't find it in index, we use "no-hash" but don't cache indefinitely
      const sha256 = pkgInfo ? pkgInfo.sha256 : "no-hash";
      
      // 2b. Construct Cache Key using SHA256 as a fingerprint
      // This ensures that if the SHA256 in repo.json changes, the cache is bypassed.
      const cacheKeyUrl = new URL(request.url);
      cacheKeyUrl.searchParams.set("hash", sha256);
      const cacheKey = new Request(cacheKeyUrl);

      let response = await cache.match(cacheKey);

      if (!response) {
        let releaseUrl;
        if (path.startsWith("/latest/")) {
          releaseUrl = `https://github.com/${env.GITHUB_USER}/${env.GITHUB_REPO}/releases/download/latest/${filename}`;
        } else {
          const parts = path.split("/");
          const tag = parts[2];
          releaseUrl = `https://github.com/${env.GITHUB_USER}/${env.GITHUB_REPO}/releases/download/${tag}/${filename}`;
        }

        const githubResp = await fetch(releaseUrl);
        if (!githubResp.ok) {
          return new Response(`GitHub Error: ${githubResp.statusText}`, { status: githubResp.status });
        }

        // Create cached response
        response = new Response(githubResp.body, githubResp);
        response.headers.set("Access-Control-Allow-Origin", "*");
        
        // If we have a hash, cache it "forever" (7 days)
        if (sha256 !== "no-hash") {
          response.headers.set("Cache-Control", "public, max-age=604800, immutable");
          await cache.put(cacheKey, response.clone());
        } else {
          // If no hash found in index, cache only briefly
          response.headers.set("Cache-Control", "public, max-age=300");
        }
      }

      return response;
    }

    return new Response("Pica Smart Proxy Worker\n- /repo.json\n- /latest/{file}\n- /releases/{tag}/{file}", { 
      status: 200,
      headers: { "content-type": "text/plain; charset=utf-8" }
    });
  }
};
