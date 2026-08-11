import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const children = [];

function start(command, args) {
  const child = spawn(command, args, { cwd: root, stdio: "inherit" });
  children.push(child);
  child.on("exit", (code) => code && stop(code));
  return child;
}

async function waitForApi() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      if ((await fetch("http://127.0.0.1:8095/api/health")).ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Research World API did not start");
}

function stop(code = 0) {
  children.forEach((child) => child.kill("SIGTERM"));
  setTimeout(() => process.exit(code), 100);
}

process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());

start("uv", ["run", "research-world", "serve", "--port", "8095"]);
await waitForApi();
start("uv", ["run", "research-worker", "--server", "http://127.0.0.1:8095"]);
start("npm", ["--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1"]);
