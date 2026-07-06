import {
  pgTable,
  text,
  serial,
  timestamp,
  boolean,
} from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const keysTable = pgTable("keys", {
  id: serial("id").primaryKey(),
  deviceId: text("device_id").notNull(),
  key: text("key").notNull().unique(),
  durationStr: text("duration_str").notNull(), // e.g. "7d", "30d", "1h"
  note: text("note"),
  isRevoked: boolean("is_revoked").notNull().default(false),
  createdBy: text("created_by"), // telegram chat_id of admin who created
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const insertKeySchema = createInsertSchema(keysTable).omit({
  id: true,
  createdAt: true,
});
export type InsertKey = z.infer<typeof insertKeySchema>;
export type Key = typeof keysTable.$inferSelect;
