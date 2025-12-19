import { useState } from "react";
import Button from "../../Button/Button";
import styles from "./Card.module.scss";

function ExpandableCard({ title, summary, children }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader} onClick={() => setIsExpanded(!isExpanded)}>
        <h3>{title}</h3>
        <Button
          className={styles.toggleBtn}
          onClick={(e) => {
            e.stopPropagation(); // prevent double toggle
            setIsExpanded(!isExpanded);
          }}
        >
          {isExpanded ? "−" : "+"}
        </Button>
      </div>

      <div className="card-summary">
        {summary}
      </div>

      {isExpanded && (
        <div className={styles.cardDetails}>
          {children}
        </div>
      )}
    </div>
  );
}

export default ExpandableCard;