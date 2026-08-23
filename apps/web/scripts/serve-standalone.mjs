import { access, cp, mkdir } from "node:fs/promises";
import { constants } from "node:fs";
import { spawn } from "node:child_process";

const copyIfPresent = async (source, destination) => {
  try {
    await access(source, constants.F_OK);
  } catch {
    return;
  }

  await mkdir(destination, { recursive: true });
  await cp(source, destination, { recursive: true, force: true });
};

await copyIfPresent(".next/static", ".next/standalone/.next/static");
await copyIfPresent("public", ".next/standalone/public");

const child = spawn(process.execPath, [".next/standalone/server.js"], {
  env: process.env,
  stdio: "inherit",
});

child.on("error", () => process.exit(1));
child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});
