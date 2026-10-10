CREATE TABLE `textbook_cards` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`favorite_id` text NOT NULL,
	`front` text NOT NULL,
	`back` text NOT NULL,
	`due_date` text NOT NULL,
	`streak` integer DEFAULT 0 NOT NULL,
	`version` integer DEFAULT 0 NOT NULL,
	`last_review_id` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `cards_owner_favorite` ON `textbook_cards` (`owner_id`,`favorite_id`);--> statement-breakpoint
CREATE INDEX `cards_owner_due` ON `textbook_cards` (`owner_id`,`due_date`);--> statement-breakpoint
CREATE TABLE `textbook_favorites` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`job_id` text NOT NULL,
	`question` text NOT NULL,
	`retrieval_query` text,
	`answer` text NOT NULL,
	`references_json` text DEFAULT '[]' NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `favorites_owner_job` ON `textbook_favorites` (`owner_id`,`job_id`);--> statement-breakpoint
CREATE TABLE `textbook_reviews` (
	`id` text PRIMARY KEY NOT NULL,
	`card_id` text NOT NULL,
	`owner_id` text NOT NULL,
	`grade` text NOT NULL,
	`response` text NOT NULL,
	`study_date` text NOT NULL,
	`due_date` text NOT NULL,
	`card_version` integer NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `reviews_owner_day` ON `textbook_reviews` (`owner_id`,`study_date`);--> statement-breakpoint
CREATE UNIQUE INDEX `reviews_card_version` ON `textbook_reviews` (`card_id`,`card_version`);