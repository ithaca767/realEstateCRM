function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, "+")
    .replace(/_/g, "/");

  const rawData = window.atob(base64);

  return Uint8Array.from(
    [...rawData].map(char => char.charCodeAt(0))
  );
}


function setPushUI(enabled, message = "") {
  const button = document.getElementById("enablePushNotificationsBtn");
  const status = document.getElementById("pushNotificationStatus");

  if (!button || !status) {
    return;
  }

  if (enabled) {
    button.textContent = "Turn Off Notifications on This Device";
    button.classList.remove("btn-outline-primary");
    button.classList.add("btn-outline-secondary");
    button.dataset.pushEnabled = "true";

    status.textContent =
      message || "Notifications are enabled on this device.";
  } else {
    button.textContent = "Enable Notifications on This Device";
    button.classList.remove("btn-outline-secondary");
    button.classList.add("btn-outline-primary");
    button.dataset.pushEnabled = "false";

    status.textContent = message;
  }
}


async function getPushRegistration() {
  await navigator.serviceWorker.register(
    "/service-worker.js",
    { scope: "/" }
  );

  return navigator.serviceWorker.ready;
}


async function enablePushNotifications() {
  const button = document.getElementById("enablePushNotificationsBtn");
  const status = document.getElementById("pushNotificationStatus");

  try {
    button.disabled = true;
    status.textContent = "Requesting notification permission...";

    const permission = await Notification.requestPermission();

    if (permission !== "granted") {
      setPushUI(
        false,
        "Notification permission was not granted."
      );
      return;
    }

    status.textContent = "Registering this device...";

    const registration = await getPushRegistration();

    const keyResponse = await fetch("/api/push/public-key");
    const keyData = await keyResponse.json();

    if (!keyResponse.ok || !keyData.ok || !keyData.public_key) {
      throw new Error("Push configuration is unavailable.");
    }

    let subscription =
      await registration.pushManager.getSubscription();

    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey:
          urlBase64ToUint8Array(keyData.public_key)
      });
    }

    const saveResponse = await fetch("/api/push/subscribe", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(subscription.toJSON())
    });

    const saveData = await saveResponse.json();

    if (!saveResponse.ok || !saveData.ok) {
      throw new Error(
        saveData?.error?.message ||
        "Could not save push subscription."
      );
    }

    setPushUI(
      true,
      "Notifications are enabled on this device."
    );

  } catch (error) {
    console.error("Push notification setup failed:", error);

    setPushUI(
      false,
      error.message || "Could not enable notifications."
    );

  } finally {
    button.disabled = false;
  }
}


async function disablePushNotifications() {
  const button = document.getElementById("enablePushNotificationsBtn");
  const status = document.getElementById("pushNotificationStatus");

  try {
    button.disabled = true;
    status.textContent = "Turning off notifications...";

    const registration = await getPushRegistration();
    const subscription =
      await registration.pushManager.getSubscription();

    if (!subscription) {
      setPushUI(false, "Notifications are off on this device.");
      return;
    }

    const endpoint = subscription.endpoint;

    const response = await fetch("/api/push/unsubscribe", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ endpoint })
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(
        data?.error?.message ||
        "Could not disable notifications."
      );
    }

    const unsubscribed = await subscription.unsubscribe();

    if (!unsubscribed) {
      throw new Error(
        "The browser could not remove the push subscription."
      );
    }

    setPushUI(
      false,
      "Notifications are off on this device."
    );

  } catch (error) {
    console.error("Push notification disable failed:", error);

    status.textContent =
      error.message || "Could not disable notifications.";

  } finally {
    button.disabled = false;
  }
}


async function initializePushNotifications() {
  const button = document.getElementById("enablePushNotificationsBtn");

  if (!button) {
    return;
  }

  if (
    !("Notification" in window) ||
    !("serviceWorker" in navigator) ||
    !("PushManager" in window)
  ) {
    button.disabled = true;

    setPushUI(
      false,
      "Push notifications are not supported on this device."
    );

    return;
  }

  try {
    const registration = await getPushRegistration();
    const subscription =
      await registration.pushManager.getSubscription();

    if (subscription) {
      setPushUI(true);
    } else if (Notification.permission === "denied") {
      button.disabled = true;

      setPushUI(
        false,
        "Notifications are blocked in your browser settings."
      );
    } else {
      setPushUI(false);
    }

  } catch (error) {
    console.error(
      "Could not determine push notification state:",
      error
    );

    setPushUI(
      false,
      "Could not determine notification status."
    );
  }
}


document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("enablePushNotificationsBtn");

  if (!button) {
    return;
  }

  button.addEventListener("click", async () => {
    if (button.dataset.pushEnabled === "true") {
      await disablePushNotifications();
    } else {
      await enablePushNotifications();
    }
  });

  initializePushNotifications();
});
