import { desc } from "drizzle-orm";
import { env } from "cloudflare:workers";
import { getDb } from "../../../db";
import { materials } from "../../../db/schema";

export async function GET() {
  try {
    const rows = await getDb().select().from(materials).orderBy(desc(materials.createdAt));
    return Response.json({ materials: rows });
  } catch (error) {
    console.error("materials GET", error);
    return Response.json({ error: "资料列表暂时无法读取。" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    if (!env.BUCKET) throw new Error("R2 unavailable");
    const form = await request.formData();
    const file = form.get("file");
    const kind = String(form.get("kind") ?? "资料");
    if (!(file instanceof File) || file.size === 0) return Response.json({ error: "请选择文件。" }, { status: 400 });
    if (file.size > 25 * 1024 * 1024) return Response.json({ error: "单个文件不能超过 25MB。" }, { status: 400 });
    const key = `${Date.now()}-${crypto.randomUUID()}`;
    await env.BUCKET.put(key, file.stream(), { httpMetadata: { contentType: file.type || "application/octet-stream" } });
    const [row] = await getDb().insert(materials).values({ fileKey: key, name: file.name, kind, contentType: file.type || "application/octet-stream", size: file.size }).returning();
    return Response.json({ material: row }, { status: 201 });
  } catch (error) {
    console.error("materials POST", error);
    return Response.json({ error: "上传失败，请稍后重试。" }, { status: 500 });
  }
}
