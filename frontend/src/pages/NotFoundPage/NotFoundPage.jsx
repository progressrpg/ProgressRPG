import { Link } from "react-router-dom";
import Button from "../../components/Button/Button";
import styles from "./NotFoundPage.module.scss";

export default function NotFoundPage() {
  return (
    <main className={styles.page}>
      <p className={styles.code}>404</p>
      <h1>Page not found</h1>
      <p className={styles.copy}>
        The page you are looking for does not exist or has moved.
      </p>
      <div className={styles.actions}>
        <Button as="a" href="/timer" variant="primary">Go to timer</Button>
      </div>
    </main>
  );
}
