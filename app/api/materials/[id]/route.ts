import { eq } from "drizzle-orm";
import { env } from "cloudflare:workers";
import { getDb } from "../../../../db";
import { materials } from "../../../../db/schema";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    if (!env.BUCKET) throw new Error("R2 unavailable");
    const { id } = await context.params;
    const [row] = await getDb().select().from(materials).where(eq(materials.id, Number(id))).limit(1);
    if (!row) return new Response("未找到文件", { status: 404 });
    const object = await env.BUCKET.get(row.fileKey);
    if (!object) return new Response("未找到文件", { status: 404 });
    return new Response(object.body, { headers: { "Content-Type": row.contentType, "Content-Disposition": `attachment; filename*=UTF-8''${encodeURIComponent(row.name)}` } });
  } catch (error) {
    console.error("material GET", error);
    return new Response("下载失败", { status: 500 });
  }
}

export async function DELETE(_request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    if (!env.BUCKET) throw new Error("R2 unavailable");
    const { id } = await context.params;
    const materialId = Number(id);
    if (!Number.isInteger(materialId) || materialId <= 0) {
      return Response.json({ error: "文件编号无效。" }, { status: 400 });
    }
    const db = getDb();
    const [row] = await db.select().from(materials).where(eq(materials.id, materialId)).limit(1);
    if (!row) return Response.json({ error: "文件不存在或已被删除。" }, { status: 404 });
    await env.BUCKET.delete(row.fileKey);
    await db.delete(materials).where(eq(materials.id, materialId));
    return Response.json({ deleted: true, id: materialId });
  } catch (error) {
    console.error("material DELETE", error);
    return Response.json({ error: "删除失败，请稍后重试。" }, { status: 500 });
  }
}
