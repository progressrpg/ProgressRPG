import React, { useState, useCallback } from "react";
import Modal from "../Modal/Modal";
import Button from "../Button/Button";
import useTutorialSteps from "../../hooks/useTutorialSteps";
import { markTutorialStepsSeen } from "../../api/tutorial";
import type { TutorialStep } from "../../types";
import styles from "./TutorialModal.module.scss";

function youtubeEmbedUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    let videoId: string | null = null;
    if (parsed.hostname === "youtu.be") {
      videoId = parsed.pathname.slice(1);
    } else if (parsed.searchParams.has("v")) {
      videoId = parsed.searchParams.get("v");
    }
    return videoId
      ? `https://www.youtube-nocookie.com/embed/${videoId}`
      : null;
  } catch {
    return null;
  }
}

interface TutorialModalProps {
  onClose: () => void;
  startAtStepId?: number | null;
  onComplete?: () => void;
}

export default function TutorialModal({
  onClose,
  startAtStepId,
  onComplete,
}: TutorialModalProps) {
  const { steps, isLoading } = useTutorialSteps();
  const [currentIndex, setCurrentIndex] = useState<number>(() => {
    if (!startAtStepId || !steps.length) return 0;
    const idx = steps.findIndex((s: TutorialStep) => s.id === startAtStepId);
    return idx >= 0 ? idx : 0;
  });

  const step: TutorialStep | null = steps[currentIndex] ?? null;
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === steps.length - 1;

  const handleDone = useCallback(async () => {
    const seenIds = steps.slice(currentIndex).map((s: TutorialStep) => s.id);
    try {
      await markTutorialStepsSeen(seenIds);
    } catch {
      // Non-fatal — modal still closes
    }
    onComplete?.();
    onClose();
  }, [steps, currentIndex, onClose, onComplete]);

  if (isLoading) return null;

  if (!steps.length) {
    return (
      <Modal
        title="Tutorial"
        onClose={onClose}
        id="tutorial-modal"
        style={{ height: "min(90vh, 800px)" }}
      >
        <p className={styles.emptyState}>No tutorial content to display yet.</p>
      </Modal>
    );
  }

  const embedUrl = step ? youtubeEmbedUrl(step.youtube_url) : null;

  const footer = (
    <>
      <div className={styles.footerLeft} />
      <div className={styles.footerCenter}>
        <span
          className={isFirst ? styles.hidden : undefined}
          inert={isFirst ? true : undefined}
        >
          <Button
            onClick={() => setCurrentIndex((i) => i - 1)}
            ariaLabel="Previous step"
          >
            ←
          </Button>
        </span>
        <span
          className={styles.stepCount}
          aria-live="polite"
          aria-atomic="true"
        >
          {currentIndex + 1} / {steps.length}
        </span>
        <span
          className={isLast ? styles.hidden : undefined}
          inert={isLast ? true : undefined}
        >
          <Button
            onClick={() => setCurrentIndex((i) => i + 1)}
            ariaLabel="Next step"
          >
            →
          </Button>
        </span>
      </div>
      <div className={styles.footerRight}>
        <Button onClick={handleDone}>✓ Done</Button>
      </div>
    </>
  );

  return (
    <Modal
      title={step?.title ?? ""}
      onClose={onClose}
      footer={footer}
      id="tutorial-modal"
      size="lg"
      style={{ height: "min(90vh, 800px)" }}
    >
      <div className={styles.content}>
        {step?.image_url && (
          <img
            src={step.image_url}
            alt={step.alt_text || step.title}
            className={styles.image}
          />
        )}
        {embedUrl && (
          <div className={styles.videoWrapper}>
            <iframe
              src={embedUrl}
              title={step!.title}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        )}
        {step?.body && <p className={styles.body}>{step.body}</p>}
      </div>
    </Modal>
  );
}
