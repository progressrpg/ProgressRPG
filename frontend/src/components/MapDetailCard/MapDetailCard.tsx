import type React from "react";
import DetailSurface from "../DetailSurface/DetailSurface";
import { DetailCardBody } from "../DetailCard/DetailCard";
import styles from "./MapDetailCard.module.scss";

interface MapDetailCardProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  onFlyTo?: () => void;
  /** Map's own wrapper element, passed through to DetailSurface so this
   * portals (and positions) relative to the map instead of the viewport -
   * see the `container` prop comment on DetailSurface. */
  container?: HTMLElement | null;
}

// Map's docked side panel (see Map's "click a tooltip -> detail card" flow) -
// reuses DetailCard's header/content layout (DetailCardBody) but, unlike
// DetailCard's centered viewport-fixed modal, docks to the map's own corner
// and stays non-modal so the map underneath stays interactive. Kept as its
// own component rather than a DetailCard variant because it needs a
// different portal target and positioning scheme, not just different CSS.
export default function MapDetailCard({
  open,
  title,
  onClose,
  children,
  onFlyTo,
  container,
}: MapDetailCardProps) {
  return (
    <DetailSurface
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title={title}
      modal={false}
      container={container}
    >
      <DetailCardBody title={title} onClose={onClose} onFlyTo={onFlyTo} className={styles.card}>
        {children}
      </DetailCardBody>
    </DetailSurface>
  );
}
