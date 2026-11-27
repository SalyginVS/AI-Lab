import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { homedir } from "node:os";
import { join } from "node:path";

const exec = promisify(execFile);
const profiles = Object.freeze({
  "ailab-strata/inkling-2-mini-sq-20": "inkling",
  "ailab-strata/qwen3.8-flash-next-ud-q6_k_xl": "flash",
  "ailab-ollama/qwen3.8-27b-gsq-rco:iq3s-mtp-262k": "q27",
});
const key = (model) => model && model.provider + "/" + model.id;
const helper = (name) => join(homedir(), ".local", "bin", name);

async function current() {
  const { stdout } = await exec(helper("ailab-mode"), ["current"], { timeout: 20000, maxBuffer: 1024 * 1024 });
  const value = stdout.trim();
  if (!Object.hasOwn(profiles, value)) throw new Error("Unverified backend/model: " + value);
  return value;
}
async function select(choice) {
  // No interactive password, shell interpolation or extra privileged commands.
  // The controller owns transition/recovery timeouts.
  const { stdout } = await exec(helper("ailab-select-model"), ["--from-pi", choice], { maxBuffer: 1024 * 1024 });
  if (!stdout.split(/\r?\n/).includes("MODEL_READY " + choice)) {
    throw new Error("Selector did not confirm " + choice);
  }
}

export function installModelSwitch(pi, ops = { current, select }) {
  let switching = false;
  let restoring = false;
  let accepted;
  let inputChecks = 0;
  const status = (ctx, message) => ctx.ui.setStatus("ailab-backend", message);
  const report = (ctx, message, level = "info") => ctx.ui.notify(message, level);
  const describe = (error) => String(error?.stderr || error?.message || error).trim().slice(0, 700);

  async function align(ctx, modelKey) {
    if (!Object.hasOwn(profiles, modelKey)) throw new Error("Cannot align with unknown model");
    if (key(ctx.model) !== modelKey) {
      const slash = modelKey.indexOf("/");
      const model = ctx.modelRegistry.find(modelKey.slice(0, slash), modelKey.slice(slash + 1));
      if (!model) throw new Error("Active model missing from local registry");
      restoring = true;
      try {
        if (!await pi.setModel(model)) throw new Error("Pi refused model restoration");
      } finally {
        restoring = false;
      }
    }
    if (key(ctx.model) !== modelKey) throw new Error("Model selection changed during restoration");
    accepted = modelKey;
    status(ctx, "AI Lab READY: " + profiles[modelKey]);
  }

  async function sync(ctx, previous) {
    accepted = undefined;
    try {
      await align(ctx, await ops.current());
      return true;
    } catch (error) {
      // Never trigger a backend transition during session restore or on error.
      if (previous && Object.hasOwn(profiles, previous) && key(ctx.model) !== previous) {
        try {
          await align(ctx, previous);
        } catch (_) {}
      }
      accepted = undefined;
      status(ctx, "AI Lab BLOCKED: backend not verified");
      report(ctx, "AI Lab: backend readiness could not be verified. " + describe(error), "error");
      return false;
    }
  }

  pi.on("session_start", async (_event, ctx) => {
    await sync(ctx);
  });

  pi.on("model_select", async (event, ctx) => {
    if (restoring) return;
    const target = key(event.model);
    const previous = key(event.previousModel);
    if (switching) {
      // Native Pi sets its model before this event. Ignore additional selections,
      // then realign to the verified result of the first transaction.
      report(ctx, "AI Lab: wait for the current model transition to finish.", "warning");
      return;
    }
    switching = true;
    try {
      if (!ctx.isIdle() || ctx.hasPendingMessages() || inputChecks > 0) {
        if (previous && Object.hasOwn(profiles, previous)) await align(ctx, previous);
        report(ctx, "AI Lab: model change refused while Pi is busy.", "warning");
        return;
      }
      if (event.source === "restore" || ctx.mode !== "tui" || !Object.hasOwn(profiles, target)) {
        await sync(ctx, previous);
        report(ctx, "AI Lab: only an explicit idle TUI selection can switch a backend.", "warning");
        return;
      }
      await ops.current();
      if (!ctx.isIdle() || ctx.hasPendingMessages() || inputChecks > 0) {
        throw new Error("Pi stopped being idle during preflight");
      }
      accepted = undefined;
      status(ctx, "AI Lab switching: " + profiles[target]);
      report(ctx, "AI Lab: loading " + profiles[target] + "; wait for READY.");
      // The local selector checks parent PID, other Pi processes, and controller locks;
      // server confirms drained connections, resource release, and readiness.
      await ops.select(profiles[target]);
      const after = await ops.current();
      if (after !== target) throw new Error("Controller returned a different model: " + after);
      await align(ctx, after);
      report(ctx, "AI Lab MODEL_READY " + profiles[target]);
    } catch (error) {
      report(ctx, "AI Lab: transition refused/failed: " + describe(error), "error");
      await sync(ctx, previous);
    } finally {
      switching = false;
    }
  });

  pi.on("input", async (_event, ctx) => {
    const requested = key(ctx.model);
    try {
      if (switching) throw new Error("Wait for MODEL_READY");
      if (!ctx.isIdle()) {
        if (accepted === requested) return { action: "continue" };
        throw new Error("Model is not verified during generation");
      }
      inputChecks++;
      let observed;
      try { observed = await ops.current(); } finally { inputChecks--; }
      if (switching || key(ctx.model) !== requested) throw new Error("Model selection changed during input preflight");
      if (observed !== requested) throw new Error("Pi=" + requested + "; backend=" + observed);
      accepted = requested;
      status(ctx, "AI Lab READY: " + profiles[requested]);
      return { action: "continue" };
    } catch (error) {
      accepted = undefined;
      status(ctx, "AI Lab BLOCKED");
      report(ctx, "AI Lab: request not sent. " + describe(error), "error");
      return { action: "handled" };
    }
  });

  pi.on("session_before_compact", async (_event, ctx) => {
    const requested = key(ctx.model);
    try {
      if (switching || await ops.current() !== requested) throw new Error("backend/model mismatch");
    } catch (error) {
      report(ctx, "AI Lab: compaction cancelled: " + describe(error), "error");
      return { cancel: true };
    }
  });

  pi.registerCommand("lab-status", {
    description: "Verify the actual AI Lab backend and current Pi model (read-only)",
    handler: async (_args, ctx) => {
      if (switching) { report(ctx, "AI Lab transition in progress."); return; }
      try {
        const observed = await ops.current();
        report(ctx, "Pi: " + key(ctx.model) + "\nBackend: " + observed,
          observed === key(ctx.model) ? "info" : "warning");
      } catch (error) { report(ctx, describe(error), "error"); }
    },
  });
}
export default function (pi) { installModelSwitch(pi); }
