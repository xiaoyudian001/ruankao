CREATE TABLE `textbook_essay_runs` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`essay_id` text NOT NULL,
	`essay_version` integer NOT NULL,
	`kind` text NOT NULL,
	`section` text NOT NULL,
	`payload_json` text NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `essay_runs_owner_essay` ON `textbook_essay_runs` (`owner_id`,`essay_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `textbook_essays` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`title` text NOT NULL,
	`topic` text NOT NULL,
	`requirements` text NOT NULL,
	`project_facts` text NOT NULL,
	`drafts_json` text NOT NULL,
	`version` integer DEFAULT 0 NOT NULL,
	`last_save_id` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `essays_owner_updated` ON `textbook_essays` (`owner_id`,`updated_at`);--> statement-breakpoint
ALTER TABLE `textbook_bridge` ADD `essay_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `task_payload_json` text;