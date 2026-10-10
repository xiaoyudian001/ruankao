// D1 batch is transactional. Only the version winner creates a review; retries reuse its id.
export const REVIEW_UPDATE_SQL=`UPDATE textbook_cards SET streak=?,due_date=?,version=version+1,last_review_id=?,updated_at=?
WHERE id=? AND owner_id=? AND version=? AND NOT EXISTS(SELECT 1 FROM textbook_reviews WHERE id=?)`;
export const REVIEW_INSERT_SQL=`INSERT OR IGNORE INTO textbook_reviews
(id,card_id,owner_id,grade,response,study_date,due_date,card_version,created_at)
SELECT ?,id,owner_id,?,?,?,?,?,? FROM textbook_cards WHERE id=? AND owner_id=? AND last_review_id=? AND version=?`;
