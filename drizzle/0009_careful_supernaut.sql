CREATE TABLE `textbook_case_attempts` (
	`id` text PRIMARY KEY NOT NULL,
	`question_id` text NOT NULL,
	`owner_id` text NOT NULL,
	`response` text NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `case_attempts_owner_question` ON `textbook_case_attempts` (`owner_id`,`question_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `textbook_case_questions` (
	`id` text PRIMARY KEY NOT NULL,
	`case_id` text NOT NULL,
	`owner_id` text NOT NULL,
	`prompt` text NOT NULL,
	`ordinal` integer NOT NULL,
	`job_id` text NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `case_question_order` ON `textbook_case_questions` (`case_id`,`ordinal`);--> statement-breakpoint
CREATE UNIQUE INDEX `case_question_job` ON `textbook_case_questions` (`job_id`);--> statement-breakpoint
CREATE TABLE `textbook_cases` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`title` text NOT NULL,
	`background` text NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `cases_owner_created` ON `textbook_cases` (`owner_id`,`created_at`);