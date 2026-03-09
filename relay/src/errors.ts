export function problemResponse(
  status: number,
  type: string,
  title: string,
  detail: string,
): Response {
  return new Response(
    JSON.stringify({ type: `https://iris.example.com/errors/${type}`, title, status, detail }),
    {
      status,
      headers: { "Content-Type": "application/problem+json" },
    },
  );
}

export function notFound(detail: string): Response {
  return problemResponse(404, "not-found", "Not Found", detail);
}

export function unauthorized(detail: string): Response {
  return problemResponse(401, "unauthorized", "Unauthorized", detail);
}

export function payloadTooLarge(detail: string): Response {
  return problemResponse(413, "payload-too-large", "Payload Too Large", detail);
}

export function tooManyRequests(retryAfter: number): Response {
  const res = problemResponse(429, "too-many-requests", "Too Many Requests", "Rate limit exceeded");
  res.headers.set("Retry-After", String(retryAfter));
  return res;
}

export function badRequest(detail: string): Response {
  return problemResponse(400, "bad-request", "Bad Request", detail);
}

export function methodNotAllowed(): Response {
  return problemResponse(405, "method-not-allowed", "Method Not Allowed", "Method not allowed");
}
