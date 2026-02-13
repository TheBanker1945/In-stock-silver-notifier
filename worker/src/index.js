const KEYBOARD = {
  inline_keyboard: [
    [
      { text: "📊 Status", callback_data: "/status" },
      { text: "💰 Price", callback_data: "/price" },
    ],
    [
      { text: "🔔 Deals", callback_data: "/deals" },
      { text: "🔑 Keys", callback_data: "/keys" },
    ],
    [{ text: "🚀 Force Scrape", callback_data: "/force" }],
  ],
};

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("OK", { status: 200 });
    }

    try {
      const update = await request.json();
      const allowedChats = env.TELEGRAM_CHAT_ID.split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      // Handle callback queries (button taps)
      if (update.callback_query) {
        const cb = update.callback_query;
        const chatId = String(cb.message.chat.id);
        if (!allowedChats.includes(chatId)) {
          return new Response("Unauthorized", { status: 403 });
        }

        const command = cb.data;
        const handler = HANDLERS[command];
        if (handler) {
          let reply;
          try {
            reply = await handler(env);
          } catch (err) {
            console.error("Handler error:", err);
            reply = `Error: ${err.message}`;
          }
          await sendTelegram(env, chatId, reply);
        }

        // Acknowledge the callback to remove the loading spinner
        await fetch(
          `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/answerCallbackQuery`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ callback_query_id: cb.id }),
          }
        );

        return new Response("OK");
      }

      // Handle text messages
      const message = update.message || update.channel_post;
      if (!message || !message.text) return new Response("OK");

      const chatId = String(message.chat.id);
      if (!allowedChats.includes(chatId)) {
        return new Response("Unauthorized", { status: 403 });
      }

      const command = message.text.split("@")[0].trim().toLowerCase();

      if (command === "/start" || command === "/menu") {
        await sendTelegram(
          env,
          chatId,
          "<b>SilverScout</b>\n\nChoose a command:",
          KEYBOARD
        );
        return new Response("OK");
      }

      const handler = HANDLERS[command];
      if (!handler) return new Response("OK");

      let reply;
      try {
        reply = await handler(env);
      } catch (err) {
        console.error("Handler error:", err);
        reply = `Error: ${err.message}`;
      }
      await sendTelegram(env, chatId, reply, KEYBOARD);

      return new Response("OK");
    } catch (err) {
      console.error("Worker error:", err);
      return new Response("Error", { status: 500 });
    }
  },
};

const HANDLERS = {
  "/status": handleStatus,
  "/price": handlePrice,
  "/deals": handleDeals,
  "/keys": handleKeys,
  "/force": handleForce,
};

async function fetchGistFiles(env) {
  const resp = await fetch(`https://api.github.com/gists/${env.GIST_ID}`, {
    headers: {
      Authorization: `token ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "SilverScout-Worker",
    },
  });
  if (!resp.ok) throw new Error(`Gist fetch failed: ${resp.status}`);
  const gist = await resp.json();
  const files = {};
  for (const [name, file] of Object.entries(gist.files)) {
    try {
      files[name] = JSON.parse(file.content);
    } catch {
      files[name] = file.content;
    }
  }
  return files;
}

async function sendTelegram(env, chatId, text, replyMarkup) {
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: "HTML",
    disable_web_page_preview: true,
  };
  if (replyMarkup) {
    body.reply_markup = replyMarkup;
  }
  await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
}

async function handleStatus(env) {
  const files = await fetchGistFiles(env);
  const cache = files["spot_price_cache.json"];
  const usage = files["api_usage.json"];

  let spotInfo = "No cached price";
  if (cache && cache.price && cache.fetched_at) {
    const ageMs = Date.now() - cache.fetched_at * 1000;
    const ageMin = Math.round(ageMs / 60000);
    const refreshMin = Math.max(0, 180 - ageMin);
    spotInfo =
      `€${cache.price.toFixed(2)}/oz\n` +
      `Cache age: ${ageMin} min\n` +
      `Refreshes in: ~${refreshMin} min`;
  }

  let keyInfo = "No usage data";
  if (usage && usage.keys) {
    const numKeys = Object.keys(usage.keys).length;
    const totalUsed = Object.values(usage.keys).reduce((a, b) => a + b, 0);
    const totalLimit = numKeys * 100;
    keyInfo = `${totalLimit - totalUsed}/${totalLimit} requests left (${numKeys} key(s))`;
  }

  return `<b>📊 SilverScout Status</b>\n\n${spotInfo}\n\nAPI: ${keyInfo}`;
}

async function handlePrice(env) {
  const files = await fetchGistFiles(env);
  const cache = files["spot_price_cache.json"];

  if (!cache || !cache.price) {
    return "<b>💰 Spot Price</b>\n\nNo cached price available. Wait for next scrape run.";
  }

  const maxPrice = cache.price + 15;
  return (
    `<b>💰 Spot Price</b>\n\n` +
    `Spot: €${cache.price.toFixed(2)}/oz\n` +
    `Max premium: €15.00/oz\n` +
    `Max acceptable: €${maxPrice.toFixed(2)}/oz\n` +
    `Hard cap: €2,500.00`
  );
}

async function handleDeals(env) {
  const files = await fetchGistFiles(env);
  const deals = files["notified_deals.json"];

  if (!deals || Object.keys(deals).length === 0) {
    return "<b>🔔 Recent Deals</b>\n\nNo deals tracked yet.";
  }

  let text = "<b>🔔 Recent Deals</b>\n";
  const entries = Object.entries(deals).slice(-10);
  for (const [url, info] of entries) {
    const name = info.name || url.split("/").pop();
    text += `\n• €${info.price_per_oz?.toFixed(2) || "?"}/oz — <a href="${url}">${name}</a>`;
  }
  return text;
}

async function handleKeys(env) {
  const files = await fetchGistFiles(env);
  const usage = files["api_usage.json"];

  if (!usage || !usage.keys) {
    return "<b>🔑 API Keys</b>\n\nNo usage data available.";
  }

  let text = `<b>🔑 API Keys</b>\n\nMonth: ${usage.month}\n`;
  for (const [keyId, count] of Object.entries(usage.keys)) {
    text += `\nKey ...${keyId}: ${count}/100 used`;
  }
  return text;
}

async function handleForce(env) {
  const [owner, repo] = env.GITHUB_REPO.split("/");
  const resp = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/scrape.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `token ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "SilverScout-Worker",
      },
      body: JSON.stringify({ ref: "main" }),
    }
  );

  if (resp.ok || resp.status === 204) {
    return "✅ Scrape triggered! Results in ~1 min.";
  }
  return `❌ Failed to trigger scrape (HTTP ${resp.status})`;
}
