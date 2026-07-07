import { decodeJwt as joseDecodeJwt } from "jose";

export const JWT_COOKIE = "datahash_jwt";

export function jwtCookieMaxAge(accessToken: string): number | undefined {
  try {
    const payload = joseDecodeJwt(accessToken);
    if (typeof payload.exp === "number") {
      const remaining = payload.exp - Math.floor(Date.now() / 1000);
      return remaining > 0 ? remaining : undefined;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

export function jwtCookieOptions(accessToken: string) {
  const isProd = process.env.NODE_ENV === "production";
  return {
    path: "/",
    sameSite: "lax" as const,
    secure: isProd,
    httpOnly: true,
    maxAge: jwtCookieMaxAge(accessToken),
  };
}
