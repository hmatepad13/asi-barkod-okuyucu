import { NextResponse } from "next/server";
import { PWA_RELEASE } from "../../release";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json(
    { release: PWA_RELEASE },
    { headers: { "Cache-Control": "no-store, max-age=0" } },
  );
}
