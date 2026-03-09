import type { ChannelRecord } from "./auth";
import { badRequest, methodNotAllowed, notFound, tooManyRequests } from "./errors";
import {
  createChannel,
  deleteChannel,
  deleteImage,
  getChannelPubkey,
  getImage,
  listImages,
  pushImage,
  registerChannel,
} from "./handlers";
import { checkRateLimit } from "./rate-limit";

declare const GIT_COMMIT: string;

interface Env {
  KV: KVNamespace;
  APNS_KEY?: string;
  APNS_KEY_ID?: string;
  APNS_TEAM_ID?: string;
  APNS_ENVIRONMENT?: string;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // GET /health
    if (path === "/health" && method === "GET") {
      return new Response(JSON.stringify({ status: "ok", commit: GIT_COMMIT }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // POST /channels
    if (path === "/channels" && method === "POST") {
      const clientIp = request.headers.get("CF-Connecting-IP") ?? "unknown";
      const rateCheck = await checkRateLimit(env.KV, clientIp, "channel_create");
      if (!rateCheck.allowed) return tooManyRequests(rateCheck.retryAfter);
      return createChannel(request, env.KV);
    }

    // Match /channels/:id/register
    const registerMatch = path.match(/^\/channels\/([^/]+)\/register$/);
    if (registerMatch) {
      const [, channelId] = registerMatch;
      const channel = await env.KV.get<ChannelRecord>(`channel:${channelId}`, "json");
      if (!channel) return notFound("Channel not found");
      if (method === "PUT") return registerChannel(request, env.KV, channelId, channel);
      return methodNotAllowed();
    }

    // Match /channels/:id/pubkey
    const pubkeyMatch = path.match(/^\/channels\/([^/]+)\/pubkey$/);
    if (pubkeyMatch) {
      const [, channelId] = pubkeyMatch;
      const channel = await env.KV.get<ChannelRecord>(`channel:${channelId}`, "json");
      if (!channel) return notFound("Channel not found");
      if (method === "GET") return getChannelPubkey(request, channel);
      return methodNotAllowed();
    }

    // Match /channels/:id/images/:image_id
    const imageMatch = path.match(/^\/channels\/([^/]+)\/images\/([^/]+)$/);
    if (imageMatch) {
      const [, channelId, imageId] = imageMatch;
      const channel = await env.KV.get<ChannelRecord>(`channel:${channelId}`, "json");
      if (!channel) return notFound("Channel not found");

      if (method === "GET") {
        const rateCheck = await checkRateLimit(env.KV, channelId, "pull");
        if (!rateCheck.allowed) return tooManyRequests(rateCheck.retryAfter);
        return getImage(request, env.KV, channelId, imageId, channel);
      }
      if (method === "DELETE") {
        return deleteImage(request, env.KV, channelId, imageId, channel);
      }
      return methodNotAllowed();
    }

    // Match /channels/:id/images
    const imagesMatch = path.match(/^\/channels\/([^/]+)\/images$/);
    if (imagesMatch) {
      const [, channelId] = imagesMatch;
      const channel = await env.KV.get<ChannelRecord>(`channel:${channelId}`, "json");
      if (!channel) return notFound("Channel not found");

      if (method === "POST") {
        const rateCheck = await checkRateLimit(env.KV, channelId, "push");
        if (!rateCheck.allowed) return tooManyRequests(rateCheck.retryAfter);
        return pushImage(request, env.KV, channelId, channel, env, ctx);
      }
      if (method === "GET") {
        const rateCheck = await checkRateLimit(env.KV, channelId, "pull");
        if (!rateCheck.allowed) return tooManyRequests(rateCheck.retryAfter);
        return listImages(request, env.KV, channelId, channel);
      }
      return methodNotAllowed();
    }

    // Match /channels/:id
    const channelMatch = path.match(/^\/channels\/([^/]+)$/);
    if (channelMatch) {
      const [, channelId] = channelMatch;
      if (method === "DELETE") {
        const channel = await env.KV.get<ChannelRecord>(`channel:${channelId}`, "json");
        if (!channel) return notFound("Channel not found");
        return deleteChannel(request, env.KV, channelId, channel);
      }
      return methodNotAllowed();
    }

    return notFound("Not found");
  },
};
