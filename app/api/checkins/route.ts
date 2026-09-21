import { desc, eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { checkins } from "../../../db/schema";

export async function GET() {
  try {
    const rows = await getDb().select().from(checkins).orderBy(desc(checkins.studyDate));
    return Response.json({ checkins: rows });
  } catch (error) {
    console.error("checkins GET", error);
    return Response.json({ error: "打卡记录暂时无法读取，请稍后重试。" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const studyDate = String(body.studyDate ?? "").trim();
    const content = String(body.content ?? "").trim();
    const duration = Math.max(0, Number(body.duration) || 0);
    const questions = Math.max(0, Number(body.questions) || 0);
    const confidence = Math.min(5, Math.max(1, Number(body.confidence) || 3));
    if (!/^\d{4}-\d{2}-\d{2}$/.test(studyDate) || !content) {
      return Response.json({ error: "请填写学习日期和复习内容。" }, { status: 400 });
    }
    const db = getDb();
    const existing = await db.select({ id: checkins.id }).from(checkins).where(eq(checkins.studyDate, studyDate)).limit(1);
    if (existing[0]) {
      const [row] = await db.update(checkins).set({ content, duration, questions, confidence, updatedAt: new Date().toISOString() }).where(eq(checkins.id, existing[0].id)).returning();
      return Response.json({ checkin: row });
    }
    const [row] = await db.insert(checkins).values({ studyDate, content, duration, questions, confidence }).returning();
    return Response.json({ checkin: row }, { status: 201 });
  } catch (error) {
    console.error("checkins POST", error);
    return Response.json({ error: "保存失败，内容已保留，请重试。" }, { status: 500 });
  }
}
