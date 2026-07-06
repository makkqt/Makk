import { Telegraf } from "telegraf";
import { db, keysTable } from "@workspace/db";
import { eq, and } from "drizzle-orm";
import { logger } from "../lib/logger";
import { randomBytes } from "crypto";

const BOT_TOKEN = process.env["TELEGRAM_BOT_TOKEN"];
const ADMIN_CHAT_ID = process.env["TELEGRAM_ADMIN_CHAT_ID"];

if (!BOT_TOKEN) {
  throw new Error("TELEGRAM_BOT_TOKEN is required");
}
if (!ADMIN_CHAT_ID) {
  throw new Error("TELEGRAM_ADMIN_CHAT_ID is required");
}

export const bot = new Telegraf(BOT_TOKEN);

function isAdmin(chatId: number | string): boolean {
  return String(chatId) === String(ADMIN_CHAT_ID);
}

/** Cryptographically secure key: KURA-XXXX-XXXX-XXXX (uppercase alphanumeric) */
function generateKey(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const pick = (len: number) =>
    Array.from(
      { length: len },
      (_, i) => chars[randomBytes(len)[i] % chars.length],
    ).join("");
  return `KURA-${pick(4)}-${pick(4)}-${pick(4)}`;
}

function parseDuration(str: string): boolean {
  return /\d+\s*(d|day|days|h|hour|hours|m|min|minute|minutes)/i.test(str);
}

/** Escape all MarkdownV2 special characters */
function esc(text: string): string {
  return String(text).replace(/[_*[\]()~`>#+=|{}.!\\-]/g, "\\$&");
}

function formatKeyRow(k: {
  deviceId: string;
  key: string;
  durationStr: string;
  note: string | null;
  isRevoked: boolean;
  createdAt: Date;
}): string {
  const status = k.isRevoked ? "❌ Revoked" : "✅ Active";
  const note = k.note ? `\n  📝 ${esc(k.note)}` : "";
  return (
    `🔑 Key: \`${esc(k.key)}\`\n` +
    `📱 Device: \`${esc(k.deviceId)}\`\n` +
    `⏱ Duration: ${esc(k.durationStr)}\n` +
    `${status}${note}\n` +
    `📅 Created: ${esc(
      k.createdAt.toLocaleString("en-US", { timeZone: "Asia/Rangoon" }),
    )}`
  );
}

function chunkArray<T>(arr: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
}

// ── /start ──────────────────────────────────────────────────────────────────
bot.start(async (ctx) => {
  const admin = isAdmin(ctx.chat.id);
  const welcome = admin
    ? `🤖 *KURANOMI Key Manager* — Admin Mode\n\n` +
      `Commands:\n` +
      `/genkey \\<device\\_id\\> \\<duration\\> — Generate a new key\n` +
      `/listkeys — List all active keys\n` +
      `/listall — List all keys including revoked\n` +
      `/revokekey \\<key\\> — Revoke a key\n` +
      `/checkdevice \\<device\\_id\\> — Check keys for a device\n\n` +
      `Duration examples: \`7d\`, \`30d\`, \`1d\`, \`12h\`, \`60m\``
    : `🤖 *KURANOMI Key Checker*\n\n` +
      `Commands:\n` +
      `/checkdevice \\<device\\_id\\> — Check key status for your device\n\n` +
      `Contact @kuranomi10 to get a key\\.`;

  await ctx.replyWithMarkdownV2(welcome);
});

// ── /genkey <device_id> <duration> [note] ───────────────────────────────────
bot.command("genkey", async (ctx) => {
  if (!isAdmin(ctx.chat.id)) {
    await ctx.reply("⛔ Admin only command.");
    return;
  }

  const args = ctx.message.text.split(/\s+/).slice(1);
  if (args.length < 2) {
    await ctx.reply(
      "Usage: /genkey <device_id> <duration> [note]\nExample: /genkey K-ABCD-EFGH 7d VIP user",
    );
    return;
  }

  const [deviceId, durationStr, ...noteParts] = args;
  const note = noteParts.length > 0 ? noteParts.join(" ") : null;

  if (!parseDuration(durationStr)) {
    await ctx.reply(
      "❌ Invalid duration format.\nExamples: 7d, 30d, 1d, 12h, 60m",
    );
    return;
  }

  const key = generateKey();

  try {
    await db.insert(keysTable).values({
      deviceId,
      key,
      durationStr,
      note,
      createdBy: String(ctx.chat.id),
    });

    await ctx.replyWithMarkdownV2(
      `✅ *Key Generated Successfully\\!*\n\n` +
        `📱 Device ID: \`${esc(deviceId)}\`\n` +
        `🔑 Key: \`${esc(key)}\`\n` +
        `⏱ Duration: ${esc(durationStr)}\n` +
        (note ? `📝 Note: ${esc(note)}\n` : "") +
        `\nSend this key to the user\\.`,
    );

    logger.info({ deviceId, key, durationStr }, "Key generated");
  } catch (err) {
    logger.error({ err }, "Failed to generate key");
    await ctx.reply("❌ Failed to generate key. Try again.");
  }
});

// ── /listkeys — active only ──────────────────────────────────────────────────
bot.command("listkeys", async (ctx) => {
  if (!isAdmin(ctx.chat.id)) {
    await ctx.reply("⛔ Admin only command.");
    return;
  }

  try {
    const keys = await db
      .select()
      .from(keysTable)
      .where(eq(keysTable.isRevoked, false));

    if (keys.length === 0) {
      await ctx.reply("📭 No active keys found.");
      return;
    }

    const chunks = chunkArray(keys, 5);
    for (const chunk of chunks) {
      const text =
        `🗝 *Active Keys \\(${esc(String(keys.length))} total\\)*\n\n` +
        chunk.map(formatKeyRow).join("\n\n─────────────\n\n");
      await ctx.replyWithMarkdownV2(text);
    }
  } catch (err) {
    logger.error({ err }, "Failed to list keys");
    await ctx.reply("❌ Failed to fetch keys.");
  }
});

// ── /listall — all keys ──────────────────────────────────────────────────────
bot.command("listall", async (ctx) => {
  if (!isAdmin(ctx.chat.id)) {
    await ctx.reply("⛔ Admin only command.");
    return;
  }

  try {
    const keys = await db.select().from(keysTable);

    if (keys.length === 0) {
      await ctx.reply("📭 No keys in database.");
      return;
    }

    const chunks = chunkArray(keys, 5);
    for (const chunk of chunks) {
      const text =
        `🗝 *All Keys \\(${esc(String(keys.length))} total\\)*\n\n` +
        chunk.map(formatKeyRow).join("\n\n─────────────\n\n");
      await ctx.replyWithMarkdownV2(text);
    }
  } catch (err) {
    logger.error({ err }, "Failed to list keys");
    await ctx.reply("❌ Failed to fetch keys.");
  }
});

// ── /revokekey <key> ─────────────────────────────────────────────────────────
bot.command("revokekey", async (ctx) => {
  if (!isAdmin(ctx.chat.id)) {
    await ctx.reply("⛔ Admin only command.");
    return;
  }

  const args = ctx.message.text.split(/\s+/).slice(1);
  if (args.length < 1) {
    await ctx.reply(
      "Usage: /revokekey <key>\nExample: /revokekey KURA-ABCD-EFGH-1234",
    );
    return;
  }

  const key = args[0].toUpperCase();

  try {
    const result = await db
      .update(keysTable)
      .set({ isRevoked: true })
      .where(and(eq(keysTable.key, key), eq(keysTable.isRevoked, false)))
      .returning();

    if (result.length === 0) {
      await ctx.reply("❌ Key not found or already revoked.");
      return;
    }

    await ctx.replyWithMarkdownV2(
      `✅ *Key Revoked\\!*\n\n` +
        `🔑 Key: \`${esc(key)}\`\n` +
        `📱 Device: \`${esc(result[0].deviceId)}\``,
    );

    logger.info({ key }, "Key revoked");
  } catch (err) {
    logger.error({ err }, "Failed to revoke key");
    await ctx.reply("❌ Failed to revoke key.");
  }
});

// ── /checkdevice <device_id> ─────────────────────────────────────────────────
bot.command("checkdevice", async (ctx) => {
  const args = ctx.message.text.split(/\s+/).slice(1);
  if (args.length < 1) {
    await ctx.reply(
      "Usage: /checkdevice <device_id>\nExample: /checkdevice K-ABCD-EFGH",
    );
    return;
  }

  const deviceId = args[0];

  try {
    const keys = await db
      .select()
      .from(keysTable)
      .where(eq(keysTable.deviceId, deviceId));

    if (keys.length === 0) {
      await ctx.reply(`❌ No keys found for device: ${deviceId}`);
      return;
    }

    const chunks = chunkArray(keys, 5);
    for (const chunk of chunks) {
      const text =
        `📱 *Keys for \`${esc(deviceId)}\`*\n\n` +
        chunk.map(formatKeyRow).join("\n\n─────────────\n\n");
      await ctx.replyWithMarkdownV2(text);
    }
  } catch (err) {
    logger.error({ err }, "Failed to check device");
    await ctx.reply("❌ Failed to check device.");
  }
});

export function startBot(): void {
  bot.launch({ dropPendingUpdates: true });
  logger.info("Telegram bot started (long polling)");

  process.once("SIGINT", () => bot.stop("SIGINT"));
  process.once("SIGTERM", () => bot.stop("SIGTERM"));
}
