import { sendPushNotification } from "./apns";
import { type ChannelRecord, authenticatePush, authenticatePull } from "./auth";
import { badRequest, notFound, payloadTooLarge } from "./errors";
import { generateToken, hashToken } from "./tokens";

const IMAGE_TTL = 1800; // 30 minutes
const CHANNEL_TTL = 2592000; // 30 days
const MAX_PAYLOAD_SIZE = 10 * 1024 * 1024; // 10MB

const MAX_DEVICE_NAME_LENGTH = 64;

function truncateDeviceName(name?: string): string | undefined {
  if (!name) return undefined;
  return name.slice(0, MAX_DEVICE_NAME_LENGTH);
}

export async function createChannel(request: Request, kv: KVNamespace): Promise<Response> {
  const body = await request.json<{ pubkey?: string; device_token?: string; device_name?: string }>().catch(() => ({}));

  const channelId = crypto.randomUUID();
  const pushToken = generateToken();
  const pullToken = generateToken();

  const deviceName = truncateDeviceName(body.device_name);

  const channel: ChannelRecord = {
    push_token_hash: await hashToken(pushToken),
    pull_token_hash: await hashToken(pullToken),
    created_at: new Date().toISOString(),
    ...(body.pubkey && { pubkey: body.pubkey }),
    ...(body.device_token && { device_token: body.device_token }),
    ...(deviceName && { device_name: deviceName }),
  };

  await kv.put(`channel:${channelId}`, JSON.stringify(channel), { expirationTtl: CHANNEL_TTL });

  return new Response(
    JSON.stringify({ channel_id: channelId, push_token: pushToken, pull_token: pullToken }),
    { status: 201, headers: { "Content-Type": "application/json" } },
  );
}

export async function pushImage(
  request: Request,
  kv: KVNamespace,
  channelId: string,
  channel: ChannelRecord,
  env: Env,
  ctx: ExecutionContext,
): Promise<Response> {
  const authError = await authenticatePush(request, channel);
  if (authError) return authError;

  if (!channel.pubkey) {
    return badRequest("Channel pairing incomplete. Waiting for device to register pubkey.");
  }

  const contentLength = request.headers.get("Content-Length");
  if (contentLength && parseInt(contentLength, 10) > MAX_PAYLOAD_SIZE) {
    return payloadTooLarge("Encrypted payload exceeds 10MB limit");
  }

  const blob = await request.arrayBuffer();
  if (blob.byteLength > MAX_PAYLOAD_SIZE) {
    return payloadTooLarge("Encrypted payload exceeds 10MB limit");
  }

  const imageId = crypto.randomUUID();
  const createdAt = new Date().toISOString();

  await Promise.all([
    kv.put(`image:${channelId}:${imageId}`, blob, { expirationTtl: IMAGE_TTL }),
    kv.put(
      `image_meta:${channelId}:${imageId}`,
      JSON.stringify({ size: blob.byteLength, created_at: createdAt }),
      { expirationTtl: IMAGE_TTL },
    ),
    // Refresh channel TTL on push
    kv.put(`channel:${channelId}`, JSON.stringify(channel), { expirationTtl: CHANNEL_TTL }),
  ]);

  // Fire-and-forget APNs notification via waitUntil
  if (channel.device_token) {
    ctx.waitUntil(sendPushNotification(env, channel.device_token, channelId, imageId));
  }

  return new Response(JSON.stringify({ id: imageId, size: blob.byteLength, created_at: createdAt }), {
    status: 201,
    headers: { "Content-Type": "application/json" },
  });
}

export async function listImages(
  request: Request,
  kv: KVNamespace,
  channelId: string,
  channel: ChannelRecord,
): Promise<Response> {
  const authError = await authenticatePull(request, channel);
  if (authError) return authError;

  const list = await kv.list({ prefix: `image_meta:${channelId}:` });

  const images = await Promise.all(
    list.keys.map(async (key) => {
      const meta = await kv.get<{ size: number; created_at: string }>(key.name, "json");
      const id = key.name.split(":")[2];
      return meta ? { id, size: meta.size, created_at: meta.created_at } : null;
    }),
  );

  return new Response(JSON.stringify({ images: images.filter(Boolean) }), {
    headers: { "Content-Type": "application/json" },
  });
}

export async function getImage(
  request: Request,
  kv: KVNamespace,
  channelId: string,
  imageId: string,
  channel: ChannelRecord,
): Promise<Response> {
  const authError = await authenticatePull(request, channel);
  if (authError) return authError;

  const blob = await kv.get(`image:${channelId}:${imageId}`, "arrayBuffer");
  if (!blob) return notFound("Image not found");

  return new Response(blob, {
    headers: { "Content-Type": "application/octet-stream" },
  });
}

export async function deleteImage(
  request: Request,
  kv: KVNamespace,
  channelId: string,
  imageId: string,
  channel: ChannelRecord,
): Promise<Response> {
  const authError = await authenticatePull(request, channel);
  if (authError) return authError;

  await kv.delete(`image:${channelId}:${imageId}`);
  await kv.delete(`image_meta:${channelId}:${imageId}`);

  return new Response(null, { status: 204 });
}

export async function deleteChannel(
  request: Request,
  kv: KVNamespace,
  channelId: string,
  channel: ChannelRecord,
): Promise<Response> {
  const authError = await authenticatePull(request, channel);
  if (authError) return authError;

  // Delete all images and metadata
  const [imageKeys, metaKeys] = await Promise.all([
    kv.list({ prefix: `image:${channelId}:` }),
    kv.list({ prefix: `image_meta:${channelId}:` }),
  ]);

  await Promise.all([
    ...imageKeys.keys.map((key) => kv.delete(key.name)),
    ...metaKeys.keys.map((key) => kv.delete(key.name)),
    kv.delete(`channel:${channelId}`),
  ]);

  return new Response(null, { status: 204 });
}

export async function getChannelPubkey(
  request: Request,
  channel: ChannelRecord,
): Promise<Response> {
  const authError = await authenticatePush(request, channel);
  if (authError) return authError;

  if (!channel.pubkey) {
    return new Response(JSON.stringify({ status: "pending" }), {
      status: 202,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ pubkey: channel.pubkey }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

export async function registerChannel(
  request: Request,
  kv: KVNamespace,
  channelId: string,
  channel: ChannelRecord,
): Promise<Response> {
  const authError = await authenticatePull(request, channel);
  if (authError) return authError;

  if (channel.pubkey) {
    return badRequest("Channel already registered");
  }

  const body = await request.json<{ pubkey?: string; device_token?: string; device_name?: string }>().catch(() => null);
  if (!body?.pubkey || !body?.device_token) {
    return badRequest("pubkey and device_token are required");
  }

  const deviceName = truncateDeviceName(body.device_name);

  const updatedChannel: ChannelRecord = {
    ...channel,
    pubkey: body.pubkey,
    device_token: body.device_token,
    ...(deviceName && { device_name: deviceName }),
  };

  await kv.put(`channel:${channelId}`, JSON.stringify(updatedChannel), { expirationTtl: CHANNEL_TTL });

  return new Response(JSON.stringify({ status: "registered" }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

interface Env {
  KV: KVNamespace;
  APNS_KEY?: string;
  APNS_KEY_ID?: string;
  APNS_TEAM_ID?: string;
  APNS_ENVIRONMENT?: string;
}
