import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const dir = path.dirname(fileURLToPath(import.meta.url));
const imageRoot = path.resolve(dir, "../images");
const imageTypes = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
};

function mockupImages() {
  return {
    name: "mockup-images",
    configureServer(server) {
      server.middlewares.use("/images", (req, res, next) => {
        const raw = decodeURIComponent((req.url || "/").split("?")[0]).replace(/^[/\\]+/, "");
        if (!raw) return next();
        const file = path.resolve(imageRoot, raw);
        const rel = path.relative(imageRoot, file);
        if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return next();
        fs.stat(file, (err, stat) => {
          if (err || !stat.isFile()) return next();
          res.setHeader("Content-Type", imageTypes[path.extname(file).toLowerCase()] || "application/octet-stream");
          fs.createReadStream(file).pipe(res);
        });
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const envDir = path.resolve(dir, "..");
  const env = loadEnv(mode, envDir, "");
  const proxyTarget = (env.API_PROXY_TARGET || "http://127.0.0.1:8000").replace(/\/$/, "");
  return {
    envDir,
    plugins: [react(), mockupImages()],
    server: {
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
      fs: {
        allow: [dir, envDir],
      },
    },
  };
});
