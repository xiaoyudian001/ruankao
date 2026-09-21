import { sql } from "drizzle-orm";
import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const checkins = sqliteTable("checkins", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  studyDate: text("study_date").notNull().unique(),
  content: text("content").notNull(),
  duration: integer("duration").notNull().default(0),
  questions: integer("questions").notNull().default(0),
  confidence: integer("confidence").notNull().default(3),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const materials = sqliteTable("materials", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  fileKey: text("file_key").notNull().unique(),
  name: text("name").notNull(),
  kind: text("kind").notNull().default("资料"),
  contentType: text("content_type").notNull(),
  size: integer("size").notNull(),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});
