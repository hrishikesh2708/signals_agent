import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { JWT_COOKIE } from "@/lib/auth";

const PUBLIC_AUTH_PATHS = new Set(["/login", "/register"]);

const PROTECTED_PREFIXES = ["/chat", "/chat-dev", "/interrupt-dev"] as const;

function getToken(request: NextRequest): string | undefined {
  return request.cookies.get(JWT_COOKIE)?.value;
}

function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = getToken(request);

  if (PUBLIC_AUTH_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  if (isProtectedPath(pathname) && !token) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/register",
    "/chat/:path*",
    "/chat-dev/:path*",
    "/interrupt-dev/:path*",
  ],
};
