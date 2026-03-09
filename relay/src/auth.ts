import { hashToken } from "./tokens";
import { unauthorized } from "./errors";

export interface ChannelRecord {
  pubkey?: string;
  push_token_hash: string;
  pull_token_hash: string;
  device_token?: string;
  device_name?: string;
  created_at: string;
}

export function extractBearerToken(request: Request): string | null {
  const auth = request.headers.get("Authorization");
  if (!auth?.startsWith("Bearer ")) return null;
  return auth.slice(7);
}

export async function authenticatePush(
  request: Request,
  channel: ChannelRecord,
): Promise<Response | null> {
  const token = extractBearerToken(request);
  if (!token) return unauthorized("Missing Authorization header");
  const hash = await hashToken(token);
  if (hash !== channel.push_token_hash) return unauthorized("Invalid push token");
  return null;
}

export async function authenticatePull(
  request: Request,
  channel: ChannelRecord,
): Promise<Response | null> {
  const token = extractBearerToken(request);
  if (!token) return unauthorized("Missing Authorization header");
  const hash = await hashToken(token);
  if (hash !== channel.pull_token_hash) return unauthorized("Invalid pull token");
  return null;
}
