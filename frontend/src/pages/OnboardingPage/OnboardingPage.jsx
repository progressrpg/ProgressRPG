import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useOnboarding from '../../hooks/useOnboarding';
import Form from '../../components/Form/Form';
import Input from '../../components/Input/Input';
import { useGame } from '../../context/GameContext';
import styles from './OnboardingPage.module.scss';

import mob1 from '../../assets/images/tutorial-mob-p1-v2.png';
import mob2 from '../../assets/images/tutorial-mob-p2-v2.png';
import desk from '../../assets/images/tutorial-desktop-v2.png';


function Step0() {
  return <p>Begin your journey through onboarding.</p>;
}

function Step1({ value, onChange }) {
  return (
    <>
      <Input
        id="display-name"
        label="Display Name"
        value={value}
        onChange={onChange}
        placeholder="Enter your display name"
        helpText="This will be visible to others"
        required
        minLength={3}
        maxLength={20}
      />
    </>
  );
}

function Step2({ characterAvailable, character }) {
  return (
    <>
    {!characterAvailable ? (
      <p style={{ color: 'red' }}>
        No characters are currently available. Please check back later.
      </p>
    ) : !character ? (
      <p style={{ color: 'orange' }}>
        Something went wrong: we couldn’t load your character. Try refreshing.
      </p>
    ) : (
      <>
        <p>✅ You have been linked with a character called {character.first_name}.</p>
        <p>Their backstory: {character.backstory}</p>
        <p>This individual's fate is now linked to yours.</p>
        <p>Every activity you complete directly impacts their world. Your consistency powers their abilities. Your achievements unlock their quests. They cannot progress without your dedication, and in turn, their journey provides a visual and tangible measure of your own advancement.</p>
        <p>While they are not aware of the connection, your success is what keeps their quest alive. This is a temporary and powerful connection that ensures neither of you will work alone.</p>
      </>
    )}
  </>
  )
}

function Step3() {
  return (
    <div className="onboarding-screenshots">
      <img src={mob1} className={styles.mobileOnly} alt="Mobile top" />
      <img src={mob2} className={styles.mobileOnly} alt="Mobile bottom" />
      <img src={desk} className={styles.desktopOnly} alt="Desktop full" />
    </div>
  );
}


export default function OnboardingPage() {
  const navigate = useNavigate();
  const { step, progress, error, loading, characterAvailable } = useOnboarding();
  const [formData, setFormData] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const { character, setCharacter } = useGame();

  // Auto-redirect if onboarding is already done
  useEffect(() => {
    if (step === 4) {
      navigate('/game');
    }
  }, [step, navigate]);

  if (loading || step === undefined) return <p>Loading onboarding status…</p>;

  const handleNext = async (e) => {
    e.preventDefault();
    if (submitting) return;

    // Guard for minimum name length on step 1
    if (step === 1 && (!formData.name || formData.name.length < MIN_NAME_LENGTH)) {
      alert(`Display name must be at least ${MIN_NAME_LENGTH} characters.`);
      return;
    }

    setSubmitting(true);
    const result = await progress(formData);
    setSubmitting(false);

    if (result?.step === 2) {
      setCharacter(result.character);
    };
    if (result?.step === 4) navigate('/game');
  };

  const  MIN_NAME_LENGTH = 3;
  const renderStep = () => {
    switch (step) {
      case 1:
        const name = formData.name || '';
        const nameTooShort = name.length < MIN_NAME_LENGTH;

        return (
          <>
            <Step1
              value={name}
              onChange={(val) => setFormData({ ...formData, name: val })}
              characterAvailable={characterAvailable}
            />
            {nameTooShort && (
              <p style={{ color: 'red' }}>
                Display name must be at least {MIN_NAME_LENGTH} characters.
              </p>
            )}
          </>
        );
      case 2:
        return (
          <Step2
            characterAvailable={characterAvailable}
            character={character}
          />
        );
      case 3:
        return <Step3 />;
      default:
        return <Step0 />;
    }
  };


  //const renderStep = () => <Step0 />;

  const getButtonLabel = () => {
    switch (step) {
      case 1:
        return 'Continue';
      case 2:
        return 'Confirm Character';
      case 3:
        return 'Finish Tutorial';
      default:
        return 'Start Onboarding';
    }
  };

  return (
    <div>
      <h1>🧭 Onboarding Step {step ?? '...'}</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <Form
        onSubmit={handleNext}
        submitLabel={getButtonLabel()}
        isSubmitting={submitting}
        disabled={
          (step === 1 && (formData.name || '').length < MIN_NAME_LENGTH) ||
          (!characterAvailable && step === 2)}
      >
        {renderStep()}
      </Form>
    </div>
  );
}
