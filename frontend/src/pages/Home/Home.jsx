import { useNavigate } from 'react-router-dom';
import Button from '../../components/Button/Button';
import styles from './Home.module.scss';

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>🧙‍♂️ Welcome to Progress RPG</h1>
        <p>Embark on epic quests and master your time through focused activity.</p>
      </div>
      <div className={styles.content}>
        <Button onClick={() => navigate('/game')}>
          Enter the game
        </Button>
      </div>
    </div>
  );
}
