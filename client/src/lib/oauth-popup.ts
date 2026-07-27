import { api } from "@/lib/api";

export type OAuthPopupResult =
  | { success: true }
  | { success: false; error: string };

const POPUP_FEATURES = "width=600,height=700";
const STATUS_POLL_MS = 1000;
const CLOSED_CHECK_MS = 400;

/**
 * Authorize a source, open the provider URL in a popup, wait for success via
 * postMessage `{ type: "oauth_complete" }` and/or connection-status polling
 * (Salesforce often clears window.opener after redirects).
 */
export async function connectSourceViaOAuth(
  sourceId: string,
  projectId: string,
): Promise<OAuthPopupResult> {
  // Open synchronously with the click gesture so the popup is not blocked and
  // the chat tab remains a reliable opener that can close the window later.
  const popup = window.open("about:blank", "oauth_popup", POPUP_FEATURES);
  if (!popup) {
    // Popup blocked (common in embedded browsers). If tokens were already
    // saved from a prior attempt, still allow the interrupt to resume.
    try {
      const status = await api.getSourceConnectionStatus(sourceId, projectId);
      if (status.connected) {
        return { success: true };
      }
    } catch {
      // fall through
    }
    return {
      success: false,
      error: "Popup was blocked. Please allow popups for this site.",
    };
  }
  const oauthWindow = popup;

  try {
    const { auth_url } = await api.authorizeConnection(sourceId, projectId);
    oauthWindow.location.href = auth_url;
  } catch (err) {
    try {
      oauthWindow.close();
    } catch {
      // ignore
    }
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to start OAuth.",
    };
  }

  return new Promise((resolve) => {
    let settled = false;
    let closedPoll: ReturnType<typeof setInterval> | undefined;
    let statusPoll: ReturnType<typeof setInterval> | undefined;

    function finish(result: OAuthPopupResult) {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", onMessage);
      if (closedPoll !== undefined) clearInterval(closedPoll);
      if (statusPoll !== undefined) clearInterval(statusPoll);
      try {
        if (!oauthWindow.closed) oauthWindow.close();
      } catch {
        // ignore
      }
      resolve(result);
    }

    function onMessage(event: MessageEvent) {
      if (event.data?.type !== "oauth_complete") return;
      if (event.data.success) {
        finish({ success: true });
      } else {
        finish({
          success: false,
          error:
            typeof event.data.error === "string" && event.data.error
              ? event.data.error
              : "Connection failed. Please try again.",
        });
      }
    }

    window.addEventListener("message", onMessage);

    statusPoll = setInterval(() => {
      void (async () => {
        if (settled) return;
        try {
          const status = await api.getSourceConnectionStatus(sourceId, projectId);
          if (status.connected) {
            finish({ success: true });
          }
        } catch {
          // keep waiting
        }
      })();
    }, STATUS_POLL_MS);

    closedPoll = setInterval(() => {
      if (!oauthWindow.closed) return;
      window.setTimeout(() => {
        if (settled) return;
        void (async () => {
          try {
            const status = await api.getSourceConnectionStatus(sourceId, projectId);
            if (status.connected) {
              finish({ success: true });
              return;
            }
          } catch {
            // fall through
          }
          finish({
            success: false,
            error: "OAuth window closed before completing.",
          });
        })();
      }, 250);
    }, CLOSED_CHECK_MS);
  });
}
