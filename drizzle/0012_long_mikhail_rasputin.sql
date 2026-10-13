ALTER TABLE `textbook_jobs` ADD `answer_action` text DEFAULT 'original' NOT NULL;--> statement-breakpoint
ALTER TABLE `textbook_jobs` ADD `source_job_id` text;