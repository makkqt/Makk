import { Router } from "express";
import { db, keysTable } from "@workspace/db";
import { eq } from "drizzle-orm";

const keysRouter = Router();

/**
 * GET /api/keys.txt
 * Public endpoint — returns active keys in the format the Python client expects:
 *   device_id|key|duration_str  (one per line)
 *
 * This mirrors the public GitHub raw-file approach in the original script.
 * The client validates device_id + key together, so exposure of this list is
 * intentional and matches the original design.
 */
keysRouter.get("/keys.txt", async (_req, res) => {
  try {
    const keys = await db
      .select()
      .from(keysTable)
      .where(eq(keysTable.isRevoked, false));

    const lines = keys
      .map((k) => `${k.deviceId}|${k.key}|${k.durationStr}`)
      .join("\n");

    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.send(lines);
  } catch {
    res.status(500).send("Internal server error");
  }
});

export default keysRouter;
