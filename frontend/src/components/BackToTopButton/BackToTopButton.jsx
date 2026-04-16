import styles from './BackToTopButton.module.scss';

function scrollToPageTop() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  window.scrollTo({
    top: 0,
    left: 0,
    behavior: prefersReducedMotion ? 'auto' : 'smooth',
  });
}

export default function BackToTopButton() {
  return (
    <button
      type="button"
      className={styles.backToTop}
      onClick={scrollToPageTop}
      aria-label="Back to top"
    >
      &#8593;
    </button>
  );
}
