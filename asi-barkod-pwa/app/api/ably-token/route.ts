import { Rest } from "ably";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const apiKey = process.env.ABLY_API_KEY;
  const workspaceId = process.env.ABLY_WORKSPACE_ID;
  if (!apiKey || !workspaceId) {
    return NextResponse.json(
      { error: "Ably sunucu ayarı eksik." },
      { status: 503 },
    );
  }

  const requestedClientId =
    request.nextUrl.searchParams.get("clientId") || "phone-pwa";
  const clientId = requestedClientId.replace(/[^a-zA-Z0-9._-]/g, "").slice(0, 80);
  const prefix = `asi-barkod:${workspaceId}:`;
  const capability = JSON.stringify({
    [`${prefix}*`]: ["publish", "subscribe"],
  });

  try {
    const ably = new Rest({ key: apiKey });
    const tokenRequest = await ably.auth.createTokenRequest({
      clientId: clientId || "phone-pwa",
      capability,
      ttl: 60 * 60 * 1000,
    });
    return NextResponse.json(tokenRequest, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
