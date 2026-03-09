interface RateLimitConfig {
  maxRequests: number;
  windowSeconds: number;
}

const RATE_LIMITS: Record<string, RateLimitConfig> = {
  push: { maxRequests: 100, windowSeconds: 3600 },
  pull: { maxRequests: 300, windowSeconds: 3600 },
  channel_create: { maxRequests: 10, windowSeconds: 3600 },
};

export async function checkRateLimit(
  kv: KVNamespace,
  key: string,
  limitType: keyof typeof RATE_LIMITS,
): Promise<{ allowed: boolean; retryAfter: number }> {
  const config = RATE_LIMITS[limitType];
  const kvKey = `ratelimit:${limitType}:${key}`;

  const stored = await kv.get<{ count: number; windowStart: number }>(kvKey, "json");
  const now = Math.floor(Date.now() / 1000);

  if (!stored || now - stored.windowStart >= config.windowSeconds) {
    await kv.put(kvKey, JSON.stringify({ count: 1, windowStart: now }), {
      expirationTtl: config.windowSeconds,
    });
    return { allowed: true, retryAfter: 0 };
  }

  if (stored.count >= config.maxRequests) {
    const retryAfter = config.windowSeconds - (now - stored.windowStart);
    return { allowed: false, retryAfter };
  }

  const remainingTtl = config.windowSeconds - (now - stored.windowStart);
  await kv.put(kvKey, JSON.stringify({ count: stored.count + 1, windowStart: stored.windowStart }), {
    expirationTtl: Math.max(remainingTtl, 60),
  });
  return { allowed: true, retryAfter: 0 };
}
