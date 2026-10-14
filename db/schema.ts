import { sql } from "drizzle-orm";
import { integer, sqliteTable, text, uniqueIndex, index } from "drizzle-orm/sqlite-core";

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
  taskType:text('task_type').notNull().default('qa'),
  answerAction:text('answer_action').notNull().default('original'),
  sourceJobId:text('source_job_id'),
  partialAnswer:text('partial_answer').notNull().default(''),
  partialSeq:integer('partial_seq').notNull().default(0),
  cancelRequested:integer('cancel_requested').notNull().default(0),
  examJson:text('exam_json'),
  practiceChoice:text('practice_choice'),
  screenshotJson:text('screenshot_json'),
  recognitionJson:text('recognition_json'),
  taskPayloadJson:text('task_payload_json'),
  retrievalMode: text("retrieval_mode").notNull().default("default"),
  historyJson: text("history_json").notNull().default("[]"),
  retrievalQuery: text("retrieval_query"),
  rewriteRoute: text("rewrite_route"),
  referencesJson: text("references_json").notNull().default("[]"),
  status: text("status").notNull().default("queued"),
  answer: text("answer"),
  error: text("error"),
  createdAt: integer("created_at").notNull(),
  completedAt: integer("completed_at"),
  lease: text("lease"),
  leasedAt: integer("leased_at"),
  elapsedMs: integer("elapsed_ms"),
  tokenUsageJson:text('token_usage_json'),
});

export const textbookSessionDeletions=sqliteTable('textbook_session_deletions',{
 sessionId:text('session_id').primaryKey().references(()=>textbookSessions.id),
 ownerId:text('owner_id').notNull(),deletedAt:integer('deleted_at').notNull(),
},t=>[index('session_deletions_owner').on(t.ownerId)]);

export const textbookBridge = sqliteTable("textbook_bridge", {
  id: text("id").primaryKey(),
  lastSeen: integer("last_seen").notNull(),
  ready: integer("ready").notNull().default(0),
  modes: text("modes").notNull().default('["default"]'),
  conversationReady: integer("conversation_ready").notNull().default(0),
  sourcesReady: integer("sources_ready").notNull().default(0),
  critiqueReady: integer("critique_ready").notNull().default(0),
  examReady:integer('exam_ready').notNull().default(0),
  screenshotReady:integer('screenshot_ready').notNull().default(0),
  essayReady:integer('essay_ready').notNull().default(0),
});

export const textbookPages = sqliteTable("textbook_pages", {
  page: integer("page").primaryKey(),
  status: text("status").notNull().default("queued"),
  fileKey: text("file_key"),
  error: text("error"),
  lease: text("lease"),
  createdAt: integer("created_at").notNull(),
  updatedAt: integer("updated_at").notNull(),
});

export const textbookFavorites = sqliteTable('textbook_favorites', {
  id:text('id').primaryKey(), ownerId:text('owner_id').notNull(), jobId:text('job_id').notNull(),
  question:text('question').notNull(), retrievalQuery:text('retrieval_query'), answer:text('answer').notNull(),
  referencesJson:text('references_json').notNull().default('[]'), createdAt:integer('created_at').notNull(),
},t=>[uniqueIndex('favorites_owner_job').on(t.ownerId,t.jobId)]);
export const textbookCards = sqliteTable('textbook_cards', {
  id:text('id').primaryKey(),ownerId:text('owner_id').notNull(),favoriteId:text('favorite_id').notNull(),
  front:text('front').notNull(),back:text('back').notNull(),dueDate:text('due_date').notNull(),
  streak:integer('streak').notNull().default(0),version:integer('version').notNull().default(0),lastReviewId:text('last_review_id'),
  createdAt:integer('created_at').notNull(),updatedAt:integer('updated_at').notNull(),
},t=>[uniqueIndex('cards_owner_favorite').on(t.ownerId,t.favoriteId),index('cards_owner_due').on(t.ownerId,t.dueDate)]);
export const textbookReviews = sqliteTable('textbook_reviews', {
  id:text('id').primaryKey(),cardId:text('card_id').notNull(),ownerId:text('owner_id').notNull(),
  grade:text('grade').notNull(),response:text('response').notNull(),studyDate:text('study_date').notNull(),
  dueDate:text('due_date').notNull(),cardVersion:integer('card_version').notNull(),createdAt:integer('created_at').notNull(),
  critiqueId:text('critique_id'),
},t=>[index('reviews_owner_day').on(t.ownerId,t.studyDate),uniqueIndex('reviews_card_version').on(t.cardId,t.cardVersion)]);

export const textbookCritiques=sqliteTable('textbook_critiques',{
 id:text('id').primaryKey(),ownerId:text('owner_id').notNull(),cardId:text('card_id').notNull(),cardVersion:integer('card_version').notNull(),
 jobId:text('job_id').notNull(),front:text('front').notNull(),back:text('back').notNull(),response:text('response').notNull(),referencesJson:text('references_json').notNull(),
 status:text('status').notNull().default('queued'),resultJson:text('result_json'),error:text('error'),lease:text('lease'),leasedAt:integer('leased_at'),
 createdAt:integer('created_at').notNull(),completedAt:integer('completed_at'),
},t=>[index('critiques_owner_card').on(t.ownerId,t.cardId),index('critiques_status').on(t.status,t.createdAt)]);

export const textbookCases=sqliteTable('textbook_cases',{
 id:text('id').primaryKey(),ownerId:text('owner_id').notNull(),title:text('title').notNull(),background:text('background').notNull(),createdAt:integer('created_at').notNull(),
},t=>[index('cases_owner_created').on(t.ownerId,t.createdAt)]);
export const textbookCaseQuestions=sqliteTable('textbook_case_questions',{
 id:text('id').primaryKey(),caseId:text('case_id').notNull(),ownerId:text('owner_id').notNull(),prompt:text('prompt').notNull(),ordinal:integer('ordinal').notNull(),jobId:text('job_id').notNull(),createdAt:integer('created_at').notNull(),
},t=>[uniqueIndex('case_question_order').on(t.caseId,t.ordinal),uniqueIndex('case_question_job').on(t.jobId)]);
export const textbookCaseAttempts=sqliteTable('textbook_case_attempts',{
 id:text('id').primaryKey(),questionId:text('question_id').notNull(),ownerId:text('owner_id').notNull(),response:text('response').notNull(),createdAt:integer('created_at').notNull(),
},t=>[index('case_attempts_owner_question').on(t.ownerId,t.questionId,t.createdAt)]);

export const textbookEssays=sqliteTable('textbook_essays',{
 id:text('id').primaryKey(),ownerId:text('owner_id').notNull(),title:text('title').notNull(),topic:text('topic').notNull(),requirements:text('requirements').notNull(),projectFacts:text('project_facts').notNull(),draftsJson:text('drafts_json').notNull(),version:integer('version').notNull().default(0),lastSaveId:text('last_save_id'),createdAt:integer('created_at').notNull(),updatedAt:integer('updated_at').notNull(),
},t=>[index('essays_owner_updated').on(t.ownerId,t.updatedAt)]);
export const textbookEssayRuns=sqliteTable('textbook_essay_runs',{
 id:text('id').primaryKey(),ownerId:text('owner_id').notNull(),essayId:text('essay_id').notNull(),essayVersion:integer('essay_version').notNull(),kind:text('kind').notNull(),section:text('section').notNull(),payloadJson:text('payload_json').notNull(),createdAt:integer('created_at').notNull(),
},t=>[index('essay_runs_owner_essay').on(t.ownerId,t.essayId,t.createdAt)]);
