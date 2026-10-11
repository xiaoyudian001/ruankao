ALTER TABLE `textbook_bridge` ADD `exam_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `task_type` text DEFAULT 'qa' NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `exam_json` text;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `practice_choice` text;