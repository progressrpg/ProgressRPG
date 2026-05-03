// SupportFlow/screens/SupportDetailScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { SUPPORT_ACTIONS } from "../supportFlowReducer";
import styles from "../SupportFlowModal.module.scss";

const ALLOWED_YOUTUBE_HOSTS = new Set([
  "www.youtube.com",
  "youtube.com",
  "www.youtube-nocookie.com",
  "youtube-nocookie.com",
]);

function getSafeEmbedUrl(url) {
  if (!url) return null;

  try {
    const parsedUrl = new URL(url);
    const isAllowedHost = ALLOWED_YOUTUBE_HOSTS.has(parsedUrl.hostname);
    const isSecure = parsedUrl.protocol === "https:";
    const isEmbedPath = parsedUrl.pathname.startsWith("/embed/");

    if (!isAllowedHost || !isSecure || !isEmbedPath) {
      return null;
    }

    return parsedUrl.toString();
  } catch {
    return null;
  }
}

export default function SupportDetailScreen({
  supportActionId,
  onBackToSupportMenu,
}) {
  const action = SUPPORT_ACTIONS[supportActionId];
  const safeVideoEmbedUrl = getSafeEmbedUrl(action?.videoEmbedUrl);
  const shouldLoadExternalVideo = import.meta.env.MODE !== "test";

  if (!action) return null;

  return (
    <div>
      <p className={styles.detailIntro}>Take your time with these steps:</p>
      {safeVideoEmbedUrl && shouldLoadExternalVideo && (
        <div className={styles.videoWrapper}>
          <iframe
            className={styles.videoEmbed}
            src={safeVideoEmbedUrl}
            title={`${action.label} guidance video`}
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      )}
      <ol className={styles.stepsList}>
        {action.steps.map((step, i) => (
          <li key={i}>{step}</li>
        ))}
      </ol>
      <ButtonFrame>
        <Button onClick={onBackToSupportMenu}>Back to support menu</Button>
      </ButtonFrame>
    </div>
  );
}
