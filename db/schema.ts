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

export const textbookSessions = sqliteTable("textbook_sessions", {
  id: text("id").primaryKey(),
  ownerId: text("owner_id").notNull(),
  title: text("title").notNull(),
  createdAt: integer("created_at").notNull(),
  updatedAt: integer("updated_at").notNull(),
});

export const textbookJobs = sqliteTable("textbook_jobs", {
  id: text("id").primaryKey(),
  sessionId: text("session_id").notNull().references(() => textbookSessions.id),
  ownerId: text("owner_id").notNull(),
  question: text("question").notNull(),
  retrievalMode: text("retrieval_mode").notNull().default("default"),
  status: text("status").notNull().default("queued"),
  answer: text("answer"),
  error: text("error"),
  createdAt: integer("created_at").notNull(),
  completedAt: integer("completed_at"),
  lease: text("lease"),
  leasedAt: integer("leased_at"),
  elapsedMs: integer("elapsed_ms"),
});

export const textbookBridge = sqliteTable("textbook_bridge", {
  id: text("id").primaryKey(),
  lastSeen: integer("last_seen").notNull(),
  ready: integer("ready").notNull().default(0),
  modes: text("modes").notNull().default('["default"]'),
});
