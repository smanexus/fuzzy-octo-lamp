// Client-side Web Push subscription flow for a person's page.
(function () {
  const root = document.getElementById("push-controls");
  if (!root) return;

  const slug = root.dataset.slug;
  const btn = document.getElementById("push-toggle");
  const testBtn = document.getElementById("push-test");
  const status = document.getElementById("push-status");

  const supported =
    "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

  if (!supported) {
    setState("unsupported", "Seu navegador não suporta notificações. No iPhone, adicione o app à tela de início primeiro.");
    return;
  }

  function setState(state, message) {
    root.dataset.state = state;
    if (message) status.textContent = message;
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    const output = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) output[i] = raw.charCodeAt(i);
    return output;
  }

  async function currentSubscription() {
    const reg = await navigator.serviceWorker.ready;
    return reg.pushManager.getSubscription();
  }

  async function refresh() {
    const sub = await currentSubscription();
    if (sub && Notification.permission === "granted") {
      setState("on", "Notificações ativadas neste aparelho.");
    } else {
      setState("off", "Ative para receber o aviso da sua escala no fim de semana.");
    }
  }

  async function subscribe() {
    setState("working", "Ativando…");
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setState("off", "Permissão negada. Você pode liberar nas configurações do navegador.");
        return;
      }
      const reg = await navigator.serviceWorker.ready;
      const keyResp = await fetch("/api/vapid-public-key");
      const { publicKey } = await keyResp.json();
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
      const resp = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug: slug, subscription: sub }),
      });
      if (!resp.ok) throw new Error("falha ao registrar");
      setState("on", "Notificações ativadas neste aparelho.");
    } catch (e) {
      setState("off", "Não foi possível ativar. Tente novamente.");
      console.error(e);
    }
  }

  async function unsubscribe() {
    setState("working", "Desativando…");
    try {
      const sub = await currentSubscription();
      if (sub) {
        await fetch("/api/unsubscribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ endpoint: sub.endpoint }),
        });
        await sub.unsubscribe();
      }
      setState("off", "Notificações desativadas neste aparelho.");
    } catch (e) {
      setState("off", "Erro ao desativar.");
      console.error(e);
    }
  }

  btn.addEventListener("click", () => {
    if (root.dataset.state === "on") {
      unsubscribe();
    } else {
      subscribe();
    }
  });

  if (testBtn) {
    testBtn.addEventListener("click", async () => {
      testBtn.disabled = true;
      try {
        await fetch("/api/test-push", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slug: slug }),
        });
      } finally {
        setTimeout(() => (testBtn.disabled = false), 1500);
      }
    });
  }

  refresh();
})();
