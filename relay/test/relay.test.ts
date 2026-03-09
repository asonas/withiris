import { env, SELF } from "cloudflare:test";
import { describe, it, expect, beforeEach } from "vitest";

const BASE = "http://localhost";

async function createChannel(
  pubkey = "dGVzdC1wdWJrZXk=",
  deviceToken = "test-device-token",
) {
  const res = await SELF.fetch(`${BASE}/channels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pubkey, device_token: deviceToken }),
  });
  return {
    res,
    data: (await res.json()) as {
      channel_id: string;
      push_token: string;
      pull_token: string;
    },
  };
}

describe("POST /channels", () => {
  it("creates a channel and returns tokens", async () => {
    const { res, data } = await createChannel();

    expect(res.status).toBe(201);
    expect(data.channel_id).toBeDefined();
    expect(data.push_token).toHaveLength(64);
    expect(data.pull_token).toHaveLength(64);
    expect(data.push_token).not.toBe(data.pull_token);
  });

  it("creates a channel without pubkey/device_token (CLI-initiated pairing)", async () => {
    const res = await SELF.fetch(`${BASE}/channels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    expect(res.status).toBe(201);
    const data = (await res.json()) as {
      channel_id: string;
      push_token: string;
      pull_token: string;
    };
    expect(data.channel_id).toBeDefined();
    expect(data.push_token).toHaveLength(64);
    expect(data.pull_token).toHaveLength(64);
  });

  it("creates a channel with only pubkey (device_token omitted)", async () => {
    const res = await SELF.fetch(`${BASE}/channels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pubkey: "key" }),
    });

    expect(res.status).toBe(201);
    const data = (await res.json()) as { channel_id: string };
    expect(data.channel_id).toBeDefined();
  });

  it("creates a channel with only device_token (pubkey omitted)", async () => {
    const res = await SELF.fetch(`${BASE}/channels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_token: "token" }),
    });

    expect(res.status).toBe(201);
    const data = (await res.json()) as { channel_id: string };
    expect(data.channel_id).toBeDefined();
  });

  it("creates a channel with device_name", async () => {
    const res = await SELF.fetch(`${BASE}/channels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_name: "my-laptop" }),
    });

    expect(res.status).toBe(201);

    // Verify device_name is stored in KV
    const data = (await res.json()) as { channel_id: string; push_token: string };
    const stored = await env.KV.get<{ device_name?: string }>(`channel:${data.channel_id}`, "json");
    expect(stored?.device_name).toBe("my-laptop");
  });

  it("truncates device_name to 64 characters", async () => {
    const longName = "a".repeat(100);
    const res = await SELF.fetch(`${BASE}/channels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_name: longName }),
    });

    expect(res.status).toBe(201);
    const data = (await res.json()) as { channel_id: string };
    const stored = await env.KV.get<{ device_name?: string }>(`channel:${data.channel_id}`, "json");
    expect(stored?.device_name).toHaveLength(64);
  });
});

describe("POST /channels/:id/images", () => {
  it("stores an encrypted blob", async () => {
    const { data: channel } = await createChannel();
    const blob = new Uint8Array([1, 2, 3, 4, 5]);

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${channel.push_token}`,
          "Content-Type": "application/octet-stream",
        },
        body: blob,
      },
    );

    expect(res.status).toBe(201);
    const data = (await res.json()) as {
      id: string;
      size: number;
      created_at: string;
    };
    expect(data.id).toBeDefined();
    expect(data.size).toBe(5);
  });

  it("returns 400 when channel has no pubkey (pairing incomplete)", async () => {
    const { data: channel } = await createChannelWithoutPubkey();
    const blob = new Uint8Array([1, 2, 3]);

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${channel.push_token}`,
          "Content-Type": "application/octet-stream",
        },
        body: blob,
      },
    );

    expect(res.status).toBe(400);
    const body = (await res.json()) as { detail: string };
    expect(body.detail).toContain("pairing");
  });

  it("returns 401 with invalid token", async () => {
    const { data: channel } = await createChannel();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: {
          Authorization: "Bearer invalid-token",
          "Content-Type": "application/octet-stream",
        },
        body: new Uint8Array([1]),
      },
    );

    expect(res.status).toBe(401);
  });

  it("returns 401 with pull_token (wrong token type)", async () => {
    const { data: channel } = await createChannel();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${channel.pull_token}`,
          "Content-Type": "application/octet-stream",
        },
        body: new Uint8Array([1]),
      },
    );

    expect(res.status).toBe(401);
  });

  it("returns 401 without Authorization header", async () => {
    const { data: channel } = await createChannel();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: new Uint8Array([1]),
      },
    );

    expect(res.status).toBe(401);
  });

  it("returns 404 for non-existent channel", async () => {
    const res = await SELF.fetch(
      `${BASE}/channels/non-existent-id/images`,
      {
        method: "POST",
        headers: {
          Authorization: "Bearer some-token",
          "Content-Type": "application/octet-stream",
        },
        body: new Uint8Array([1]),
      },
    );

    expect(res.status).toBe(404);
  });
});

describe("GET /channels/:id/images", () => {
  it("lists image metadata", async () => {
    const { data: channel } = await createChannel();

    // Push two images
    for (const byte of [1, 2]) {
      await SELF.fetch(
        `${BASE}/channels/${channel.channel_id}/images`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${channel.push_token}`,
            "Content-Type": "application/octet-stream",
          },
          body: new Uint8Array([byte]),
        },
      );
    }

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );

    expect(res.status).toBe(200);
    const data = (await res.json()) as {
      images: Array<{ id: string; size: number; created_at: string }>;
    };
    expect(data.images).toHaveLength(2);
    expect(data.images[0].id).toBeDefined();
    expect(data.images[0].size).toBe(1);
  });

  it("returns 401 with push_token (wrong token type)", async () => {
    const { data: channel } = await createChannel();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        headers: { Authorization: `Bearer ${channel.push_token}` },
      },
    );

    expect(res.status).toBe(401);
  });
});

describe("GET /channels/:id/images/:image_id", () => {
  it("returns the encrypted blob", async () => {
    const { data: channel } = await createChannel();
    const originalBlob = new Uint8Array([10, 20, 30, 40, 50]);

    const pushRes = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${channel.push_token}`,
          "Content-Type": "application/octet-stream",
        },
        body: originalBlob,
      },
    );
    const { id: imageId } = (await pushRes.json()) as { id: string };

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images/${imageId}`,
      {
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );

    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("application/octet-stream");
    const body = new Uint8Array(await res.arrayBuffer());
    expect(body).toEqual(originalBlob);
  });

  it("returns 404 for non-existent image", async () => {
    const { data: channel } = await createChannel();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images/non-existent`,
      {
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );

    expect(res.status).toBe(404);
  });
});

describe("DELETE /channels/:id/images/:image_id", () => {
  it("deletes a single image", async () => {
    const { data: channel } = await createChannel();

    const pushRes = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${channel.push_token}`,
          "Content-Type": "application/octet-stream",
        },
        body: new Uint8Array([1, 2, 3]),
      },
    );
    const { id: imageId } = (await pushRes.json()) as { id: string };

    const deleteRes = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images/${imageId}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );

    expect(deleteRes.status).toBe(204);

    // Verify image is gone
    const getRes = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images/${imageId}`,
      {
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );
    expect(getRes.status).toBe(404);
  });
});

describe("DELETE /channels/:id", () => {
  it("deletes channel and all images", async () => {
    const { data: channel } = await createChannel();

    // Push an image
    await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${channel.push_token}`,
          "Content-Type": "application/octet-stream",
        },
        body: new Uint8Array([1]),
      },
    );

    const deleteRes = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );

    expect(deleteRes.status).toBe(204);

    // Verify channel is gone
    const listRes = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/images`,
      {
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );
    expect(listRes.status).toBe(404);
  });

  it("returns 401 with push_token", async () => {
    const { data: channel } = await createChannel();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${channel.push_token}` },
      },
    );

    expect(res.status).toBe(401);
  });
});

// Helper: create a channel without pubkey (CLI-initiated)
async function createChannelWithoutPubkey() {
  const res = await SELF.fetch(`${BASE}/channels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return {
    res,
    data: (await res.json()) as {
      channel_id: string;
      push_token: string;
      pull_token: string;
    },
  };
}

describe("PUT /channels/:id/register", () => {
  it("registers pubkey and device_token with valid pull_token", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${channel.pull_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pubkey: "dGVzdC1wdWJrZXk=",
          device_token: "test-device-token",
        }),
      },
    );

    expect(res.status).toBe(200);
    const body = (await res.json()) as { status: string };
    expect(body.status).toBe("registered");
  });

  it("returns 401 without Authorization header", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pubkey: "dGVzdC1wdWJrZXk=",
          device_token: "test-device-token",
        }),
      },
    );

    expect(res.status).toBe(401);
  });

  it("returns 401 with push_token (wrong token type)", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${channel.push_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pubkey: "dGVzdC1wdWJrZXk=",
          device_token: "test-device-token",
        }),
      },
    );

    expect(res.status).toBe(401);
  });

  it("returns 400 when pubkey is missing", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${channel.pull_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ device_token: "test-device-token" }),
      },
    );

    expect(res.status).toBe(400);
  });

  it("returns 400 when channel already has pubkey", async () => {
    const { data: channel } = await createChannel();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${channel.pull_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pubkey: "bmV3LXB1YmtleQ==",
          device_token: "new-device-token",
        }),
      },
    );

    expect(res.status).toBe(400);
  });

  it("returns 404 for non-existent channel", async () => {
    const res = await SELF.fetch(
      `${BASE}/channels/non-existent-id/register`,
      {
        method: "PUT",
        headers: {
          Authorization: "Bearer some-token",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pubkey: "dGVzdC1wdWJrZXk=",
          device_token: "test-device-token",
        }),
      },
    );

    expect(res.status).toBe(404);
  });

  it("stores device_name from register request", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${channel.pull_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pubkey: "dGVzdC1wdWJrZXk=",
          device_token: "test-device-token",
          device_name: "my-iphone",
        }),
      },
    );

    expect(res.status).toBe(200);
    const stored = await env.KV.get<{ device_name?: string }>(`channel:${channel.channel_id}`, "json");
    expect(stored?.device_name).toBe("my-iphone");
  });

  it("truncates device_name to 64 characters in register", async () => {
    const { data: channel } = await createChannelWithoutPubkey();
    const longName = "b".repeat(100);

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${channel.pull_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pubkey: "dGVzdC1wdWJrZXk=",
          device_token: "test-device-token",
          device_name: longName,
        }),
      },
    );

    expect(res.status).toBe(200);
    const stored = await env.KV.get<{ device_name?: string }>(`channel:${channel.channel_id}`, "json");
    expect(stored?.device_name).toHaveLength(64);
  });
});

describe("GET /channels/:id/pubkey", () => {
  it("returns 202 when pubkey is not yet registered", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/pubkey`,
      {
        headers: { Authorization: `Bearer ${channel.push_token}` },
      },
    );

    expect(res.status).toBe(202);
    const body = (await res.json()) as { status: string };
    expect(body.status).toBe("pending");
  });

  it("returns 200 with pubkey after registration", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    // Register pubkey first
    await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/register`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${channel.pull_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pubkey: "dGVzdC1wdWJrZXk=",
          device_token: "test-device-token",
        }),
      },
    );

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/pubkey`,
      {
        headers: { Authorization: `Bearer ${channel.push_token}` },
      },
    );

    expect(res.status).toBe(200);
    const body = (await res.json()) as { pubkey: string };
    expect(body.pubkey).toBe("dGVzdC1wdWJrZXk=");
  });

  it("returns 401 without Authorization header", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/pubkey`,
    );

    expect(res.status).toBe(401);
  });

  it("returns 401 with pull_token (wrong token type)", async () => {
    const { data: channel } = await createChannelWithoutPubkey();

    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}/pubkey`,
      {
        headers: { Authorization: `Bearer ${channel.pull_token}` },
      },
    );

    expect(res.status).toBe(401);
  });
});

describe("Error responses", () => {
  it("returns RFC 9457 Problem Details format", async () => {
    // Use a non-existent channel to trigger 404 as an example of Problem Details
    const res = await SELF.fetch(`${BASE}/channels/non-existent/images`, {
      method: "POST",
      headers: {
        Authorization: "Bearer some-token",
        "Content-Type": "application/octet-stream",
      },
      body: new Uint8Array([1]),
    });

    expect(res.status).toBe(404);
    expect(res.headers.get("Content-Type")).toBe("application/problem+json");
    const body = (await res.json()) as {
      type: string;
      title: string;
      status: number;
      detail: string;
    };
    expect(body.type).toContain("https://iris.example.com/errors/");
    expect(body.title).toBeDefined();
    expect(body.status).toBe(404);
    expect(body.detail).toBeDefined();
  });

  it("returns 404 for unknown paths", async () => {
    const res = await SELF.fetch(`${BASE}/unknown`);
    expect(res.status).toBe(404);
  });

  it("returns 405 for wrong method", async () => {
    const { data: channel } = await createChannel();
    const res = await SELF.fetch(
      `${BASE}/channels/${channel.channel_id}`,
      { method: "GET" },
    );
    expect(res.status).toBe(405);
  });
});

describe("GET /health", () => {
  it("returns 200 with status and commit hash", async () => {
    const res = await SELF.fetch(`${BASE}/health`);
    expect(res.status).toBe(200);
    const data = (await res.json()) as { status: string; commit: string };
    expect(data.status).toBe("ok");
    expect(data.commit).toBeDefined();
    expect(typeof data.commit).toBe("string");
  });
});
