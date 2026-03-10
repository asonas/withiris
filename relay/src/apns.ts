interface ApnsConfig {
  key: string;
  keyId: string;
  teamId: string;
  environment: string;
}

function base64url(data: Uint8Array): string {
  return btoa(String.fromCharCode(...data))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function base64urlEncode(str: string): string {
  return base64url(new TextEncoder().encode(str));
}

async function importPrivateKey(pem: string): Promise<CryptoKey> {
  const pemContents = pem
    .replace(/-----BEGIN PRIVATE KEY-----/g, "")
    .replace(/-----END PRIVATE KEY-----/g, "")
    .replace(/\s/g, "");
  const binaryDer = Uint8Array.from(atob(pemContents), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey("pkcs8", binaryDer, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
}

async function generateJwt(config: ApnsConfig): Promise<string> {
  const header = base64urlEncode(JSON.stringify({ alg: "ES256", kid: config.keyId }));
  const payload = base64urlEncode(
    JSON.stringify({ iss: config.teamId, iat: Math.floor(Date.now() / 1000) }),
  );
  const signingInput = `${header}.${payload}`;

  const key = await importPrivateKey(config.key);
  const signature = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    key,
    new TextEncoder().encode(signingInput),
  );

  return `${signingInput}.${base64url(new Uint8Array(signature))}`;
}

export async function sendPushNotification(
  env: { APNS_KEY?: string; APNS_KEY_ID?: string; APNS_TEAM_ID?: string; APNS_ENVIRONMENT?: string; APNS_TOPIC?: string },
  deviceToken: string,
  channelId: string,
  imageId: string,
): Promise<void> {
  if (!env.APNS_KEY || !env.APNS_KEY_ID || !env.APNS_TEAM_ID) {
    return;
  }

  const config: ApnsConfig = {
    key: env.APNS_KEY,
    keyId: env.APNS_KEY_ID,
    teamId: env.APNS_TEAM_ID,
    environment: env.APNS_ENVIRONMENT ?? "sandbox",
  };

  const host =
    config.environment === "production" ? "api.push.apple.com" : "api.sandbox.push.apple.com";

  try {
    const jwt = await generateJwt(config);

    const response = await fetch(`https://${host}/3/device/${deviceToken}`, {
      method: "POST",
      headers: {
        authorization: `bearer ${jwt}`,
        "apns-topic": env.APNS_TOPIC ?? "com.asonas.iris",
        "apns-push-type": "alert",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        aps: {
          alert: {
            title: "Iris",
            body: "New image received",
          },
          sound: "default",
        },
        channel_id: channelId,
        image_id: imageId,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      console.error(`APNs error: status=${response.status} body=${body} token=${deviceToken.substring(0, 8)}...`);
    } else {
      console.log(`APNs success: status=${response.status}`);
    }
  } catch (e) {
    console.error(`APNs exception: ${e}`);
  }
}
